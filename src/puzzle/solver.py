"""Exact adversarial solver for puzzle positions and puzzle-specific move rules."""

import hashlib
import math
import threading
import time
from collections import deque
from typing import Any

from config import settings
from src.core.game_logic import BEATS, Coord, GameState, Move, Piece, PieceSpec

SolveResult = tuple[float, list[Any], str]
ADVERSARIAL = "adversarial"
RACE_CERTIFICATE = "race_certificate"


def puzzle_position_key(
    board_size: int, pieces: list[PieceSpec], target_coord: Coord | None = None
) -> str:
    """Bind a saved verification to this layout and the corner-win rules."""
    target = target_coord or (0, board_size - 1)
    position = (
        "corner_win_v1",
        board_size,
        target,
        tuple(sorted(tuple(p) for p in pieces)),
    )
    return hashlib.sha256(repr(position).encode()).hexdigest()


def make_puzzle_move(state: GameState, start: Coord, end: Coord) -> Move | None:
    """Apply a puzzle move: wins require the corner and a defender without moves passes."""
    if (start, end) not in state.get_valid_moves(state.current_turn):
        raise ValueError("Illegal puzzle move")
    move = state.make_move(start, end)
    corner_piece = state.get_piece(*state.target_corners[0])
    if state.winner == 0 and not (corner_piece and corner_piece.owner == 0):
        state.winner = None
    if state.winner is None and state.current_turn == 1 and not state.get_valid_moves(1):
        state.current_turn = 0
    return move


def bfs_safe_path(
    board_size: int,
    pieces: list[PieceSpec],
    start_coord: Coord,
    target_coord: Coord,
    player_type: str,
) -> tuple[int | None, list[Coord]]:
    """Find the shortest route on the frozen board, capturing prey but never entering blockers."""
    occupied = {(r, c): (owner, piece_type) for r, c, owner, piece_type in pieces}
    queue = deque([(start_coord, [start_coord])])
    visited = {start_coord}
    while queue:
        (r, c), path = queue.popleft()
        if (r, c) == target_coord:
            return len(path) - 1, path
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                step = (r + dr, c + dc)
                if (
                    (dr == 0 and dc == 0)
                    or not (0 <= step[0] < board_size and 0 <= step[1] < board_size)
                    or step in visited
                ):
                    continue
                if step in occupied:
                    owner, piece_type = occupied[step]
                    if owner == 0 or BEATS[player_type] != piece_type:
                        continue
                visited.add(step)
                queue.append((step, path + [step]))
    return None, []


def _build_state(
    board_size: int, pieces: list[PieceSpec], target: Coord, current_turn: int
) -> GameState:
    """Validate solver inputs and build the root position."""
    if current_turn not in (0, 1):
        raise ValueError("Invalid verification turn")
    state = GameState(board_size, custom_setup=True)
    state.current_turn = current_turn
    state.target_corners[0] = target
    if not state.is_valid_coordinate(*target):
        raise ValueError("Invalid target coordinate")
    for r, c, owner, piece_type in pieces:
        if (
            not state.is_valid_coordinate(r, c)
            or state.board[r][c] is not None
            or owner not in (0, 1)
            or piece_type not in BEATS
        ):
            raise ValueError("Invalid or overlapping puzzle pieces")
        state.board[r][c] = Piece(owner, piece_type)
    return state


def _distance(a: tuple[Any, ...], b: Coord) -> int:
    """Return the king-move distance from a coordinate-prefixed tuple to a square."""
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def _race_trail(start: Coord, target: Coord) -> list[tuple[int, Coord, Coord]]:
    """Build the straight king-move line used by the race certificate."""
    coord = start
    trail = []
    while coord != target:
        dest = (
            coord[0] + (target[0] > coord[0]) - (target[0] < coord[0]),
            coord[1] + (target[1] > coord[1]) - (target[1] < coord[1]),
        )
        trail.append((0, coord, dest))
        coord = dest
    return trail


def _extract_policy(
    cache: dict[tuple[Any, ...], SolveResult],
    board_size: int,
    target: Coord,
    verified: bool,
    root_turn: int,
) -> dict[str, dict[str, Any]]:
    """Turn solved defender nodes into a reusable position-to-reply table."""
    policy: dict[str, dict[str, Any]] = {}
    for (cells, turn, horizon), (value, line, _) in cache.items():
        if (
            turn != 1
            or not line
            or line[0][0] != 1
            or ((root_turn == 0 or verified) and math.isinf(value))
        ):
            continue
        key = puzzle_position_key(board_size, list(cells), target)
        distance = None if math.isinf(value) else int(value)
        previous = policy.get(key)
        if (
            previous is None
            or (previous["steps"] is None and distance is not None)
            or (previous["steps"] is None and distance is None and horizon > previous["remaining"])
        ):
            policy[key] = {"move": line[0][1:], "steps": distance, "remaining": horizon}
    return policy


def verify_puzzle(
    board_size: int,
    pieces: list[PieceSpec],
    target_coord: Coord | None = None,
    max_steps: int = settings.VERIFY_MAX_STEPS,
    time_budget: float = settings.VERIFY_TIME_BUDGET,
    node_budget: int = settings.VERIFY_NODE_BUDGET,
    current_turn: int = 0,
    cancel_event: threading.Event | None = None,
) -> dict[str, Any]:
    """Prove the shortest forced corner win, or explicitly return an unknown result.

    The bounded search considers every legal defensive reply. A geometric
    certificate handles sparse race puzzles without enumerating equivalent replies.
    """
    target = target_coord or (0, board_size - 1)
    if max_steps < 0:
        raise ValueError("Verification horizon must not be negative")
    root = _build_state(board_size, pieces, target, current_turn)
    deadline = time.perf_counter() + max(0.0, time_budget)
    cache: dict[tuple[Any, ...], SolveResult] = {}
    expanded = generated = evaluated = pruned = 0

    def outcome(
        status: str,
        steps: int | None = None,
        path: list[Coord] | None = None,
        moves: list[Any] | None = None,
        method: str = "",
        reason: str = "",
    ) -> dict[str, Any]:
        policy: dict[str, dict[str, Any]] = {}
        if status != "UNVERIFIED":
            policy = _extract_policy(cache, board_size, target, status == "VERIFIED", current_turn)
        result = {
            "status": status,
            "steps": steps,
            "path": path or [],
            "moves": moves or [],
            "method": method,
            "reason": reason,
            "defender_policy": policy,
            "nodes_generated": generated,
            "nodes_evaluated": evaluated,
            "nodes_pruned": pruned,
        }
        if status == "VERIFIED":
            result["position_key"] = puzzle_position_key(board_size, pieces, target)
        return result

    def solve(position: GameState, remaining: int) -> SolveResult:
        nonlocal expanded, generated, evaluated, pruned
        if (
            (cancel_event is not None and cancel_event.is_set())
            or time.perf_counter() >= deadline
            or expanded >= node_budget
        ):
            raise TimeoutError
        cells = tuple(position.get_pieces())
        key = (cells, position.current_turn, remaining)
        if key in cache:
            return cache[key]
        expanded += 1
        players = [(r, c, kind) for r, c, owner, kind in cells if owner == 0]
        defenders = [(r, c, kind) for r, c, owner, kind in cells if owner == 1]
        home = position.target_corners[1]
        if any((r, c) == target for r, c, _ in players):
            return 0, [], ADVERSARIAL
        if position.winner == 1 or not players or any((r, c) == home for r, c, _ in defenders):
            return math.inf, [], ADVERSARIAL
        lower_bound = min(_distance(piece, target) for piece in players)
        if remaining < lower_bound:
            return math.inf, [], ADVERSARIAL

        # A lone attacker that can capture every defender and outruns the fastest
        # reply wins by simply walking to the corner, so distance proves minimality.
        if (
            position.current_turn == 0
            and len(players) == 1
            and all(
                kind == BEATS[players[0][2]] and _distance(defender, home) >= lower_bound
                for defender in defenders
                for kind in (defender[2],)
            )
        ):
            return lower_bound, _race_trail(players[0][:2], target), RACE_CERTIFICATE

        turn = position.current_turn
        moves = position.get_valid_moves(turn)
        if not moves:
            if turn == 0:
                return math.inf, [], ADVERSARIAL
            passed = position.clone()
            passed.current_turn = 0
            passed.winner = None
            return solve(passed, remaining)
        cost = 1 if turn == 0 else 0
        if remaining < cost:
            return math.inf, [], ADVERSARIAL
        if turn == 0:
            moves.sort(key=lambda move: _distance(move[1], target))
        else:
            moves.sort(
                key=lambda move: (
                    move[1] != home,
                    position.get_piece(*move[1]) is None,
                    _distance(move[1], home),
                )
            )
        generated += len(moves)
        best = math.inf if turn == 0 else -math.inf
        trail: list[Any] = []
        for index, (start, end) in enumerate(moves):
            evaluated += 1
            child = position.clone()
            child.make_move(start, end)

            # Capturing the final defender does not replace the corner objective.
            if child.winner == 0 and end != target:
                child.winner = None
            value, continuation, _ = solve(child, remaining - cost)
            value += cost
            if (turn == 0 and value < best) or (turn == 1 and value > best):
                best, trail = value, [(turn, start, end)] + continuation
            if (turn == 0 and best == lower_bound) or (turn == 1 and math.isinf(best)):
                pruned += len(moves) - index - 1
                break
        cache[key] = (best, trail, ADVERSARIAL)
        return cache[key]

    try:
        first_horizon = min(
            (_distance((r, c), target) for r, c, owner, _ in pieces if owner == 0),
            default=0,
        )
        steps: float = math.inf
        moves: list[Any] = []
        method = ADVERSARIAL
        for horizon in range(first_horizon, max_steps + 1):
            steps, moves, method = solve(root, horizon)
            if not math.isinf(steps):
                break
    except TimeoutError:
        return outcome("UNVERIFIED", reason="Verification time or node budget exhausted")
    if math.isinf(steps):
        return outcome(
            "NO_WIN_WITHIN_LIMIT",
            moves=moves,
            reason=f"No forced corner win within {max_steps} player moves",
        )
    player_moves = [(start, end) for owner, start, end in moves if owner == 0]
    path = [player_moves[0][0]] + [end for _, end in player_moves] if player_moves else [target]

    # A single coordinate route cannot represent switches between player pieces.
    if any(a[1] != b[0] for a, b in zip(player_moves, player_moves[1:], strict=False)):
        path = []
    return outcome(
        "VERIFIED",
        int(steps),
        path,
        moves,
        method,
        "Forced corner win verified against all legal replies",
    )

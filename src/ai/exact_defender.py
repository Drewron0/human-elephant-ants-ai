"""Puzzle defender that plays only proven replies and never guesses on timeout."""

import math
import threading
import time
from typing import Any

from config import settings
from src.ai.search import SearchTelemetry
from src.core.game_logic import GameState, MoveTuple
from src.puzzle.solver import make_puzzle_move, puzzle_position_key, verify_puzzle


def _cached_reply(
    entry: Any, legal: list[MoveTuple], remaining_steps: int
) -> tuple[MoveTuple, int | None] | None:
    """Return a stored reply when it is still valid for the remaining move budget."""
    if not isinstance(entry, dict):
        return None
    try:
        move = tuple(tuple(coord) for coord in entry["move"])
        steps = entry["steps"]
        usable = (type(steps) is int and steps >= 0) or (
            steps is None and entry["remaining"] >= remaining_steps
        )
    except (KeyError, TypeError, ValueError):
        return None
    if usable and move in legal:
        return move, steps
    return None


def get_exact_defender_reply(
    state: GameState,
    remaining_steps: int,
    policy: dict[str, Any] | None = None,
    time_budget: float = settings.EXACT_TIME_BUDGET,
    node_budget: int = settings.EXACT_NODE_BUDGET,
    cancel_event: threading.Event | None = None,
) -> dict[str, Any]:
    """Use a proven reply or solve the finite puzzle exactly; never guess on timeout."""
    started = time.perf_counter()
    telemetry = SearchTelemetry()
    policy = policy or {}
    pieces = state.get_pieces()
    key = puzzle_position_key(state.board_size, pieces, state.target_corners[0])

    def result(
        status: str,
        move: MoveTuple | None = None,
        steps: int | None = None,
        updates: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        telemetry.t_turn = time.perf_counter() - started
        if status == "PROVEN":
            telemetry.completed_depth = steps if steps is not None else remaining_steps
        return {
            "status": status,
            "move": move,
            "eval_score": (
                (settings.WIN_SCORE - steps) if steps is not None else -settings.WIN_SCORE
            ),
            "telemetry": telemetry,
            "defender_policy": updates or {},
            "proof_horizon": telemetry.completed_depth,
        }

    if cancel_event is not None and cancel_event.is_set():
        return result("UNVERIFIED")
    if state.current_turn != 1 or state.winner is not None or remaining_steps <= 0:
        return result("TERMINAL")
    legal = state.get_valid_moves(1)
    if not legal:
        return result("NO_MOVES")

    cached = _cached_reply(policy.get(key), legal, remaining_steps)
    if cached is not None:
        return result("PROVEN", cached[0], cached[1])

    # An immediate defender win needs no search.
    telemetry.nodes_generated += len(legal)
    for index, move in enumerate(legal):
        if cancel_event is not None and cancel_event.is_set():
            return result("UNVERIFIED")
        telemetry.nodes_evaluated += 1
        child = state.clone()
        make_puzzle_move(child, *move)
        if child.winner == 1:
            telemetry.nodes_pruned += len(legal) - index - 1
            update = {key: {"move": move, "steps": None, "remaining": remaining_steps}}
            return result("PROVEN", move, updates=update)

    # No player piece can reach the corner in time, regardless of the reply.
    target = state.target_corners[0]
    distance = min(
        (max(abs(r - target[0]), abs(c - target[1])) for r, c, owner, _ in pieces if owner == 0),
        default=math.inf,
    )
    if distance > remaining_steps:
        update = {key: {"move": legal[0], "steps": None, "remaining": remaining_steps}}
        return result("PROVEN", legal[0], updates=update)

    proof = verify_puzzle(
        state.board_size,
        pieces,
        target,
        max_steps=remaining_steps,
        time_budget=time_budget,
        node_budget=node_budget,
        current_turn=1,
        cancel_event=cancel_event,
    )
    telemetry.nodes_generated += proof.get("nodes_generated", 0)
    telemetry.nodes_evaluated += proof.get("nodes_evaluated", 0)
    telemetry.nodes_pruned = proof.get("nodes_pruned", 0)
    if proof["status"] == "UNVERIFIED":
        telemetry.timed_out = True
        return result("UNVERIFIED")
    entry = proof["defender_policy"].get(key)
    if entry is None:
        return result("UNVERIFIED")
    move = tuple(tuple(coord) for coord in entry["move"])  # type: ignore[assignment]
    if move not in legal:
        return result("UNVERIFIED")
    return result("PROVEN", move, entry["steps"], proof["defender_policy"])

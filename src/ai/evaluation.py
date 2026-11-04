"""Static evaluation functions and move ordering heuristics."""

from config import settings
from src.core.game_logic import BEATS, PREDATORS, Coord, GameState, MoveTuple

PieceEntry = tuple[int, int, str]
PIECE_TYPES: tuple[str, ...] = ("H", "E", "A")


def chebyshev_distance(p1: Coord, p2: Coord) -> int:
    """Return the king-move distance between two squares, ignoring obstacles."""
    return max(abs(p1[0] - p2[0]), abs(p1[1] - p2[1]))


def _dynamic_piece_value(piece_type: str, enemy_counts: dict[str, int]) -> float:
    """Value a piece by how much prey and how few predators the enemy has left."""
    prey = BEATS[piece_type]
    predator = PREDATORS[piece_type]
    return settings.MATERIAL_BASE * (enemy_counts[prey] + 1.0) / (enemy_counts[predator] + 1.0)


def _material_score(pieces: list[PieceEntry], enemy_counts: dict[str, int]) -> float:
    """Compute one side's share of the dynamic material term M(s)."""
    return sum(_dynamic_piece_value(piece_type, enemy_counts) for _, _, piece_type in pieces)


def _proximity_score(friendly: list[PieceEntry], hostile: list[PieceEntry]) -> float:
    """Compute one side's share of the predator-prey proximity term C(s)."""
    score = 0.0
    for fr, fc, friend_type in friendly:
        for hr, hc, hostile_type in hostile:
            distance = max(abs(fr - hr), abs(fc - hc))
            if distance > 2:
                continue
            if BEATS[friend_type] == hostile_type:
                score += (
                    settings.PROXIMITY_PREY_ADJACENT
                    if distance == 1
                    else settings.PROXIMITY_PREY_NEAR
                )
            elif BEATS[hostile_type] == friend_type:
                score += (
                    settings.PROXIMITY_PREDATOR_ADJACENT
                    if distance == 1
                    else settings.PROXIMITY_PREDATOR_NEAR
                )
    return score


def _progress_score(size: int, distance: int, weight: float, adjacent: float, near: float) -> float:
    """Reward the closest piece to a goal corner, sharply so when almost there."""
    score = (size - distance) * weight
    if distance <= 1:
        score += adjacent
    elif distance <= 2:
        score += near
    return score


def _count_mobility(state: GameState, r: int, c: int, owner: int, piece_type: str) -> int:
    """Count a piece's legal destinations without allocating move tuples."""
    board = state.board
    size = state.board_size
    mobility = 0
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < size and 0 <= nc < size:
                dest = board[nr][nc]
                if dest is None or (dest.owner != owner and BEATS[piece_type] == dest.p_type):
                    mobility += 1
    return mobility


def evaluate_non_transitive(state: GameState, weights: dict[str, float] | None = None) -> float:
    """Evaluate a position for player 0: E(s) = wm*M(s) + wc*C(s) + wp*P(s) + wt*T(s).

    wm weighs dynamic material, wc predator-prey proximity, wp position and
    mobility, and wt progress towards the goal corner.
    """
    if state.winner == 0:
        return settings.WIN_SCORE
    if state.winner == 1:
        return -settings.WIN_SCORE

    w = weights or settings.DEFAULT_EVALUATION_WEIGHTS
    size = state.board_size
    target_0 = state.target_corners[0]
    target_1 = state.target_corners[1]
    center = (size - 1) / 2.0

    pieces: tuple[list[PieceEntry], list[PieceEntry]] = ([], [])
    counts: tuple[dict[str, int], dict[str, int]] = (
        dict.fromkeys(PIECE_TYPES, 0),
        dict.fromkeys(PIECE_TYPES, 0),
    )
    min_distance = [99, 99]
    center_score = [0.0, 0.0]
    mobility = [0, 0]

    for r, row in enumerate(state.board):
        for c, piece in enumerate(row):
            if piece is None:
                continue
            owner = piece.owner
            pieces[owner].append((r, c, piece.p_type))
            counts[owner][piece.p_type] += 1
            center_score[owner] += max(0.0, center - max(abs(r - center), abs(c - center)))
            mobility[owner] += _count_mobility(state, r, c, owner, piece.p_type)
            goal = target_0 if owner == 0 else target_1
            min_distance[owner] = min(min_distance[owner], chebyshev_distance((r, c), goal))

    m_score = _material_score(pieces[0], counts[1]) - _material_score(pieces[1], counts[0])
    c_score = _proximity_score(pieces[0], pieces[1]) - _proximity_score(pieces[1], pieces[0])
    p_score = (mobility[0] - mobility[1]) * settings.MOBILITY_WEIGHT + (
        center_score[0] - center_score[1]
    ) * settings.CENTER_WEIGHT
    t_score = _progress_score(
        size,
        min_distance[0],
        settings.ATTACKER_PROGRESS_WEIGHT,
        settings.ATTACKER_ADJACENT_BONUS,
        settings.ATTACKER_NEAR_BONUS,
    ) - _progress_score(
        size,
        min_distance[1],
        settings.DEFENDER_PROGRESS_WEIGHT,
        settings.DEFENDER_ADJACENT_BONUS,
        settings.DEFENDER_NEAR_BONUS,
    )
    return (w["wm"] * m_score) + (w["wc"] * c_score) + (w["wp"] * p_score) + (w["wt"] * t_score)


def evaluate_static_material(state: GameState) -> float:
    """Evaluate a position by fixed piece values, the transitive baseline."""
    if state.winner == 0:
        return settings.WIN_SCORE
    if state.winner == 1:
        return -settings.WIN_SCORE
    score = 0.0
    for row in state.board:
        for piece in row:
            if piece:
                value = settings.PIECE_VALUES[piece.p_type]
                score += value if piece.owner == 0 else -value
    return score


def evaluate_board(state: GameState, player: int, difficulty: str = "normal") -> float:
    """Evaluate a position for the Versus-AI practice opponents using static values."""
    opponent = 1 - player
    if state.winner == player:
        return settings.WIN_SCORE
    if state.winner == opponent:
        return -settings.WIN_SCORE

    target = state.target_corners[player]
    opp_target = state.target_corners[opponent]
    size = state.board_size
    my_score = opp_score = 0.0
    min_my_dist = min_opp_dist = 99

    def piece_score(piece_type: str, distance: int) -> float:
        bonus = (size - 1 - distance) * settings.PRACTICE_POSITION_WEIGHT
        if distance <= 2:
            bonus += (3 - distance) * settings.PRACTICE_NEAR_GOAL_WEIGHT
        return settings.PIECE_VALUES[piece_type] + bonus

    for r, row in enumerate(state.board):
        for c, piece in enumerate(row):
            if piece is None:
                continue
            if piece.owner == player:
                distance = chebyshev_distance((r, c), target)
                min_my_dist = min(min_my_dist, distance)
                my_score += piece_score(piece.p_type, distance)
            else:
                distance = chebyshev_distance((r, c), opp_target)
                min_opp_dist = min(min_opp_dist, distance)
                opp_score += piece_score(piece.p_type, distance)

    threat_differential = 0.0
    if difficulty in ("normal", "hard"):
        if min_opp_dist <= 1:
            threat_differential -= settings.PRACTICE_THREAT_SCORE
        if min_my_dist <= 1:
            threat_differential += settings.PRACTICE_THREAT_SCORE
    return (my_score - opp_score) + threat_differential


def order_moves_mvv_lva(
    moves: list[MoveTuple], state: GameState, current_player: int
) -> list[MoveTuple]:
    """Sort moves by goal reach, then suit-adapted MVV-LVA captures, then progress."""
    target = state.target_corners[current_player]
    my_counts = dict.fromkeys(PIECE_TYPES, 0)
    opp_counts = dict.fromkeys(PIECE_TYPES, 0)
    for row in state.board:
        for piece in row:
            if piece:
                (my_counts if piece.owner == current_player else opp_counts)[piece.p_type] += 1

    def score_move(move: MoveTuple) -> float:
        start, end = move
        attacker = state.board[start[0]][start[1]]
        victim = state.board[end[0]][end[1]]
        if end == target:
            return settings.ORDER_TARGET_SCORE
        if victim is not None and attacker is not None:
            victim_value = _dynamic_piece_value(victim.p_type, my_counts)
            attacker_value = _dynamic_piece_value(attacker.p_type, opp_counts)
            return (
                settings.ORDER_CAPTURE_BASE
                + victim_value * settings.ORDER_VICTIM_FACTOR
                - attacker_value
            )
        progress = chebyshev_distance(start, target) - chebyshev_distance(end, target)
        return progress * settings.ORDER_PROGRESS_FACTOR

    return sorted(moves, key=score_move, reverse=True)


def order_moves(moves: list[MoveTuple], state: GameState, player: int) -> list[MoveTuple]:
    """Sort moves for the practice opponents by goal reach, captures and progress."""
    target = state.target_corners[player]

    def score_move(move: MoveTuple) -> float:
        start, end = move
        if end == target:
            return settings.PRACTICE_WIN_ORDER_SCORE
        score = 0.0
        dest = state.board[end[0]][end[1]]
        if dest is not None:
            score += settings.PRACTICE_CAPTURE_BASE + settings.PIECE_VALUES[dest.p_type]
        progress = chebyshev_distance(start, target) - chebyshev_distance(end, target)
        return score + progress * settings.PRACTICE_PROGRESS_FACTOR

    return sorted(moves, key=score_move, reverse=True)

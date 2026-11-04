import math
import random
import time
from typing import Tuple, Optional, List, Dict, Any
from game_logic import GameState, Piece, BEATS, PREDATORS

PIECE_VALUES = {"E": 14.0, "H": 12.0, "A": 10.0}

DEFAULT_EVALUATION_WEIGHTS = {"wm": 1.0, "wc": 1.5, "wp": 0.5, "wt": 2.5}

DEFAULT_PROPOSAL_WEIGHTS = DEFAULT_EVALUATION_WEIGHTS


def chebyshev_distance(p1: Tuple[int, int], p2: Tuple[int, int]) -> int:
    return max(abs(p1[0] - p2[0]), abs(p1[1] - p2[1]))


# =====================================================================
# E(s)
# E(s) = wm * M(s) + wc * C(s) + wp * P(s) + wt * T(s)
# =====================================================================


def evaluate_non_transitive(
    state: GameState, weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Evaluates board state s from Player 0's perspective:
    E(s) = wm * M(s) + wc * C(s) + wp * P(s) + wt * T(s)
    Uses a highly optimized single-pass board scanner.
    """
    if state.winner == 0:
        return 100000.0
    if state.winner == 1:
        return -100000.0

    w = weights if weights else DEFAULT_PROPOSAL_WEIGHTS
    wm = w.get("wm", 1.0)
    wc = w.get("wc", 1.5)
    wp = w.get("wp", 0.5)
    wt = w.get("wt", 2.5)

    size = state.board_size
    target_0 = state.target_corners[0]
    target_1 = state.target_corners[1]
    center = (size - 1) / 2.0

    p0_pieces = []
    p1_pieces = []
    p0_counts = {"H": 0, "E": 0, "A": 0}
    p1_counts = {"H": 0, "E": 0, "A": 0}

    min_d0 = 99
    min_d1 = 99
    center_0 = 0.0
    center_1 = 0.0
    mobility_est_0 = 0
    mobility_est_1 = 0

    board = state.board
    for r in range(size):
        row = board[r]
        for c in range(size):
            p = row[c]
            if p:
                pt = p.p_type
                pos_val = max(0.0, center - max(abs(r - center), abs(c - center)))
                # Mobility count
                mob = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < size and 0 <= nc < size:
                            dest = board[nr][nc]
                            if dest is None or (
                                dest.owner != p.owner and BEATS.get(pt) == dest.p_type
                            ):
                                mob += 1

                if p.owner == 0:
                    p0_pieces.append((r, c, pt))
                    p0_counts[pt] += 1
                    center_0 += pos_val
                    mobility_est_0 += mob
                    d = max(abs(r - target_0[0]), abs(c - target_0[1]))
                    if d < min_d0:
                        min_d0 = d
                else:
                    p1_pieces.append((r, c, pt))
                    p1_counts[pt] += 1
                    center_1 += pos_val
                    mobility_est_1 += mob
                    d = max(abs(r - target_1[0]), abs(c - target_1[1]))
                    if d < min_d1:
                        min_d1 = d

    # Dynamic Material Score M(s)
    def calc_mat(pieces, opp_dist):
        tot = 0.0
        for r, c, pt in pieces:
            prey = BEATS[pt]
            pred = PREDATORS[pt]
            ratio = (opp_dist[prey] + 1.0) / (opp_dist[pred] + 1.0)
            tot += 10.0 * ratio
        return tot

    m_score = calc_mat(p0_pieces, p1_counts) - calc_mat(p1_pieces, p0_counts)

    # Predator-Prey Proximity Score C(s)
    def calc_prox(friendly, hostile):
        score = 0.0
        for fr, fc, fpt in friendly:
            for hr, hc, hpt in hostile:
                dist = max(abs(fr - hr), abs(fc - hc))
                if BEATS.get(fpt) == hpt:
                    if dist == 1:
                        score += 15.0
                    elif dist == 2:
                        score += 5.0
                elif BEATS.get(hpt) == fpt:
                    if dist == 1:
                        score -= 22.0
                    elif dist == 2:
                        score -= 6.0
        return score

    c_score = calc_prox(p0_pieces, p1_pieces) - calc_prox(p1_pieces, p0_pieces)

    # Positional and Mobility Score P(s)
    p_score = (mobility_est_0 - mobility_est_1) * 0.75 + (center_0 - center_1) * 1.5

    # Target Progress Score T(s)
    prog_0 = (size - min_d0) * 14.0
    if min_d0 <= 1:
        prog_0 += 150.0
    elif min_d0 <= 2:
        prog_0 += 50.0

    prog_1 = (size - min_d1) * 10.0
    if min_d1 <= 1:
        prog_1 += 120.0
    elif min_d1 <= 2:
        prog_1 += 40.0
    t_score = prog_0 - prog_1

    return (wm * m_score) + (wc * c_score) + (wp * p_score) + (wt * t_score)


# =====================================================================
# SUIT-ADAPTED MVV-LVA MOVE ORDERING
# =====================================================================


def order_moves_mvv_lva(
    moves: List[Tuple[Tuple[int, int], Tuple[int, int]]],
    state: GameState,
    current_player: int,
) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    """
    Explores high-priority captures first using a suit-adapted MVV-LVA heuristic
    based on dynamic material values M(s).
    """
    target = state.target_corners[current_player]

    opp_counts = {"H": 0, "E": 0, "A": 0}
    my_counts = {"H": 0, "E": 0, "A": 0}
    for r in range(state.board_size):
        for c in range(state.board_size):
            p = state.board[r][c]
            if p:
                if p.owner == current_player:
                    my_counts[p.p_type] += 1
                else:
                    opp_counts[p.p_type] += 1

    def dynamic_val(p_type: str, opp_c: Dict[str, int]) -> float:
        prey = BEATS[p_type]
        pred = PREDATORS[p_type]
        return 10.0 * (opp_c[prey] + 1.0) / (opp_c[pred] + 1.0)

    def score_move(m):
        start, end = m
        attacker = state.board[start[0]][start[1]]
        victim = state.board[end[0]][end[1]]

        if end == target:
            return 100000.0

        if victim is not None:
            # MVV - LVA
            victim_val = dynamic_val(victim.p_type, my_counts)
            attacker_val = (
                dynamic_val(attacker.p_type, opp_counts) if attacker else 10.0
            )
            return 1000.0 + (victim_val * 10.0) - attacker_val

        # Non-capture progress
        d_before = chebyshev_distance(start, target)
        d_after = chebyshev_distance(end, target)
        return (d_before - d_after) * 8.0

    return sorted(moves, key=score_move, reverse=True)


# =====================================================================
# SEARCH TELEMETRY AND ALGORITHMIC ARCHITECTURES
# =====================================================================


# dipake untuk
# 1. proposed algo (dynamic value)
# 2. baseline algo minimax (static )
# 3.
class SearchTelemetry:
    def __init__(self):
        self.nodes_generated: int = 0
        self.nodes_evaluated: int = 0
        self.nodes_pruned: int = 0
        self.t_turn: float = 0.0
        self.completed_depth: int = 0
        self.timed_out: bool = False

    @property
    def pruning_efficiency(self) -> float:
        """
        Percentage of generated child moves skipped by alpha-beta cutoffs.
        Unfinished work at a timeout is not counted as pruning.
        """
        if self.nodes_generated <= 0:
            return 0.0
        return 100.0 * self.nodes_pruned / self.nodes_generated


class SearchTimeout(Exception):
    pass


# Optimized Minimax with Alpha-Beta Pruning and Move Ordering
def _minimax_ab_internal(
    state: GameState,
    depth: int,
    alpha: float,
    beta: float,
    maximizing: bool,
    weights: Dict[str, float],
    telemetry: SearchTelemetry,
    deadline: Optional[float] = None,
) -> Tuple[float, Optional[Tuple[Tuple[int, int], Tuple[int, int]]]]:
    current_player = 0 if maximizing else 1

    if deadline is not None and time.perf_counter() >= deadline:
        raise SearchTimeout
    if state.winner is not None:
        return ((100000.0 + depth) if state.winner == 0 else (-100000.0 - depth)), None

    valid_moves = state.get_valid_moves(current_player)
    if not valid_moves:
        # Player without moves loses
        return ((100000.0 + depth) if not maximizing else (-100000.0 - depth)), None

    if depth == 0:
        return evaluate_non_transitive(state, weights), None

    ordered = order_moves_mvv_lva(valid_moves, state, current_player)
    telemetry.nodes_generated += len(ordered)
    best_move = ordered[0]

    target_win_coord = state.target_corners[current_player]

    best_eval = -math.inf if maximizing else math.inf
    for index, m in enumerate(ordered):
        if deadline is not None and time.perf_counter() >= deadline:
            raise SearchTimeout
        telemetry.nodes_evaluated += 1
        s, e = m
        piece = state.board[s[0]][s[1]]
        target_piece = state.board[e[0]][e[1]]
        old_winner = state.winner
        state.board[e[0]][e[1]], state.board[s[0]][s[1]] = piece, None
        if e == target_win_coord:
            state.winner = current_player
        try:
            val, _ = _minimax_ab_internal(
                state,
                depth - 1,
                alpha,
                beta,
                not maximizing,
                weights,
                telemetry,
                deadline,
            )
        finally:
            state.board[s[0]][s[1]], state.board[e[0]][e[1]] = piece, target_piece
            state.winner = old_winner
        if (maximizing and val > best_eval) or (not maximizing and val < best_eval):
            best_eval, best_move = val, m
        if maximizing:
            alpha = max(alpha, val)
        else:
            beta = min(beta, val)
        if beta <= alpha:
            telemetry.nodes_pruned += len(ordered) - index - 1
            break
    return best_eval, best_move


# Vanilla Minimax (Baseline Model)
# menghitung score minimax dengan menggunakan static piece value * jumlahnya -> kemudian hitung selisihnya
def _evaluate_static_material(state: GameState) -> float:
    if state.winner == 0:
        return 100000.0
    if state.winner == 1:
        return -100000.0

    p0_val = 0.0
    p1_val = 0.0
    for r in range(state.board_size):
        for c in range(state.board_size):
            p = state.board[r][c]
            if p:
                val = PIECE_VALUES.get(p.p_type, 10.0)
                if p.owner == 0:
                    p0_val += val
                else:
                    p1_val += val
    return p0_val - p1_val


def _minimax_vanilla_internal(
    state: GameState, depth: int, maximizing: bool, telemetry: SearchTelemetry
) -> Tuple[float, Optional[Tuple[Tuple[int, int], Tuple[int, int]]]]:
    current_player = 0 if maximizing else 1

    if depth == 0 or state.winner is not None:
        return _evaluate_static_material(state), None

    valid_moves = state.get_valid_moves(current_player)
    if not valid_moves:
        return (100000.0 if not maximizing else -100000.0), None

    telemetry.nodes_generated += len(valid_moves)
    best_move = valid_moves[0]
    target_win_coord = state.target_corners[current_player]

    if maximizing:
        max_eval = -math.inf
        for m in valid_moves:
            telemetry.nodes_evaluated += 1
            s, e = m
            piece = state.board[s[0]][s[1]]
            target_piece = state.board[e[0]][e[1]]

            state.board[e[0]][e[1]] = piece
            state.board[s[0]][s[1]] = None
            old_winner = state.winner
            if e == target_win_coord:
                state.winner = 0

            if state.winner == 0:
                val = 100000.0
            else:
                val, _ = _minimax_vanilla_internal(state, depth - 1, False, telemetry)

            state.board[s[0]][s[1]] = piece
            state.board[e[0]][e[1]] = target_piece
            state.winner = old_winner

            if val > max_eval:
                max_eval = val
                best_move = m
        return max_eval, best_move
    else:
        min_eval = math.inf
        for m in valid_moves:
            telemetry.nodes_evaluated += 1
            s, e = m
            piece = state.board[s[0]][s[1]]
            target_piece = state.board[e[0]][e[1]]

            state.board[e[0]][e[1]] = piece
            state.board[s[0]][s[1]] = None
            old_winner = state.winner
            if e == target_win_coord:
                state.winner = 1

            if state.winner == 1:
                val = -100000.0
            else:
                val, _ = _minimax_vanilla_internal(state, depth - 1, True, telemetry)

            state.board[s[0]][s[1]] = piece
            state.board[e[0]][e[1]] = target_piece
            state.winner = old_winner

            if val < min_eval:
                min_eval = val
                best_move = m
        return min_eval, best_move


# called by any model mode
# get AI move
# searchtelemetry baru dibentuk
def get_defender_move(
    state: GameState,
    agent_model: str = "proposed_d6",
    depth: Optional[int] = None,
    weights: Optional[Dict[str, float]] = None,
    time_budget: float = 1.95,
    rng=None,
) -> Tuple[Optional[Tuple[Tuple[int, int], Tuple[int, int]]], float, SearchTelemetry]:
    """
    Main interface for AI Defender:
    Returns (best_move, eval_score, telemetry)
    where best_move is ((start_r, start_c), (end_r, end_c)).
    Optimal defensive action tuple A = (SourceCoord, TargetCoord, EvalScore).
    """
    t0 = time.perf_counter()
    telemetry = SearchTelemetry()
    valid_moves = state.get_valid_moves(1)
    if not valid_moves:
        telemetry.t_turn = time.perf_counter() - t0
        return None, 100000.0, telemetry

    w = weights if weights else DEFAULT_PROPOSAL_WEIGHTS

    model_clean = agent_model.lower()

    if "baseline_1" in model_clean or "random" in model_clean:
        # Random Move Baseline Agent
        chosen = (rng or random).choice(valid_moves)
        telemetry.t_turn = time.perf_counter() - t0
        return chosen, 0.0, telemetry

    elif "baseline_2" in model_clean or "vanilla" in model_clean:
        # Vanilla Minimax Baseline Agent
        d = 3 if depth is None else depth
        eval_score, move = _minimax_vanilla_internal(
            state, depth=d, maximizing=False, telemetry=telemetry
        )
        telemetry.completed_depth = d
        telemetry.t_turn = time.perf_counter() - t0
        return move or random.choice(valid_moves), eval_score, telemetry

    else:
        # Optimized Minimax Agent with Alpha-Beta Pruning
        d = depth if depth is not None else 6
        deadline = t0 + max(0.0, time_budget)
        move, eval_score = valid_moves[0], evaluate_non_transitive(state, w)
        for horizon in range(1, d + 1):
            try:
                score, candidate = _minimax_ab_internal(
                    state, horizon, -math.inf, math.inf, False, w, telemetry, deadline
                )
            except SearchTimeout:
                telemetry.timed_out = True
                break
            move, eval_score = candidate or move, score
            telemetry.completed_depth = horizon
        telemetry.t_turn = time.perf_counter() - t0
        return move, eval_score, telemetry


# =====================================================================
# BACKWARD COMPATIBILITY INTERFACES (For existing PvE modes)
# =====================================================================


def evaluate_board(state: GameState, player: int, difficulty: str = "normal") -> float:
    opponent = 1 - player
    if state.winner == player:
        return 100000.0
    if state.winner == opponent:
        return -100000.0

    target = state.target_corners[player]
    opp_target = state.target_corners[opponent]

    my_score = 0.0
    opp_score = 0.0

    min_my_dist = 99
    min_opp_dist = 99

    for r in range(state.board_size):
        for c in range(state.board_size):
            piece = state.board[r][c]
            if not piece:
                continue

            dist_my_target = chebyshev_distance((r, c), target)
            dist_opp_target = chebyshev_distance((r, c), opp_target)
            val = PIECE_VALUES.get(piece.p_type, 10.0)

            if piece.owner == player:
                min_my_dist = min(min_my_dist, dist_my_target)
                pos_bonus = (state.board_size - 1 - dist_my_target) * 6.0
                if dist_my_target <= 2:
                    pos_bonus += (3 - dist_my_target) * 25.0
                my_score += val + pos_bonus
            else:
                min_opp_dist = min(min_opp_dist, dist_opp_target)
                opp_pos_bonus = (state.board_size - 1 - dist_opp_target) * 6.0
                if dist_opp_target <= 2:
                    opp_pos_bonus += (3 - dist_opp_target) * 25.0
                opp_score += val + opp_pos_bonus

    threat_differential = 0.0
    if difficulty in ("normal", "hard"):
        if min_opp_dist <= 1:
            threat_differential -= 250.0
        if min_my_dist <= 1:
            threat_differential += 250.0

    return (my_score - opp_score) + threat_differential


def order_moves(
    moves: List[Tuple[Tuple[int, int], Tuple[int, int]]], state: GameState, player: int
) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    target = state.target_corners[player]

    def score_move(move):
        start, end = move
        dest = state.board[end[0]][end[1]]
        score = 0.0

        if end == target:
            return 10000.0

        if dest is not None:
            score += 50.0 + PIECE_VALUES.get(dest.p_type, 10.0)

        dist_before = chebyshev_distance(start, target)
        dist_after = chebyshev_distance(end, target)
        score += (dist_before - dist_after) * 10.0

        return score

    return sorted(moves, key=score_move, reverse=True)


class SearchStats:
    def __init__(self):
        self.nodes = 0


# use fixed piece value, while the minimax_a_b use dynamic piece value
def minimax(
    state: GameState,
    depth: int,
    alpha: float,
    beta: float,
    maximizing: bool,
    player: int,
    difficulty: str = "normal",
    stats: Optional[SearchStats] = None,
) -> Tuple[float, Optional[Tuple[Tuple[int, int], Tuple[int, int]]]]:
    if stats:
        stats.nodes += 1

    # for break the recursive
    if depth == 0 or state.winner is not None:
        return evaluate_board(state, player, difficulty), None

    current_player = state.current_turn
    valid_moves = state.get_valid_moves(current_player)
    if not valid_moves:
        return (-100000.0 if maximizing else 100000.0), None

    ordered = order_moves(valid_moves, state, current_player)
    best_move = ordered[0]

    if maximizing:
        max_eval = -math.inf
        for move in ordered:
            state_clone = state.clone()
            state_clone.make_move(move[0], move[1])
            eval_val, _ = minimax(
                state_clone, depth - 1, alpha, beta, False, player, difficulty, stats
            )
            if eval_val > max_eval:
                max_eval = eval_val
                best_move = move
            alpha = max(alpha, eval_val)
            if beta <= alpha:
                break
        return max_eval, best_move
    else:
        min_eval = math.inf
        for move in ordered:
            state_clone = state.clone()
            state_clone.make_move(move[0], move[1])
            eval_val, _ = minimax(
                state_clone, depth - 1, alpha, beta, True, player, difficulty, stats
            )
            if eval_val < min_eval:
                min_eval = eval_val
                best_move = move
            beta = min(beta, eval_val)
            if beta <= alpha:
                break
        return min_eval, best_move


class AIEngine:
    @staticmethod
    def get_move_and_delay(
        state: GameState, difficulty: str = "normal"
    ) -> Tuple[Optional[Tuple[Tuple[int, int], Tuple[int, int]]], float]:
        player = state.current_turn
        valid_moves = state.get_valid_moves(player)
        if not valid_moves:
            return None, 0.5

        target = state.target_corners[player]
        for move in valid_moves:
            if move[1] == target:
                return move, 0.8

        diff = difficulty.lower()
        stats = SearchStats()

        if diff == "proposed":
            # Search using optimized agent
            best_m, _, telemetry = get_defender_move(state, "proposed_d6", depth=6)
            delay = min(2.0, max(0.5, telemetry.t_turn))
            return best_m or random.choice(valid_moves), delay

        elif diff == "easy":
            scored_moves = []
            for m in valid_moves:
                clone = state.clone()
                clone.make_move(m[0], m[1])
                score = evaluate_board(clone, player, "easy")
                scored_moves.append((score, m))
                stats.nodes += 1
            scored_moves.sort(key=lambda x: x[0], reverse=True)
            top_moves = [m for _, m in scored_moves[: min(3, len(scored_moves))]]
            chosen = (
                random.choice(top_moves)
                if random.random() < 0.35 and len(top_moves) > 1
                else top_moves[0]
            )
            delay = 1.0 + (min(len(valid_moves), 15) / 30.0)
            return chosen, delay

        elif diff == "hard":
            _, move = minimax(
                state,
                depth=3,
                alpha=-math.inf,
                beta=math.inf,
                maximizing=True,
                player=player,
                difficulty="hard",
                stats=stats,
            )
            chosen = move or random.choice(valid_moves)
            node_factor = min(stats.nodes / 200.0, 2.0)
            delay = 2.4 + node_factor
            return chosen, delay

        else:
            _, move = minimax(
                state,
                depth=2,
                alpha=-math.inf,
                beta=math.inf,
                maximizing=True,
                player=player,
                difficulty="normal",
                stats=stats,
            )
            chosen = move or random.choice(valid_moves)
            node_factor = min(stats.nodes / 100.0, 1.2)
            delay = 1.6 + node_factor
            return chosen, delay


def get_ai_move_with_delay(
    state: GameState, difficulty: str = "normal"
) -> Tuple[Optional[Tuple[Tuple[int, int], Tuple[int, int]]], float]:
    return AIEngine.get_move_and_delay(state, difficulty)

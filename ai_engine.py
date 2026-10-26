import math
import random
import time
from typing import Tuple, Optional, List, Dict, Any
from game_logic import GameState, Piece, BEATS, PREDATORS

PIECE_VALUES = {
    'E': 14.0,  # Elephant
    'H': 12.0,  # Human
    'A': 10.0   # Ant
}

DEFAULT_PROPOSAL_WEIGHTS = {
    'wm': 1.0,  # Dynamic Material Score weight
    'wc': 1.5,  # Predator-Prey Proximity Score weight
    'wp': 0.5,  # Positional and Mobility Score weight
    'wt': 2.5   # Target Progress Score weight
}


def chebyshev_distance(p1: Tuple[int, int], p2: Tuple[int, int]) -> int:
    return max(abs(p1[0] - p2[0]), abs(p1[1] - p2[1]))


# =====================================================================
# PROPOSAL IMPLEMENTATION: NON-TRANSITIVE HEURISTIC EVALUATION E(s)
# E(s) = wm * M(s) + wc * C(s) + wp * P(s) + wt * T(s)
# =====================================================================

def dynamic_material_score(state: GameState, player: int = 0) -> float:
    """
    M(s) Dynamic Material Score:
    Evaluates piece values by the ratio of opponent pieces each suit defeats (suit j)
    to opponent pieces that defeat it (suit k).
    """
    opponent = 1 - player
    my_counts = {'H': 0, 'E': 0, 'A': 0}
    opp_counts = {'H': 0, 'E': 0, 'A': 0}
    my_pieces = []
    opp_pieces = []

    for r in range(state.board_size):
        for c in range(state.board_size):
            p = state.board[r][c]
            if p:
                if p.owner == player:
                    my_counts[p.p_type] += 1
                    my_pieces.append((r, c, p))
                else:
                    opp_counts[p.p_type] += 1
                    opp_pieces.append((r, c, p))

    def side_material(pieces, opp_dist):
        total = 0.0
        for r, c, p in pieces:
            prey = BEATS[p.p_type]
            pred = PREDATORS[p.p_type]
            ratio = (opp_dist[prey] + 1.0) / (opp_dist[pred] + 1.0)
            total += 10.0 * ratio
        return total

    return side_material(my_pieces, opp_counts) - side_material(opp_pieces, my_counts)


def predator_prey_proximity_score(state: GameState, player: int = 0) -> float:
    """
    C(s) Predator-Prey Proximity Score:
    Chebyshev distance and attack vectors favoring states where friendly pieces
    threaten valid prey while avoiding adjacent predators.
    """
    opponent = 1 - player
    my_pieces = []
    opp_pieces = []

    for r in range(state.board_size):
        for c in range(state.board_size):
            p = state.board[r][c]
            if p:
                if p.owner == player:
                    my_pieces.append((r, c, p))
                else:
                    opp_pieces.append((r, c, p))

    def proximity_threat(friendly, hostile):
        score = 0.0
        for fr, fc, fp in friendly:
            for hr, hc, hp in hostile:
                dist = chebyshev_distance((fr, fc), (hr, hc))
                if BEATS.get(fp.p_type) == hp.p_type:
                    # Friendly hunts prey
                    if dist == 1:
                        score += 15.0  # Immediate strike range
                    elif dist == 2:
                        score += 5.0   # Closing in on prey
                elif BEATS.get(hp.p_type) == fp.p_type:
                    # Friendly threatened by predator
                    if dist == 1:
                        score -= 22.0  # Imminent predator danger
                    elif dist == 2:
                        score -= 6.0   # In predator attack perimeter
        return score

    return proximity_threat(my_pieces, opp_pieces) - proximity_threat(opp_pieces, my_pieces)


def positional_mobility_score(state: GameState, player: int = 0) -> float:
    """
    P(s) Positional and Mobility Score:
    Legal moves count differential and center-board control.
    """
    opponent = 1 - player
    moves_player = len(state.get_valid_moves(player))
    moves_opponent = len(state.get_valid_moves(opponent))
    mobility_score = (moves_player - moves_opponent) * 0.75

    center = (state.board_size - 1) / 2.0
    center_p = 0.0
    center_o = 0.0

    for r in range(state.board_size):
        for c in range(state.board_size):
            p = state.board[r][c]
            if p:
                dist_center = max(abs(r - center), abs(c - center))
                pos_val = max(0.0, center - dist_center)
                if p.owner == player:
                    center_p += pos_val
                else:
                    center_o += pos_val

    center_score = (center_p - center_o) * 1.5
    return mobility_score + center_score


def target_progress_score(state: GameState, player: int = 0) -> float:
    """
    T(s) Target Progress Score:
    Chebyshev distance in moves from player's pieces to the target corner.
    """
    opponent = 1 - player
    target_p = state.target_corners[player]
    target_o = state.target_corners[opponent]

    min_dist_p = 99
    min_dist_o = 99

    for r in range(state.board_size):
        for c in range(state.board_size):
            p = state.board[r][c]
            if p:
                if p.owner == player:
                    d = chebyshev_distance((r, c), target_p)
                    if d < min_dist_p:
                        min_dist_p = d
                else:
                    d = chebyshev_distance((r, c), target_o)
                    if d < min_dist_o:
                        min_dist_o = d

    size = state.board_size
    prog_p = (size - min_dist_p) * 14.0
    if min_dist_p <= 1:
        prog_p += 150.0
    elif min_dist_p <= 2:
        prog_p += 50.0

    prog_o = (size - min_dist_o) * 10.0
    if min_dist_o <= 1:
        prog_o += 120.0
    elif min_dist_o <= 2:
        prog_o += 40.0

    return prog_p - prog_o


def evaluate_non_transitive(state: GameState, weights: Optional[Dict[str, float]] = None) -> float:
    """
    Evaluates board state s from Player 0's perspective according to the proposal formula:
    E(s) = wm * M(s) + wc * C(s) + wp * P(s) + wt * T(s)
    Uses a highly optimized single-pass board scanner.
    """
    if state.winner == 0:
        return 100000.0
    if state.winner == 1:
        return -100000.0

    w = weights if weights else DEFAULT_PROPOSAL_WEIGHTS
    wm = w.get('wm', 1.0)
    wc = w.get('wc', 1.5)
    wp = w.get('wp', 0.5)
    wt = w.get('wt', 2.5)

    size = state.board_size
    target_0 = state.target_corners[0]
    target_1 = state.target_corners[1]
    center = (size - 1) / 2.0

    p0_pieces = []
    p1_pieces = []
    p0_counts = {'H': 0, 'E': 0, 'A': 0}
    p1_counts = {'H': 0, 'E': 0, 'A': 0}

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
                            if dest is None or (dest.owner != p.owner and BEATS.get(pt) == dest.p_type):
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

    # 1. Dynamic Material Score M(s)
    def calc_mat(pieces, opp_dist):
        tot = 0.0
        for r, c, pt in pieces:
            prey = BEATS[pt]
            pred = PREDATORS[pt]
            ratio = (opp_dist[prey] + 1.0) / (opp_dist[pred] + 1.0)
            tot += 10.0 * ratio
        return tot

    m_score = calc_mat(p0_pieces, p1_counts) - calc_mat(p1_pieces, p0_counts)

    # 2. Predator-Prey Proximity Score C(s)
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

    # 3. Positional and Mobility Score P(s)
    p_score = (mobility_est_0 - mobility_est_1) * 0.75 + (center_0 - center_1) * 1.5

    # 4. Target Progress Score T(s)
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

def order_moves_mvv_lva(moves: List[Tuple[Tuple[int, int], Tuple[int, int]]],
                        state: GameState, current_player: int) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    """
    Explores high-priority captures first using a suit-adapted MVV-LVA heuristic
    based on dynamic material values M(s).
    """
    target = state.target_corners[current_player]

    opp_counts = {'H': 0, 'E': 0, 'A': 0}
    my_counts = {'H': 0, 'E': 0, 'A': 0}
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
            attacker_val = dynamic_val(attacker.p_type, opp_counts) if attacker else 10.0
            return 1000.0 + (victim_val * 10.0) - attacker_val

        # Non-capture progress
        d_before = chebyshev_distance(start, target)
        d_after = chebyshev_distance(end, target)
        return (d_before - d_after) * 8.0

    return sorted(moves, key=score_move, reverse=True)


# =====================================================================
# PROPOSAL SEARCH TELEMETRY & ALGORITHMIC ARCHITECTURES
# =====================================================================

class SearchTelemetry:
    def __init__(self):
        self.nodes_generated: int = 0
        self.nodes_evaluated: int = 0
        self.t_turn: float = 0.0

    @property
    def pruning_efficiency(self) -> float:
        """
        Pruning efficiency: prune = (1 - n_evaluated / n_generated) * 100%
        """
        if self.nodes_generated <= 0:
            return 0.0
        return max(0.0, (1.0 - (self.nodes_evaluated / self.nodes_generated)) * 100.0)


# Proposed Method: Minimax with Alpha-Beta Pruning, MVV-LVA, and E(s)
def _minimax_ab_internal(state: GameState, depth: int, alpha: float, beta: float,
                         maximizing: bool, weights: Dict[str, float],
                         telemetry: SearchTelemetry, deadline: Optional[float] = None) -> Tuple[float, Optional[Tuple[Tuple[int, int], Tuple[int, int]]]]:
    current_player = 0 if maximizing else 1

    if depth == 0 or state.winner is not None or (deadline and time.time() > deadline):
        return evaluate_non_transitive(state, weights), None

    valid_moves = state.get_valid_moves(current_player)
    if not valid_moves:
        # Player without moves loses
        return (100000.0 if not maximizing else -100000.0), None

    ordered = order_moves_mvv_lva(valid_moves, state, current_player)
    telemetry.nodes_generated += len(ordered)
    best_move = ordered[0]

    target_win_coord = state.target_corners[current_player]

    if maximizing:
        max_eval = -math.inf
        for m in ordered:
            if deadline and time.time() > deadline:
                break
            telemetry.nodes_evaluated += 1
            s, e = m
            piece = state.board[s[0]][s[1]]
            target_piece = state.board[e[0]][e[1]]

            # Execute in-place
            state.board[e[0]][e[1]] = piece
            state.board[s[0]][s[1]] = None
            old_winner = state.winner
            if e == target_win_coord:
                state.winner = 0

            if state.winner == 0:
                val = 100000.0
            else:
                val, _ = _minimax_ab_internal(state, depth - 1, alpha, beta, False, weights, telemetry, deadline)

            # Revert in-place
            state.board[s[0]][s[1]] = piece
            state.board[e[0]][e[1]] = target_piece
            state.winner = old_winner

            if val > max_eval:
                max_eval = val
                best_move = m
            alpha = max(alpha, val)
            if beta <= alpha:
                break  # Alpha-Beta cutoff

        return max_eval, best_move
    else:
        min_eval = math.inf
        for m in ordered:
            if deadline and time.time() > deadline:
                break
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
                val, _ = _minimax_ab_internal(state, depth - 1, alpha, beta, True, weights, telemetry, deadline)

            state.board[s[0]][s[1]] = piece
            state.board[e[0]][e[1]] = target_piece
            state.winner = old_winner

            if val < min_eval:
                min_eval = val
                best_move = m
            beta = min(beta, val)
            if beta <= alpha:
                break  # Alpha-Beta cutoff

        return min_eval, best_move


# Baseline 2: Vanilla Minimax (Depth 3, Static Material, No Pruning)
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


def _minimax_vanilla_internal(state: GameState, depth: int, maximizing: bool,
                              telemetry: SearchTelemetry) -> Tuple[float, Optional[Tuple[Tuple[int, int], Tuple[int, int]]]]:
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


def get_defender_move(state: GameState, agent_model: str = 'proposed_d6',
                      depth: int = 6, weights: Optional[Dict[str, float]] = None) -> Tuple[Optional[Tuple[Tuple[int, int], Tuple[int, int]]], float, SearchTelemetry]:
    """
    Main interface for AI Defender:
    Returns (best_move, eval_score, telemetry)
    where best_move is ((start_r, start_c), (end_r, end_c)).
    Optimal defensive action tuple A = (SourceCoord, TargetCoord, EvalScore).
    """
    telemetry = SearchTelemetry()
    valid_moves = state.get_valid_moves(1)  # Defender is Player 1
    if not valid_moves:
        return None, 100000.0, telemetry

    # Instant victory check for defender
    defender_target = state.target_corners[1]
    for m in valid_moves:
        if m[1] == defender_target:
            telemetry.nodes_generated = len(valid_moves)
            telemetry.nodes_evaluated = 1
            telemetry.t_turn = 0.001
            return m, -100000.0, telemetry

    w = weights if weights else DEFAULT_PROPOSAL_WEIGHTS
    t0 = time.time()

    model_clean = agent_model.lower()

    if 'baseline_1' in model_clean or 'random' in model_clean:
        # Baseline 1: Random Move Agent
        chosen = random.choice(valid_moves)
        telemetry.nodes_generated = len(valid_moves)
        telemetry.nodes_evaluated = 1
        t1 = time.time()
        telemetry.t_turn = max(0.001, t1 - t0)
        return chosen, 0.0, telemetry

    elif 'baseline_2' in model_clean or 'vanilla' in model_clean:
        # Baseline 2: Vanilla Minimax Agent (d=3, static, no pruning)
        d = 3 if depth is None else depth
        eval_score, move = _minimax_vanilla_internal(state, depth=d, maximizing=False, telemetry=telemetry)
        t1 = time.time()
        telemetry.t_turn = max(0.001, t1 - t0)
        return move or random.choice(valid_moves), eval_score, telemetry

    else:
        # Proposed Method: Optimized Minimax with Alpha-Beta Pruning, MVV-LVA & E(s)
        d = depth if depth is not None else 6
        deadline = t0 + 1.95  # Strict 2.0s time budget as required in proposal Table 1 & 3
        eval_score, move = _minimax_ab_internal(state, depth=d, alpha=-math.inf, beta=math.inf,
                                                maximizing=False, weights=w, telemetry=telemetry, deadline=deadline)
        t1 = time.time()
        telemetry.t_turn = max(0.001, t1 - t0)
        return move or random.choice(valid_moves), eval_score, telemetry


# =====================================================================
# BACKWARD COMPATIBILITY INTERFACES (For existing PvE modes)
# =====================================================================

def evaluate_board(state: GameState, player: int, difficulty: str = 'normal') -> float:
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
    if difficulty in ('normal', 'hard'):
        if min_opp_dist <= 1:
            threat_differential -= 250.0
        if min_my_dist <= 1:
            threat_differential += 250.0

    return (my_score - opp_score) + threat_differential


def order_moves(moves: List[Tuple[Tuple[int, int], Tuple[int, int]]], state: GameState, player: int) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
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


def minimax(state: GameState, depth: int, alpha: float, beta: float,
            maximizing: bool, player: int, difficulty: str = 'normal', stats: Optional[SearchStats] = None) -> Tuple[float, Optional[Tuple[Tuple[int, int], Tuple[int, int]]]]:
    if stats:
        stats.nodes += 1

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
            eval_val, _ = minimax(state_clone, depth - 1, alpha, beta, False, player, difficulty, stats)
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
            eval_val, _ = minimax(state_clone, depth - 1, alpha, beta, True, player, difficulty, stats)
            if eval_val < min_eval:
                min_eval = eval_val
                best_move = move
            beta = min(beta, eval_val)
            if beta <= alpha:
                break
        return min_eval, best_move


class AIEngine:
    @staticmethod
    def get_move_and_delay(state: GameState, difficulty: str = 'normal') -> Tuple[Optional[Tuple[Tuple[int, int], Tuple[int, int]]], float]:
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

        if diff == 'proposed':
            # Use proposed Alpha-Beta search at depth 6
            best_m, _, telemetry = get_defender_move(state, 'proposed_d6', depth=6)
            delay = min(2.0, max(0.5, telemetry.t_turn))
            return best_m or random.choice(valid_moves), delay

        elif diff == 'easy':
            scored_moves = []
            for m in valid_moves:
                clone = state.clone()
                clone.make_move(m[0], m[1])
                score = evaluate_board(clone, player, 'easy')
                scored_moves.append((score, m))
                stats.nodes += 1
            scored_moves.sort(key=lambda x: x[0], reverse=True)
            top_moves = [m for _, m in scored_moves[:min(3, len(scored_moves))]]
            chosen = random.choice(top_moves) if random.random() < 0.35 and len(top_moves) > 1 else top_moves[0]
            delay = 1.0 + (min(len(valid_moves), 15) / 30.0)
            return chosen, delay

        elif diff == 'hard':
            _, move = minimax(state, depth=3, alpha=-math.inf, beta=math.inf, maximizing=True, player=player, difficulty='hard', stats=stats)
            chosen = move or random.choice(valid_moves)
            node_factor = min(stats.nodes / 200.0, 2.0)
            delay = 2.4 + node_factor
            return chosen, delay

        else:
            _, move = minimax(state, depth=2, alpha=-math.inf, beta=math.inf, maximizing=True, player=player, difficulty='normal', stats=stats)
            chosen = move or random.choice(valid_moves)
            node_factor = min(stats.nodes / 100.0, 1.2)
            delay = 1.6 + node_factor
            return chosen, delay


def get_ai_move(state: GameState, difficulty: str = 'normal'):
    move, _ = AIEngine.get_move_and_delay(state, difficulty)
    return move


def get_ai_move_with_delay(state: GameState, difficulty: str = 'normal') -> Tuple[Optional[Tuple[Tuple[int, int], Tuple[int, int]]], float]:
    return AIEngine.get_move_and_delay(state, difficulty)

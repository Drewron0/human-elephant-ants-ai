import math
import random
import time
from typing import Tuple, Optional, List
from game_logic import GameState, TARGET_CORNERS, BEATS

PIECE_VALUES = {
    'E': 14.0,  # Elephant
    'H': 12.0,  # Human
    'A': 10.0   # Ant
}


def chebyshev_distance(p1: Tuple[int, int], p2: Tuple[int, int]) -> int:
    return max(abs(p1[0] - p2[0]), abs(p1[1] - p2[1]))


def evaluate_board(state: GameState, player: int, difficulty: str = 'normal') -> float:
    opponent = 1 - player
    if state.winner == player:
        return 100000.0
    if state.winner == opponent:
        return -100000.0

    target = TARGET_CORNERS[player]
    opp_target = TARGET_CORNERS[opponent]

    my_score = 0.0
    opp_score = 0.0

    min_my_dist = 99
    min_opp_dist = 99

    for r in range(9):
        for c in range(9):
            piece = state.board[r][c]
            if not piece:
                continue

            dist_my_target = chebyshev_distance((r, c), target)
            dist_opp_target = chebyshev_distance((r, c), opp_target)
            val = PIECE_VALUES.get(piece.p_type, 10.0)

            if piece.owner == player:
                min_my_dist = min(min_my_dist, dist_my_target)
                pos_bonus = (8 - dist_my_target) * 6.0
                if dist_my_target <= 2:
                    pos_bonus += (3 - dist_my_target) * 25.0
                my_score += val + pos_bonus
            else:
                min_opp_dist = min(min_opp_dist, dist_opp_target)
                opp_pos_bonus = (8 - dist_opp_target) * 6.0
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
    target = TARGET_CORNERS[player]

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
        """
        Returns (best_move, simulated_thinking_time_in_seconds).
        Thinking time is determined dynamically by algorithm complexity so AI consumes clock time.
        """
        player = state.current_turn
        valid_moves = state.get_valid_moves(player)
        if not valid_moves:
            return None, 0.5

        # Immediate winning move: very quick reaction
        target = TARGET_CORNERS[player]
        for move in valid_moves:
            if move[1] == target:
                return move, 0.8

        diff = difficulty.lower()
        stats = SearchStats()

        if diff == 'easy':
            # Depth 1 with minor heuristic check
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
            # Easy thinking delay: 1.0s to 1.6s
            delay = 1.0 + (min(len(valid_moves), 15) / 30.0)
            return chosen, delay

        elif diff == 'hard':
            # Depth 3 with move ordering
            _, move = minimax(state, depth=3, alpha=-math.inf, beta=math.inf, maximizing=True, player=player, difficulty='hard', stats=stats)
            chosen = move or random.choice(valid_moves)
            # Hard thinking delay: 2.5s to 4.5s depending on nodes explored
            node_factor = min(stats.nodes / 200.0, 2.0)
            delay = 2.4 + node_factor
            return chosen, delay

        else:
            # Normal: Depth 2
            _, move = minimax(state, depth=2, alpha=-math.inf, beta=math.inf, maximizing=True, player=player, difficulty='normal', stats=stats)
            chosen = move or random.choice(valid_moves)
            # Normal thinking delay: 1.6s to 2.8s
            node_factor = min(stats.nodes / 100.0, 1.2)
            delay = 1.6 + node_factor
            return chosen, delay


def get_ai_move(state: GameState, difficulty: str = 'normal'):
    move, _ = AIEngine.get_move_and_delay(state, difficulty)
    return move


def get_ai_move_with_delay(state: GameState, difficulty: str = 'normal') -> Tuple[Optional[Tuple[Tuple[int, int], Tuple[int, int]]], float]:
    return AIEngine.get_move_and_delay(state, difficulty)
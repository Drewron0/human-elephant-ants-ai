import math
import random
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

    # Threat evaluation for normal and hard
    threat_differential = 0.0
    if difficulty in ('normal', 'hard'):
        if min_opp_dist <= 1:
            threat_differential -= 250.0
        if min_my_dist <= 1:
            threat_differential += 250.0

    total_eval = (my_score - opp_score) + threat_differential
    return total_eval


def order_moves(moves: List[Tuple[Tuple[int, int], Tuple[int, int]]], state: GameState, player: int) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    target = TARGET_CORNERS[player]

    def score_move(move):
        start, end = move
        piece = state.board[start[0]][start[1]]
        dest = state.board[end[0]][end[1]]
        score = 0.0

        if end == target:
            return 10000.0

        # Prioritize captures
        if dest is not None:
            score += 50.0 + PIECE_VALUES.get(dest.p_type, 10.0)

        # Prioritize moving closer to target
        dist_before = chebyshev_distance(start, target)
        dist_after = chebyshev_distance(end, target)
        score += (dist_before - dist_after) * 10.0

        return score

    return sorted(moves, key=score_move, reverse=True)


def minimax(state: GameState, depth: int, alpha: float, beta: float,
            maximizing: bool, player: int, difficulty: str = 'normal') -> Tuple[float, Optional[Tuple[Tuple[int, int], Tuple[int, int]]]]:
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
            eval_val, _ = minimax(state_clone, depth - 1, alpha, beta, False, player, difficulty)
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
            eval_val, _ = minimax(state_clone, depth - 1, alpha, beta, True, player, difficulty)
            if eval_val < min_eval:
                min_eval = eval_val
                best_move = move
            beta = min(beta, eval_val)
            if beta <= alpha:
                break
        return min_eval, best_move


class AIEngine:
    @staticmethod
    def get_move(state: GameState, difficulty: str = 'normal') -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        player = state.current_turn
        valid_moves = state.get_valid_moves(player)
        if not valid_moves:
            return None

        # Check for immediate win
        target = TARGET_CORNERS[player]
        for move in valid_moves:
            if move[1] == target:
                return move

        diff = difficulty.lower()
        if diff == 'easy':
            # Depth 1 with light variety
            scored_moves = []
            for m in valid_moves:
                clone = state.clone()
                clone.make_move(m[0], m[1])
                score = evaluate_board(clone, player, 'easy')
                scored_moves.append((score, m))
            scored_moves.sort(key=lambda x: x[0], reverse=True)
            # Pick from top moves with high probability for best, small chance for second best
            top_moves = [m for _, m in scored_moves[:min(3, len(scored_moves))]]
            return random.choice(top_moves) if random.random() < 0.35 and len(top_moves) > 1 else top_moves[0]

        elif diff == 'hard':
            # Depth 3 with move ordering and advanced heuristics
            _, move = minimax(state, depth=3, alpha=-math.inf, beta=math.inf, maximizing=True, player=player, difficulty='hard')
            return move or random.choice(valid_moves)

        else:
            # Normal: Depth 2 Minimax Alpha-Beta
            _, move = minimax(state, depth=2, alpha=-math.inf, beta=math.inf, maximizing=True, player=player, difficulty='normal')
            return move or random.choice(valid_moves)


def get_ai_move(state: GameState, difficulty: str = 'normal'):
    return AIEngine.get_move(state, difficulty)
"""Versus-AI opponents: a greedy Easy agent and clone-based alpha-beta levels."""

import math
import random

from config import settings
from src.ai.agents import OPTIMIZED_D6
from src.ai.evaluation import evaluate_board, order_moves
from src.ai.search import get_defender_move
from src.core.game_logic import GameState, MoveTuple

OPTIMIZED_DIFFICULTY = "proposed"
DIFFICULTY_LABELS: dict[str, str] = {
    "easy": "Easy",
    "normal": "Normal",
    "hard": "Hard",
    OPTIMIZED_DIFFICULTY: "Optimized",
}


def minimax(
    state: GameState,
    depth: int,
    alpha: float,
    beta: float,
    maximizing: bool,
    player: int,
    difficulty: str,
) -> tuple[float, MoveTuple | None]:
    """Search with alpha-beta from ``player``'s perspective using static evaluation."""
    if depth == 0 or state.winner is not None:
        return evaluate_board(state, player, difficulty), None

    current_player = state.current_turn
    valid_moves = state.get_valid_moves(current_player)
    if not valid_moves:
        return (-settings.WIN_SCORE if maximizing else settings.WIN_SCORE), None

    ordered = order_moves(valid_moves, state, current_player)
    best_move = ordered[0]
    best_eval = -math.inf if maximizing else math.inf
    for move in ordered:
        child = state.clone()
        child.make_move(move[0], move[1])
        value, _ = minimax(child, depth - 1, alpha, beta, not maximizing, player, difficulty)
        if (maximizing and value > best_eval) or (not maximizing and value < best_eval):
            best_eval, best_move = value, move
        if maximizing:
            alpha = max(alpha, value)
        else:
            beta = min(beta, value)
        if beta <= alpha:
            break
    return best_eval, best_move


def _easy_move(state: GameState, player: int, valid_moves: list[MoveTuple]) -> MoveTuple:
    """Choose the best one-ply move, occasionally taking a near-best alternative."""
    scored: list[tuple[float, MoveTuple]] = []
    for move in valid_moves:
        child = state.clone()
        child.make_move(move[0], move[1])
        scored.append((evaluate_board(child, player, "easy"), move))
    scored.sort(key=lambda item: item[0], reverse=True)
    top_moves = [move for _, move in scored[: settings.EASY_TOP_MOVES]]
    if len(top_moves) > 1 and random.random() < settings.EASY_MISTAKE_RATE:
        return random.choice(top_moves)
    return top_moves[0]


def get_ai_move(state: GameState, difficulty: str = "normal") -> MoveTuple | None:
    """Return the opponent's move for the selected level."""
    player = state.current_turn
    valid_moves = state.get_valid_moves(player)
    if not valid_moves:
        return None

    target = state.target_corners[player]
    for move in valid_moves:
        if move[1] == target:
            return move

    level = difficulty.lower()
    if level == OPTIMIZED_DIFFICULTY:
        best_move, _, _ = get_defender_move(state, OPTIMIZED_D6, settings.OPTIMIZED_DEFAULT_DEPTH)
        return best_move or valid_moves[0]

    if level == "easy":
        return _easy_move(state, player, valid_moves)

    hard = level == "hard"
    _, chosen = minimax(
        state,
        settings.HARD_DEPTH if hard else settings.NORMAL_DEPTH,
        -math.inf,
        math.inf,
        True,
        player,
        "hard" if hard else "normal",
    )
    return chosen or valid_moves[0]

"""Minimax family used by the optimized agent and the benchmark baselines."""

import math
import random
import time
from dataclasses import dataclass

from config import settings
from src.ai.agents import BASELINE_RANDOM, BASELINE_VANILLA
from src.ai.evaluation import (
    evaluate_non_transitive,
    evaluate_static_material,
    order_moves_mvv_lva,
)
from src.core.game_logic import GameState, MoveTuple


@dataclass
class SearchTelemetry:
    """Per-turn search counters reported by every defender."""

    nodes_generated: int = 0
    nodes_evaluated: int = 0
    nodes_pruned: int = 0
    t_turn: float = 0.0
    completed_depth: int = 0
    timed_out: bool = False

    @property
    def pruning_efficiency(self) -> float:
        """Return the percentage of generated child moves skipped by cutoffs."""
        if self.nodes_generated <= 0:
            return 0.0
        return 100.0 * self.nodes_pruned / self.nodes_generated


class SearchTimeoutError(Exception):
    """Raised inside the search when its time budget runs out."""


def _terminal_score(winner: int, depth: int) -> float:
    """Score a finished game, preferring wins found closer to the root."""
    score = settings.WIN_SCORE + depth
    return score if winner == 0 else -score


def _minimax_ab_internal(
    state: GameState,
    depth: int,
    alpha: float,
    beta: float,
    maximizing: bool,
    weights: dict[str, float],
    telemetry: SearchTelemetry,
    deadline: float | None = None,
) -> tuple[float, MoveTuple | None]:
    """Run alpha-beta with move ordering, applying moves in place for speed."""
    current_player = 0 if maximizing else 1
    if deadline is not None and time.perf_counter() >= deadline:
        raise SearchTimeoutError
    if state.winner is not None:
        return _terminal_score(state.winner, depth), None

    valid_moves = state.get_valid_moves(current_player)
    if not valid_moves:
        return _terminal_score(1 - current_player, depth), None
    if depth == 0:
        return evaluate_non_transitive(state, weights), None

    ordered = order_moves_mvv_lva(valid_moves, state, current_player)
    telemetry.nodes_generated += len(ordered)
    best_move = ordered[0]
    target_win_coord = state.target_corners[current_player]
    best_eval = -math.inf if maximizing else math.inf

    for index, move in enumerate(ordered):
        if deadline is not None and time.perf_counter() >= deadline:
            raise SearchTimeoutError
        telemetry.nodes_evaluated += 1
        start, end = move
        piece = state.board[start[0]][start[1]]
        target_piece = state.board[end[0]][end[1]]
        old_winner = state.winner
        state.board[end[0]][end[1]], state.board[start[0]][start[1]] = piece, None
        if end == target_win_coord:
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
            state.board[start[0]][start[1]], state.board[end[0]][end[1]] = (
                piece,
                target_piece,
            )
            state.winner = old_winner
        if (maximizing and val > best_eval) or (not maximizing and val < best_eval):
            best_eval, best_move = val, move
        if maximizing:
            alpha = max(alpha, val)
        else:
            beta = min(beta, val)
        if beta <= alpha:
            telemetry.nodes_pruned += len(ordered) - index - 1
            break
    return best_eval, best_move


def _minimax_vanilla_internal(
    state: GameState, depth: int, maximizing: bool, telemetry: SearchTelemetry
) -> tuple[float, MoveTuple | None]:
    """Run plain minimax over static material: no pruning and no move ordering."""
    current_player = 0 if maximizing else 1
    if depth == 0 or state.winner is not None:
        return evaluate_static_material(state), None

    valid_moves = state.get_valid_moves(current_player)
    if not valid_moves:
        return (settings.WIN_SCORE if not maximizing else -settings.WIN_SCORE), None

    telemetry.nodes_generated += len(valid_moves)
    best_move = valid_moves[0]
    target_win_coord = state.target_corners[current_player]
    win_value = settings.WIN_SCORE if maximizing else -settings.WIN_SCORE
    best_eval = -math.inf if maximizing else math.inf

    for move in valid_moves:
        telemetry.nodes_evaluated += 1
        start, end = move
        piece = state.board[start[0]][start[1]]
        target_piece = state.board[end[0]][end[1]]
        state.board[end[0]][end[1]] = piece
        state.board[start[0]][start[1]] = None
        if end == target_win_coord:
            val = win_value
        else:
            val, _ = _minimax_vanilla_internal(state, depth - 1, not maximizing, telemetry)
        state.board[start[0]][start[1]] = piece
        state.board[end[0]][end[1]] = target_piece
        if (maximizing and val > best_eval) or (not maximizing and val < best_eval):
            best_eval, best_move = val, move
    return best_eval, best_move


def get_defender_move(
    state: GameState,
    agent_model: str,
    depth: int | None = None,
    weights: dict[str, float] | None = None,
    time_budget: float = settings.OPTIMIZED_TIME_BUDGET,
    rng: random.Random | None = None,
) -> tuple[MoveTuple | None, float, SearchTelemetry]:
    """Pick a move for player 1 and return (move, evaluation, telemetry)."""
    started = time.perf_counter()
    telemetry = SearchTelemetry()
    valid_moves = state.get_valid_moves(1)
    if not valid_moves:
        telemetry.t_turn = time.perf_counter() - started
        return None, settings.WIN_SCORE, telemetry

    if agent_model == BASELINE_RANDOM:
        chosen = (rng or random).choice(valid_moves)
        telemetry.t_turn = time.perf_counter() - started
        return chosen, 0.0, telemetry

    if agent_model == BASELINE_VANILLA:
        horizon = settings.VANILLA_DEFAULT_DEPTH if depth is None else depth
        eval_score, move = _minimax_vanilla_internal(state, horizon, False, telemetry)
        telemetry.completed_depth = horizon
        telemetry.t_turn = time.perf_counter() - started
        return move or valid_moves[0], eval_score, telemetry

    weights = weights or settings.DEFAULT_EVALUATION_WEIGHTS
    max_depth = settings.OPTIMIZED_DEFAULT_DEPTH if depth is None else depth
    deadline = started + max(0.0, time_budget)
    best_move, eval_score = valid_moves[0], evaluate_non_transitive(state, weights)
    for horizon in range(1, max_depth + 1):
        try:
            score, candidate = _minimax_ab_internal(
                state, horizon, -math.inf, math.inf, False, weights, telemetry, deadline
            )
        except SearchTimeoutError:
            telemetry.timed_out = True
            break
        best_move, eval_score = candidate or best_move, score
        telemetry.completed_depth = horizon
    telemetry.t_turn = time.perf_counter() - started
    return best_move, eval_score, telemetry

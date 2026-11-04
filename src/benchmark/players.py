"""Scripted puzzle players used as the benchmark's opponents."""

import random
from typing import Protocol

from config import settings
from src.core.game_logic import GameState, MoveTuple
from src.puzzle.solver import bfs_safe_path

SHORTEST_PATH = "shortest_path"
SUB_OPTIMAL = "sub_optimal"
RANDOM_PLAYER = "random"
BENCHMARK_PLAYERS: tuple[str, ...] = (SHORTEST_PATH, SUB_OPTIMAL, RANDOM_PLAYER)
PLAYER_LABELS: dict[str, str] = {
    SHORTEST_PATH: "Shortest-Path Player",
    SUB_OPTIMAL: "Sub-Optimal Player",
    RANDOM_PLAYER: "Random Move Player",
}


class ScriptedPlayer(Protocol):
    """A policy that selects the next player move."""

    def select_move(self, state: GameState) -> MoveTuple | None:
        """Return a legal move, or None when no move exists."""


class ShortestPathScriptedPlayer:
    """Replan the shortest legal route on the current, frozen board each turn."""

    def select_move(self, state: GameState) -> MoveTuple | None:
        """Take the first step of the shortest route, or any legal move if blocked."""
        valid_moves = state.get_valid_moves(0)
        if not valid_moves:
            return None
        pieces = state.get_pieces()
        routes = [
            bfs_safe_path(state.board_size, pieces, (r, c), state.target_corners[0], kind)
            for r, c, owner, kind in pieces
            if owner == 0
        ]
        reachable = [route for route in routes if route[0]]
        if reachable:
            _, path = min(reachable, key=lambda item: item[0] or 0)
            return path[0], path[1]
        return valid_moves[0]


class SubOptimalScriptedPlayer:
    """Follow the shortest route, deviating randomly with a fixed probability."""

    def __init__(
        self,
        deviation_rate: float = settings.BENCHMARK_DEVIATION_RATE,
        rng: random.Random | None = None,
    ) -> None:
        self.deviation_rate = deviation_rate
        self.shortest_player = ShortestPathScriptedPlayer()
        self.rng = rng or random.Random()

    def select_move(self, state: GameState) -> MoveTuple | None:
        """Return the shortest-route step or, sometimes, a different legal move."""
        valid_moves = state.get_valid_moves(0)
        if not valid_moves:
            return None
        shortest = self.shortest_player.select_move(state)
        if self.rng.random() < self.deviation_rate and len(valid_moves) > 1:
            return self.rng.choice([move for move in valid_moves if move != shortest])
        return shortest


class RandomScriptedPlayer:
    """Play uniformly random legal moves."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()

    def select_move(self, state: GameState) -> MoveTuple | None:
        """Return a random legal move."""
        valid_moves = state.get_valid_moves(0)
        return self.rng.choice(valid_moves) if valid_moves else None


def build_player(player_type: str, rng: random.Random) -> ScriptedPlayer:
    """Create the scripted player registered under ``player_type``."""
    if player_type == RANDOM_PLAYER:
        return RandomScriptedPlayer(rng)
    if player_type == SUB_OPTIMAL:
        return SubOptimalScriptedPlayer(rng=rng)
    return ShortestPathScriptedPlayer()

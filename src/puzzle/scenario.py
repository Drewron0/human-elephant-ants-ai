"""Puzzle stage definitions, the stage catalog and per-attempt session tracking."""

import logging
from dataclasses import dataclass, field
from typing import Any

from config import settings
from src import storage
from src.core.game_logic import Coord, GameState, Piece, PieceSpec
from src.puzzle.solver import puzzle_position_key

logger = logging.getLogger(__name__)

STATUS_SOLVED = "SOLVED"
STATUS_NEUTRALIZED = "NEUTRALIZED"
STATUS_DELAYED = "DELAYED"
STATUS_ON_TRACK = "ON_TRACK"


class PuzzleScenario:
    """One stage: its board, author-entered minimum and optional proof metadata."""

    def __init__(
        self,
        id_str: str,
        title: str,
        description: str,
        board_size: int,
        s_optimal: int | None = None,
        pieces: list[PieceSpec] | None = None,
        optimal_path: list[Coord] | None = None,
        is_custom: bool = False,
        verification_status: str = "UNVERIFIED",
        verification_method: str = "",
        verification_key: str = "",
        optimal_moves: list[Any] | None = None,
        move_limit: int | None = None,
        defender_policy: dict[str, Any] | None = None,
        minimum_source: str = "",
    ) -> None:
        self.id = id_str
        self.title = title
        self.description = description
        self.board_size = board_size
        self.pieces = pieces or []
        verified = (
            minimum_source != "manual"
            and verification_status == "VERIFIED"
            and verification_key == puzzle_position_key(board_size, self.pieces)
            and type(s_optimal) is int
            and s_optimal >= 0
        )
        self.s_optimal = s_optimal if type(s_optimal) is int and s_optimal > 0 else None
        self.minimum_source = minimum_source
        self.optimal_path = (optimal_path or []) if verified else []
        self.optimal_moves = (optimal_moves or []) if verified else []
        self.defender_policy = (defender_policy or {}) if verified else {}
        if self.s_optimal is not None:
            self.s_max = settings.PUZZLE_MOVE_LIMIT_MULTIPLIER * self.s_optimal
        elif type(move_limit) is int and move_limit > 0:
            self.s_max = move_limit
        else:
            self.s_max = settings.PUZZLE_MOVE_LIMIT_MULTIPLIER * board_size
        self.is_custom = is_custom
        self.verification_status = "VERIFIED" if verified else "UNVERIFIED"
        self.verification_method = verification_method if verified else ""
        self.verification_key = verification_key if verified else ""

    @property
    def step_label(self) -> str:
        """Describe where the stored minimum came from."""
        if self.minimum_source == "manual":
            return "Minimum (user-entered)"
        if self.is_custom or self.verification_status != "VERIFIED":
            return "Minimum (saved)"
        return "Minimum (best defense)"

    @property
    def step_summary(self) -> str:
        """Return a one-line description of the stage minimum."""
        if self.s_optimal is None:
            return "Minimum: not set"
        return f"{self.step_label}: {self.s_optimal} steps"

    def create_initial_state(self) -> GameState:
        """Build a fresh position for this stage."""
        state = GameState(board_size=self.board_size, custom_setup=True)
        for r, c, owner, piece_type in self.pieces:
            state.board[r][c] = Piece(owner, piece_type)
        return state

    def to_dict(self) -> dict[str, Any]:
        """Serialize the stage for storage and benchmark reports."""
        data: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "board_size": self.board_size,
            "s_optimal": self.s_optimal,
            "s_max": self.s_max,
            "pieces": self.pieces,
            "optimal_path": self.optimal_path,
            "optimal_moves": self.optimal_moves,
            "is_custom": self.is_custom,
            "verification_status": self.verification_status,
            "verification_method": self.verification_method,
            "verification_key": self.verification_key,
        }
        if self.defender_policy:
            data["defender_policy"] = self.defender_policy
        if self.minimum_source == "manual":
            data["minimum_source"] = "manual"
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "PuzzleScenario":
        """Rebuild a stage from its stored form."""
        return PuzzleScenario(
            id_str=data.get("id", "custom_stage"),
            title=data.get("title", "Custom Stage"),
            description=data.get("description", ""),
            board_size=data.get("board_size", settings.EDITOR_DEFAULT_BOARD_SIZE),
            s_optimal=data.get("s_optimal"),
            pieces=[(p[0], p[1], p[2], p[3]) for p in data.get("pieces", [])],
            optimal_path=data.get("optimal_path", []),
            optimal_moves=data.get("optimal_moves", []),
            defender_policy=data.get("defender_policy", {}),
            is_custom=data.get("is_custom", True),
            verification_status=data.get("verification_status", "UNVERIFIED"),
            verification_method=data.get("verification_method", ""),
            verification_key=data.get("verification_key", ""),
            move_limit=data.get("s_max"),
            minimum_source=data.get("minimum_source", ""),
        )


def validate_stage(board_size: int, pieces: list[PieceSpec], minimum_text: str) -> str:
    """Return a readable problem with a stage about to be saved, or an empty string."""
    try:
        minimum = int(minimum_text.strip())
    except ValueError:
        minimum = 0
    if minimum <= 0:
        return "Enter a positive whole number for Minimum Steps."
    if not any(owner == 0 for _, _, owner, _ in pieces):
        return "Place at least one of your pieces on the board."
    goal = (0, board_size - 1)
    home = (board_size - 1, 0)
    if any(owner == 0 and (r, c) == goal for r, c, owner, _ in pieces):
        return "Your pieces cannot start on the gold star corner."
    if any(owner == 1 and (r, c) == home for r, c, owner, _ in pieces):
        return "AI pieces cannot start on the red star corner."
    return ""


def get_all_puzzles() -> dict[str, PuzzleScenario]:
    """Load user-created stages, skipping and logging any malformed entry."""
    puzzles: dict[str, PuzzleScenario] = {}
    for item in storage.get_custom_stages():
        try:
            scenario = PuzzleScenario.from_dict(item)
        except (AttributeError, IndexError, KeyError, TypeError, ValueError) as error:
            logger.error("Skipping malformed custom stage: %s", error)
            continue
        scenario.is_custom = True
        puzzles[scenario.id] = scenario
    return puzzles


@dataclass
class PuzzleSession:
    """Track one stage run: steps, undos, resets, outcome and per-turn AI telemetry."""

    scenario: PuzzleScenario
    show_metrics: bool = False
    current_attempt_steps: int = 0
    cumulative_steps: int = 0
    resets_count: int = 0
    undo_count: int = 0
    is_solved: bool = False
    is_neutralized: bool = False
    neutralization_reason: str = ""
    ai_telemetry_history: list[dict[str, Any]] = field(default_factory=list)

    @property
    def s_optimal(self) -> int | None:
        """Return the stage's minimum step count."""
        return self.scenario.s_optimal

    @property
    def s_max(self) -> int:
        """Return the stage's move limit."""
        return self.scenario.s_max

    @property
    def delay_margin(self) -> int:
        """Return how many steps this attempt has used beyond the minimum."""
        if self.s_optimal is None:
            return 0
        return max(0, self.current_attempt_steps - self.s_optimal)

    def record_player_step(self) -> None:
        """Count one player move."""
        self.current_attempt_steps += 1

    def record_undo(self) -> None:
        """Count one undo action and take back its step."""
        self.undo_count += 1
        if self.current_attempt_steps > 0:
            self.current_attempt_steps -= 1

    def record_ai_telemetry(self, **record: Any) -> None:
        """Append one defender turn's metrics."""
        self.ai_telemetry_history.append(record)

    def reset_attempt(self) -> None:
        """Start the attempt over, keeping cumulative statistics."""
        self.resets_count += 1
        self.cumulative_steps += self.current_attempt_steps
        self.current_attempt_steps = 0
        self.is_solved = False
        self.is_neutralized = False
        self.neutralization_reason = ""

    def _neutralize(self, reason: str) -> str:
        """Mark the attempt lost for a stated reason."""
        self.is_neutralized = True
        self.neutralization_reason = reason
        return STATUS_NEUTRALIZED

    def evaluate_status(self, state: GameState) -> str:
        """Classify the position as solved, neutralized, delayed or on track."""
        self.is_solved = False
        self.is_neutralized = False
        self.neutralization_reason = ""
        pieces = state.get_pieces()
        target = state.target_corners[0]
        home = state.target_corners[1]

        if any(owner == 0 and (r, c) == target for r, c, owner, _ in pieces):
            self.is_solved = True
            return STATUS_SOLVED
        if any(owner == 1 and (r, c) == home for r, c, owner, _ in pieces):
            return self._neutralize("The defender reached your home corner")
        if not any(owner == 0 for _, _, owner, _ in pieces):
            return self._neutralize("All player pieces captured")
        if state.current_turn == 0 and not state.get_valid_moves(0):
            return self._neutralize("No legal moves available")
        if self.current_attempt_steps >= self.s_max:
            return self._neutralize(f"Move limit reached ({self.s_max} moves)")
        if self.s_optimal is not None and self.current_attempt_steps > self.s_optimal:
            return STATUS_DELAYED
        return STATUS_ON_TRACK

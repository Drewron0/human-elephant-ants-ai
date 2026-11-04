"""Every tunable constant, parameter and file path used by Chess-Sut.

Values can be overridden with environment variables or a local ``.env`` file.
Logic modules import from here so no parameter is hardcoded at the logic level.
"""

import os
from pathlib import Path
from typing import Final

BASE_DIR: Final[Path] = Path(__file__).resolve().parents[1]


def _load_env_file(path: Path) -> None:
    """Load ``KEY=value`` lines into the environment without overriding real variables."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


_load_env_file(BASE_DIR / ".env")

# Paths and logging
DATA_DIR: Path = Path(os.environ.get("CHESS_SUT_DATA_DIR") or BASE_DIR)
ASSETS_DIR: Final[Path] = BASE_DIR / "assets"
LEADERBOARD_FILE: Path = DATA_DIR / "leaderboard.json"
APP_CONFIG_FILE: Path = DATA_DIR / "app_config.json"
CUSTOM_STAGES_FILE: Path = DATA_DIR / "custom_stages.json"
BENCHMARK_DIR: Path = DATA_DIR / "benchmark_results"
LOG_LEVEL: Final[str] = os.environ.get("CHESS_SUT_LOG_LEVEL", "INFO").upper()
LOG_FORMAT: Final[str] = "%(asctime)s %(levelname)s %(name)s: %(message)s"

# Board rules
DEFAULT_BOARD_SIZE: Final[int] = 9
DEFAULT_PLAYER_NAME: Final[str] = "Player 1"
RECENT_PROFILE_LIMIT: Final[int] = 10
STARTING_LAYOUTS: Final[dict[int, tuple[tuple[int, int, str], ...]]] = {
    9: (
        (8, 0, "H"),
        (8, 1, "E"),
        (8, 2, "A"),
        (8, 3, "E"),
        (7, 0, "A"),
        (7, 1, "H"),
        (7, 2, "E"),
        (6, 0, "E"),
        (6, 1, "H"),
        (5, 0, "A"),
    ),
    6: (
        (5, 0, "H"),
        (5, 1, "E"),
        (5, 2, "A"),
        (4, 0, "A"),
        (4, 1, "H"),
        (3, 0, "E"),
    ),
}

# Evaluation function E(s) = wm*M(s) + wc*C(s) + wp*P(s) + wt*T(s)
WIN_SCORE: Final[float] = 100000.0
DECISIVE_SCORE: Final[float] = 90000.0
DEFAULT_EVALUATION_WEIGHTS: Final[dict[str, float]] = {
    "wm": 1.0,
    "wc": 1.5,
    "wp": 0.5,
    "wt": 2.5,
}
PIECE_VALUES: Final[dict[str, float]] = {"E": 14.0, "H": 12.0, "A": 10.0}
MATERIAL_BASE: Final[float] = 10.0
PROXIMITY_PREY_ADJACENT: Final[float] = 15.0
PROXIMITY_PREY_NEAR: Final[float] = 5.0
PROXIMITY_PREDATOR_ADJACENT: Final[float] = -22.0
PROXIMITY_PREDATOR_NEAR: Final[float] = -6.0
MOBILITY_WEIGHT: Final[float] = 0.75
CENTER_WEIGHT: Final[float] = 1.5
ATTACKER_PROGRESS_WEIGHT: Final[float] = 14.0
ATTACKER_ADJACENT_BONUS: Final[float] = 150.0
ATTACKER_NEAR_BONUS: Final[float] = 50.0
DEFENDER_PROGRESS_WEIGHT: Final[float] = 10.0
DEFENDER_ADJACENT_BONUS: Final[float] = 120.0
DEFENDER_NEAR_BONUS: Final[float] = 40.0

# Move ordering
ORDER_TARGET_SCORE: Final[float] = 100000.0
ORDER_CAPTURE_BASE: Final[float] = 1000.0
ORDER_VICTIM_FACTOR: Final[float] = 10.0
ORDER_PROGRESS_FACTOR: Final[float] = 8.0

# Search budgets
OPTIMIZED_DEFAULT_DEPTH: Final[int] = 6
OPTIMIZED_TIME_BUDGET: Final[float] = 1.95
VANILLA_DEFAULT_DEPTH: Final[int] = 3

# Versus-AI practice opponents
PRACTICE_POSITION_WEIGHT: Final[float] = 6.0
PRACTICE_NEAR_GOAL_WEIGHT: Final[float] = 25.0
PRACTICE_THREAT_SCORE: Final[float] = 250.0
PRACTICE_CAPTURE_BASE: Final[float] = 50.0
PRACTICE_PROGRESS_FACTOR: Final[float] = 10.0
PRACTICE_WIN_ORDER_SCORE: Final[float] = 10000.0
EASY_TOP_MOVES: Final[int] = 3
EASY_MISTAKE_RATE: Final[float] = 0.35
NORMAL_DEPTH: Final[int] = 2
HARD_DEPTH: Final[int] = 3
AI_DELAY_WINNING_MOVE: Final[float] = 0.8
AI_DELAY_NO_MOVE: Final[float] = 0.5
AI_DELAY_OPTIMIZED_MIN: Final[float] = 0.5
AI_DELAY_OPTIMIZED_MAX: Final[float] = 2.0
AI_DELAY_EASY_BASE: Final[float] = 1.0
AI_DELAY_EASY_PER_MOVE: Final[float] = 1.0 / 30.0
AI_DELAY_EASY_MOVE_CAP: Final[int] = 15
AI_DELAY_NORMAL_BASE: Final[float] = 1.6
AI_DELAY_NORMAL_NODE_DIVISOR: Final[float] = 100.0
AI_DELAY_NORMAL_NODE_CAP: Final[float] = 1.2
AI_DELAY_HARD_BASE: Final[float] = 2.4
AI_DELAY_HARD_NODE_DIVISOR: Final[float] = 200.0
AI_DELAY_HARD_NODE_CAP: Final[float] = 2.0

# Puzzle mode
PUZZLE_MOVE_LIMIT_MULTIPLIER: Final[int] = 3
EXACT_TIME_BUDGET: Final[float] = 120.0
EXACT_NODE_BUDGET: Final[int] = 3000000
VERIFY_MAX_STEPS: Final[int] = 14
VERIFY_TIME_BUDGET: Final[float] = 1.0
VERIFY_NODE_BUDGET: Final[int] = 30000
EDITOR_BOARD_SIZES: Final[tuple[int, ...]] = (6, 7, 8, 9)
EDITOR_DEFAULT_BOARD_SIZE: Final[int] = 6
STAGE_LEADERBOARD_PREVIEW: Final[int] = 5
AI_POLL_INTERVAL_MS: Final[int] = 15
UI_SWITCH_INTERVAL_S: Final[float] = 0.0002

# Benchmark
BENCHMARK_GAMES: Final[int] = 1000
BENCHMARK_SEED: Final[int] = 2026
BENCHMARK_BOARD_SIZE: Final[int] = 11
BENCHMARK_STEPS: Final[int] = 10
BENCHMARK_DEVIATION_RATE: Final[float] = 0.25
BENCHMARK_DEFENDER_SEED_OFFSET: Final[int] = 1000003
BENCHMARK_GAME_CHOICES: Final[tuple[int, ...]] = (1, 10, 25, 100, 1000)
BENCHMARK_BOARD_CHOICES: Final[tuple[int, ...]] = (11, 12)
BENCHMARK_MAX_DEFENDERS: Final[int] = 3

# Match setup
TIME_LIMIT_CHOICES: Final[dict[str, int]] = {
    "1 Minute": 60,
    "2 Minutes": 120,
    "3 Minutes": 180,
    "5 Minutes": 300,
    "10 Minutes": 600,
    "No Timer": -1,
}
DEFAULT_TIME_LABEL: Final[str] = "2 Minutes"
NO_TIMER: Final[int] = -1

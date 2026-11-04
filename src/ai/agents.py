"""Registry of selectable defender agents shared by logic, benchmark and UI."""

from typing import NamedTuple


class AgentSpec(NamedTuple):
    """A defender agent: registry key, search depth and display label."""

    model: str
    depth: int
    label: str


EXACT_DEFENDER = "exact_defender"
OPTIMIZED_D6 = "proposed_d6"
OPTIMIZED_D3 = "proposed_d3"
BASELINE_VANILLA = "baseline_2_vanilla"
BASELINE_RANDOM = "baseline_1_random"

BENCHMARK_AGENTS: tuple[AgentSpec, ...] = (
    AgentSpec(OPTIMIZED_D6, 6, "Optimized (Alpha-Beta d=6)"),
    AgentSpec(OPTIMIZED_D3, 3, "Optimized (Alpha-Beta d=3)"),
    AgentSpec(BASELINE_VANILLA, 3, "Vanilla Minimax (d=3, static)"),
    AgentSpec(BASELINE_RANDOM, 1, "Random Move Agent"),
)

PUZZLE_AGENTS: tuple[AgentSpec, ...] = (
    AgentSpec(EXACT_DEFENDER, 6, "Exact Defender (best defense)"),
    AgentSpec(OPTIMIZED_D6, 6, "Optimized Alpha-Beta (d=6)"),
    AgentSpec(BASELINE_VANILLA, 3, "Practice: Vanilla Minimax"),
    AgentSpec(BASELINE_RANDOM, 1, "Practice: Random Moves"),
)

"""Seeded corpus generation and the defender comparison experiment."""

import hashlib
import json
import random
import threading
from collections.abc import Callable
from typing import Any

from config import settings
from src.ai.agents import BENCHMARK_AGENTS
from src.ai.search import get_defender_move
from src.benchmark.players import BENCHMARK_PLAYERS, build_player
from src.core.game_logic import BEATS
from src.puzzle.scenario import PuzzleScenario
from src.puzzle.solver import make_puzzle_move, verify_puzzle

ProgressCallback = Callable[[int, int], None]
TurnCallback = Callable[[dict[str, Any]], None]


class BenchmarkCancelledError(Exception):
    """Raised when a running benchmark is cancelled by the caller."""


def generate_benchmark_corpus(
    num_games: int = settings.BENCHMARK_GAMES,
    board_size: int = settings.BENCHMARK_BOARD_SIZE,
    seed: int = settings.BENCHMARK_SEED,
) -> list[PuzzleScenario]:
    """Generate the seeded, certified 10-step positions used by the benchmark lab."""
    if num_games < 1 or board_size < settings.BENCHMARK_BOARD_SIZE:
        raise ValueError(
            f"Benchmark needs at least one game and a board size of "
            f"{settings.BENCHMARK_BOARD_SIZE} or greater"
        )
    rng = random.Random(seed)
    steps = settings.BENCHMARK_STEPS
    corpus = []
    for _ in range(num_games):
        # This draw keeps the random stream of existing benchmark seeds intact.
        rng.randint(steps, steps)
        suit = rng.choice(list(BEATS))
        start = (steps, rng.randrange(board_size - 1 - steps, board_size))
        columns = rng.sample(
            range(board_size - 1),
            rng.randint(1, min(settings.BENCHMARK_MAX_DEFENDERS, board_size - 1)),
        )
        pieces = [(start[0], start[1], 0, suit)] + [(0, c, 1, BEATS[suit]) for c in columns]
        proof = verify_puzzle(board_size, pieces, max_steps=steps)
        if proof["status"] != "VERIFIED" or proof["steps"] != steps:
            raise RuntimeError("Generated benchmark puzzle failed verification")
        corpus.append(
            PuzzleScenario(
                id_str=(
                    f"race_{board_size}_{start[0]}_{start[1]}_{suit}_"
                    f"{'_'.join(map(str, columns))}"
                ),
                title=f"Benchmark Race ({steps} Steps)",
                description=f"Sparse race: a forced corner win in exactly {steps} moves.",
                board_size=board_size,
                s_optimal=steps,
                pieces=pieces,
                optimal_path=proof["path"],
                optimal_moves=proof["moves"],
                verification_status=proof["status"],
                verification_method=proof["method"],
                verification_key=proof["position_key"],
            )
        )
    return corpus


def _validate_corpus(corpus: list[PuzzleScenario], board_size: int) -> None:
    """Fail fast unless every scenario is a verified race of the configured length."""
    steps = settings.BENCHMARK_STEPS
    for scenario in corpus:
        proof = verify_puzzle(scenario.board_size, scenario.pieces, max_steps=steps)
        if (
            scenario.board_size != board_size
            or proof["status"] != "VERIFIED"
            or proof["steps"] != steps
            or scenario.s_optimal != steps
        ):
            raise ValueError(f"Benchmark requires verified {steps}-step puzzles of this size")


def _play_game(
    scenario: PuzzleScenario,
    game_index: int,
    agent_model: str,
    player_type: str,
    depth: int,
    seed: int,
    totals: dict[str, Any],
    turn_callback: TurnCallback | None,
) -> None:
    """Play one seeded game, accumulating its metrics into ``totals``."""
    player = build_player(player_type, random.Random(seed + game_index))
    defender_rng = random.Random(seed + game_index + settings.BENCHMARK_DEFENDER_SEED_OFFSET)
    state = scenario.create_initial_state()
    solved = False
    for player_step in range(1, scenario.s_max + 1):
        move = player.select_move(state)
        if move is None:
            break
        make_puzzle_move(state, *move)
        corner_piece = state.get_piece(*state.target_corners[0])
        if corner_piece and corner_piece.owner == 0:
            totals["solved_delays"].append(player_step - (scenario.s_optimal or 0))
            solved = True
            break
        if state.winner == 1 or player_step == scenario.s_max:
            break
        if state.current_turn == 0:
            continue
        defender_move, score, telemetry = get_defender_move(
            state, agent_model, depth, rng=defender_rng
        )
        totals["latencies"].append(telemetry.t_turn)
        totals["completed_depths"].append(telemetry.completed_depth)
        totals["timeouts"] += int(telemetry.timed_out)
        totals["full_depth"] += int(telemetry.completed_depth == depth)
        totals["generated"] += telemetry.nodes_generated
        totals["evaluated"] += telemetry.nodes_evaluated
        totals["pruned"] += telemetry.nodes_pruned
        if turn_callback:
            turn_callback(
                {
                    "agent_model": agent_model,
                    "scripted_player": player_type,
                    "game": game_index + 1,
                    "puzzle_id": scenario.id,
                    "player_step": player_step,
                    "action": defender_move,
                    "eval_score": score,
                    **vars(telemetry),
                }
            )
        if defender_move is None:
            state.current_turn = 0
            state.winner = None
            continue
        make_puzzle_move(state, *defender_move)
        if state.winner == 1:
            break
    totals["neutralized"] += int(not solved)


def run_simulation_benchmark(
    agent_model: str,
    scripted_player_type: str,
    num_games: int = settings.BENCHMARK_GAMES,
    depth: int = settings.OPTIMIZED_DEFAULT_DEPTH,
    board_size: int = settings.BENCHMARK_BOARD_SIZE,
    progress_callback: ProgressCallback | None = None,
    corpus: list[PuzzleScenario] | None = None,
    seed: int = settings.BENCHMARK_SEED,
    turn_callback: TurnCallback | None = None,
    cancel_event: threading.Event | None = None,
) -> dict[str, Any]:
    """Compare a defender on a shared certified corpus; emit optional per-turn records."""
    if agent_model not in [agent.model for agent in BENCHMARK_AGENTS]:
        raise ValueError("Unknown benchmark agent")
    if scripted_player_type not in BENCHMARK_PLAYERS or num_games < 1:
        raise ValueError("Invalid player or game count")
    games = corpus if corpus is not None else generate_benchmark_corpus(num_games, board_size, seed)
    if len(games) != num_games:
        raise ValueError("Corpus length must equal num_games")
    _validate_corpus(games, board_size)
    corpus_hash = hashlib.sha256(
        json.dumps([s.to_dict() for s in games], sort_keys=True).encode()
    ).hexdigest()

    totals: dict[str, Any] = {
        "solved_delays": [],
        "latencies": [],
        "completed_depths": [],
        "neutralized": 0,
        "generated": 0,
        "evaluated": 0,
        "pruned": 0,
        "timeouts": 0,
        "full_depth": 0,
    }
    for game_index, scenario in enumerate(games):
        if cancel_event is not None and cancel_event.is_set():
            raise BenchmarkCancelledError
        _play_game(
            scenario,
            game_index,
            agent_model,
            scripted_player_type,
            depth,
            seed,
            totals,
            turn_callback,
        )
        if progress_callback:
            progress_callback(game_index + 1, num_games)

    latencies = totals["latencies"]
    solved_delays = totals["solved_delays"]
    turns = len(latencies)
    generated = totals["generated"]
    return {
        "agent_model": agent_model,
        "scripted_player": scripted_player_type,
        "total_games": num_games,
        "neutralized_count": totals["neutralized"],
        "solved_count": len(solved_delays),
        "neutralization_rate": totals["neutralized"] / num_games * 100.0,
        "delay_margin": (sum(solved_delays) / len(solved_delays) if solved_delays else None),
        "avg_latency": sum(latencies) / turns if turns else 0.0,
        "max_latency": max(latencies, default=0.0),
        "avg_pruning_efficiency": (100.0 * totals["pruned"] / generated if generated else 0.0),
        "nodes_generated": generated,
        "nodes_evaluated": totals["evaluated"],
        "nodes_pruned": totals["pruned"],
        "timeout_count": totals["timeouts"],
        "avg_completed_depth": (sum(totals["completed_depths"]) / turns if turns else 0.0),
        "full_depth_rate": 100.0 * totals["full_depth"] / turns if turns else 0.0,
        "requested_depth": depth,
        "ai_turns": turns,
        "seed": seed,
        "board_size": board_size,
        "s_optimal": settings.BENCHMARK_STEPS,
        "s_max": settings.PUZZLE_MOVE_LIMIT_MULTIPLIER * settings.BENCHMARK_STEPS,
        "corpus_hash": corpus_hash,
        "corpus_family": "certified_sparse_race",
    }

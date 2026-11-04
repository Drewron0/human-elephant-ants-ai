"""Reproducible proposal benchmark: 1,000 games for each of 12 combinations."""

import argparse
import csv
import json
import logging
from pathlib import Path
from typing import Any

from config import settings
from src.ai.agents import BENCHMARK_AGENTS
from src.benchmark.players import BENCHMARK_PLAYERS
from src.benchmark.runner import generate_benchmark_corpus, run_simulation_benchmark

logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=int, default=settings.BENCHMARK_GAMES)
    parser.add_argument("--board-size", type=int, default=settings.BENCHMARK_BOARD_SIZE)
    parser.add_argument("--seed", type=int, default=settings.BENCHMARK_SEED)
    parser.add_argument("--output-dir", type=Path, default=settings.BENCHMARK_DIR)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> list[dict[str, Any]]:
    """Run every defender against every scripted player and save the reports."""
    logging.basicConfig(level=settings.LOG_LEVEL, format="%(message)s")
    args = parse_args(argv)
    corpus = generate_benchmark_corpus(args.games, args.board_size, args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "corpus.json").write_text(
        json.dumps([s.to_dict() for s in corpus], indent=2), encoding="utf-8"
    )
    results: list[dict[str, Any]] = []
    with (args.output_dir / "turns.jsonl").open("w", encoding="utf-8") as turns:

        def log_turn(record: dict[str, Any]) -> None:
            turns.write(json.dumps(record, allow_nan=False) + "\n")

        for model, depth, label in BENCHMARK_AGENTS:
            for player in BENCHMARK_PLAYERS:
                logger.info("%s vs %s: %s games...", label, player, args.games)
                result = run_simulation_benchmark(
                    model,
                    player,
                    args.games,
                    depth,
                    args.board_size,
                    corpus=corpus,
                    seed=args.seed,
                    turn_callback=log_turn,
                )
                results.append(result)

                # Save completed combinations even if a later run is interrupted.
                with (args.output_dir / "results.csv").open(
                    "w", newline="", encoding="utf-8"
                ) as output:
                    writer = csv.DictWriter(output, fieldnames=list(result))
                    writer.writeheader()
                    writer.writerows(results)
                logger.info(
                    "  Max latency: %.3fs; full-depth turns: %.1f%%; neutralized: %.1f%%",
                    result["max_latency"],
                    result["full_depth_rate"],
                    result["neutralization_rate"],
                )
    logger.info("Saved %s combinations to %s", len(results), args.output_dir)
    return results


if __name__ == "__main__":
    main()

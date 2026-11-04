"""Report bounded adversarial verification without turning an unknown result into a proof."""

import argparse
import logging

from config import settings
from src.benchmark.runner import generate_benchmark_corpus
from src.puzzle.scenario import get_all_puzzles
from src.puzzle.solver import verify_puzzle

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    """Verify stages; exit 0 when proven, 1 on no win, 2 when the budget ran out."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--time-budget", type=float, default=settings.VERIFY_TIME_BUDGET)
    parser.add_argument("--node-budget", type=int, default=settings.VERIFY_NODE_BUDGET)
    parser.add_argument("--generated-only", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=settings.LOG_LEVEL, format="%(message)s")

    scenarios = [] if args.generated_only else list(get_all_puzzles().values())
    scenarios += generate_benchmark_corpus(args.samples)
    unknown = failed = False
    for scenario in scenarios:
        result = verify_puzzle(
            scenario.board_size,
            scenario.pieces,
            time_budget=args.time_budget,
            node_budget=args.node_budget,
        )
        logger.info(
            "%s: %s | steps=%s | %s",
            scenario.id,
            result["status"],
            result["steps"],
            result["reason"],
        )
        unknown |= result["status"] == "UNVERIFIED"
        failed |= result["status"] == "NO_WIN_WITHIN_LIMIT"
    logger.info("No global optimality claim is made for unverified stages.")
    return 1 if failed else 2 if unknown else 0


if __name__ == "__main__":
    raise SystemExit(main())

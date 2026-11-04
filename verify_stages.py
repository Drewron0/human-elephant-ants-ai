"""Report bounded adversarial verification without turning an unknown result into a proof."""
import argparse

from puzzle_logic import get_all_puzzles, generate_benchmark_corpus, verify_puzzle


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=int, default=20)
    parser.add_argument('--time-budget', type=float, default=1.0)
    parser.add_argument('--node-budget', type=int, default=30000)
    parser.add_argument('--generated-only', action='store_true')
    args = parser.parse_args(argv)
    scenarios = [] if args.generated_only else list(get_all_puzzles().values())
    scenarios += generate_benchmark_corpus(args.samples)
    unknown = failed = False
    for scenario in scenarios:
        result = verify_puzzle(scenario.board_size, scenario.pieces, time_budget=args.time_budget,
                               node_budget=args.node_budget)
        print(f"{scenario.id}: {result['status']} | "
              f"steps={result['steps']} | {result['reason']}", flush=True)
        unknown |= result['status'] == 'UNVERIFIED'
        failed |= result['status'] == 'NO_WIN_WITHIN_LIMIT'
    print('No global optimality claim is made for unverified stages.')
    return 1 if failed else 2 if unknown else 0


if __name__ == '__main__':
    raise SystemExit(main())

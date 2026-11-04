"""Reproducible proposal benchmark: 1,000 games for each of 12 combinations."""
import argparse
import csv
import json
from pathlib import Path

from puzzle_logic import (BENCHMARK_AGENTS, BENCHMARK_PLAYERS,
                          generate_benchmark_corpus, run_simulation_benchmark)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--games', type=int, default=1000, help='Games per combination (default: 1000)')
    parser.add_argument('--board-size', type=int, default=11, help='At least 11 for certified 10-step races')
    parser.add_argument('--seed', type=int, default=2026)
    parser.add_argument('--output-dir', type=Path, default=Path('benchmark_results'))
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    corpus = generate_benchmark_corpus(args.games, args.board_size, args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / 'corpus.json').write_text(
        json.dumps([s.to_dict() for s in corpus], indent=2), encoding='utf-8')
    results = []
    with (args.output_dir / 'turns.jsonl').open('w', encoding='utf-8') as turns:
        def log_turn(record):
            turns.write(json.dumps(record, allow_nan=False) + '\n')

        for model, depth, label in BENCHMARK_AGENTS:
            for player in BENCHMARK_PLAYERS:
                print(f'{label} vs {player}: {args.games} games...', flush=True)
                result = run_simulation_benchmark(
                    model, player, args.games, depth, args.board_size,
                    corpus=corpus, seed=args.seed, turn_callback=log_turn)
                results.append(result)
                # Save completed combinations even if a later run is interrupted.
                with (args.output_dir / 'results.csv').open('w', newline='', encoding='utf-8') as output:
                    writer = csv.DictWriter(output, fieldnames=list(result))
                    writer.writeheader()
                    writer.writerows(results)
                print(f"  Max latency: {result['max_latency']:.3f}s; "
                      f"full-depth turns: {result['full_depth_rate']:.1f}%; "
                      f"neutralized: {result['neutralization_rate']:.1f}%", flush=True)
    print(f'Saved {len(results)} combinations, corpus and per-turn telemetry to {args.output_dir}')
    return results


if __name__ == '__main__':
    main()

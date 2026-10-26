"""
Chess-Sut: Minimax with Alpha-Beta Pruning Evaluation Framework
Standalone Benchmark Runner (Russell & Norvig, Table 3 Comparative Analysis)

Team: Felix Richardo, Vallerian Davyne Djunarko, Aaron Hans Adiputra
Universitas Ciputra Surabaya 2026
"""

import sys
import time
from puzzle_logic import run_simulation_benchmark


def main():
    print("=" * 80)
    print("CHESS-SUT AI AGENT EVALUATION BENCHMARK")
    print("Comparing Proposed Optimized Agent against Baselines (Proposal Table 3)")
    print("=" * 80)

    configurations = [
        # Model, Depth, Display Label, Opponents
        ('proposed_d6', 6, "Proposed: Optimized (Alpha-Beta d=6)"),
        ('proposed_d3', 3, "Proposed: Optimized (Alpha-Beta d=3)"),
        ('baseline_2_vanilla', 3, "Baseline 2: Vanilla Minimax (d=3, static)"),
        ('baseline_1_random', 1, "Baseline 1: Random Move Agent")
    ]

    opponents = [
        ('shortest_path', 'Shortest-Path Player'),
        ('sub_optimal', 'Sub-Optimal Player (25% deviations)'),
        ('random', 'Random Move Player')
    ]

    games_per_run = 10
    board_size = 6  # Fast benchmark on 6x6 or 9x9

    print(f"\nConfiguration: {games_per_run} games per combination on {board_size}x{board_size} puzzle board.\n")

    results = []

    for agent_k, depth, agent_label in configurations:
        for script_k, opp_label in opponents:
            print(f"Running: [{agent_label}] vs [{opp_label}] ... ", end="", flush=True)
            t_start = time.time()
            res = run_simulation_benchmark(
                agent_model=agent_k,
                scripted_player_type=script_k,
                num_games=games_per_run,
                depth=depth,
                board_size=board_size
            )
            elapsed = time.time() - t_start
            print(f"Done ({elapsed:.2f}s)")
            results.append((agent_label, opp_label, res))

    print("\n" + "=" * 96)
    print(f"{'Defender Model':<32} | {'Scripted Opponent':<24} | {'Tturn (s)':<10} | {'Prune %':<9} | {'ΔS (moves)':<10} | {'Rneut %':<8}")
    print("-" * 96)

    for agent_label, opp_label, r in results:
        print(f"{agent_label:<32} | {opp_label:<24} | {r['avg_latency']:<10.4f} | {r['avg_pruning_efficiency']:<9.1f} | {r['delay_margin']:<10.2f} | {r['neutralization_rate']:<8.1f}")

    print("=" * 96)
    print("\nBenchmark successfully finished!")


if __name__ == "__main__":
    main()

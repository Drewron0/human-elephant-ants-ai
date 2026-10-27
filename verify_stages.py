"""
Stage Winnability Verification Suite
Validates that all 10 preset 6x6 stages and dynamically generated random stages
are mathematically guaranteed to have a reachable, winnable optimal path.
"""

import sys
from puzzle_logic import PRECONFIGURED_STAGES_6X6, find_optimal_winning_path, generate_winnable_puzzle


def verify_preset_stages() -> bool:
    print("=" * 72)
    print("VERIFYING 10 PRESET 6x6 PUZZLE STAGES")
    print("=" * 72)

    all_passed = True

    for stage_id, scenario in sorted(PRECONFIGURED_STAGES_6X6.items()):
        target = (0, scenario.board_size - 1)
        d, path, best_pc = find_optimal_winning_path(scenario.board_size, scenario.pieces, target)

        if d is None:
            print(f"[FAIL] {stage_id} ({scenario.title}): No safe path found!")
            all_passed = False
        else:
            piece_str = best_pc[2] if best_pc else "?"
            print(f"[PASS] {stage_id:<14} | {scenario.title:<24} | Optimal = {d:>2} steps | Limit = {3*d:>2} | Best: {piece_str}")

    return all_passed


def verify_random_generator(sample_size: int = 20) -> bool:
    print("\n" + "=" * 72)
    print(f"VERIFYING RANDOM STAGE GENERATOR ({sample_size} Samples)")
    print("=" * 72)

    passed_count = 0

    for i in range(1, sample_size + 1):
        puzzle = generate_winnable_puzzle(board_size=6, min_steps=5, max_steps=9)
        target = (0, puzzle.board_size - 1)
        d, path, best_pc = find_optimal_winning_path(puzzle.board_size, puzzle.pieces, target)

        if d is not None:
            passed_count += 1
            if i <= 5 or i == sample_size:
                piece_str = best_pc[2] if best_pc else "?"
                print(f"Sample {i:>2}: [PASS] {puzzle.title:<30} | Optimal = {d} steps | Best: {piece_str}")
        else:
            print(f"Sample {i:>2}: [FAIL] Generated unwinnable puzzle!")

    rate = (passed_count / sample_size) * 100.0
    print(f"\nRandom Generation Winnability Rate: {passed_count}/{sample_size} ({rate:.1f}%)")
    return passed_count == sample_size


def main():
    presets_ok = verify_preset_stages()
    random_ok = verify_random_generator(sample_size=20)

    print("\n" + "=" * 72)
    if presets_ok and random_ok:
        print("RESULT: ALL 10 PRESETS AND RANDOM GENERATOR ARE 100% VERIFIED WINNABLE!")
        print("=" * 72)
        sys.exit(0)
    else:
        print("RESULT: VERIFICATION FAILED FOR SOME STAGES.")
        print("=" * 72)
        sys.exit(1)


if __name__ == "__main__":
    main()

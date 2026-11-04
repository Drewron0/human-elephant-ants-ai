import unittest
import os
import json
from typing import List, Tuple, Dict, Any, Optional
from game_logic import GameState, Piece, BEATS, PREDATORS, TARGET_CORNERS
from puzzle_logic import (
    bfs_safe_path,
    find_optimal_winning_path,
    generate_winnable_puzzle,
    PRECONFIGURED_STAGES_6X6,
    PRECONFIGURED_PUZZLES,
    make_puzzle_move,
    PuzzleScenario,
)
from ai_engine import evaluate_non_transitive, get_defender_move, DEFAULT_EVALUATION_WEIGHTS
import storage


class TestGameLogic(unittest.TestCase):
    # Tests non-transitive cyclic capture hierarchy and core mechanics
    def test_cyclic_capture_hierarchy(self) -> None:
        self.assertEqual(BEATS['E'], 'H')
        self.assertEqual(BEATS['H'], 'A')
        self.assertEqual(BEATS['A'], 'E')

        self.assertEqual(PREDATORS['E'], 'A')
        self.assertEqual(PREDATORS['H'], 'E')
        self.assertEqual(PREDATORS['A'], 'H')

    def test_piece_movement_and_capture(self) -> None:
        state = GameState(board_size=6)
        state.board = [[None for _ in range(6)] for _ in range(6)]
        state.board[3][3] = Piece(0, 'E')
        state.board[3][4] = Piece(1, 'H')
        state.board[2][3] = Piece(1, 'A')

        valid_moves = state.get_valid_moves_for_piece(3, 3)
        valid_destinations = [m[1] for m in valid_moves]

        self.assertIn((3, 4), valid_destinations)
        self.assertNotIn((2, 3), valid_destinations)

    def test_target_corner_victory(self) -> None:
        state = GameState(board_size=6)
        state.board = [[None for _ in range(6)] for _ in range(6)]
        state.board[1][5] = Piece(0, 'H')

        move_res = state.make_move((1, 5), (0, 5))
        self.assertTrue(move_res)
        self.assertEqual(state.winner, 0)


class TestPuzzleLogic(unittest.TestCase):
    # Tests BFS safe path search, preset stages, and random puzzle generation
    def test_presets_have_replayable_minimum_routes_with_fixed_enemies(self) -> None:
        for stage_key, scenario in PRECONFIGURED_PUZZLES.items():
            with self.subTest(stage=stage_key):
                self.assertIn('fixed enemies', scenario.step_label)
                self.assertIsNotNone(scenario.s_optimal)
                self.assertEqual(len(scenario.optimal_path) - 1, scenario.s_optimal)
                self.assertEqual(scenario.s_max, 3 * scenario.s_optimal)
                state = scenario.create_initial_state()
                for start, end in zip(scenario.optimal_path, scenario.optimal_path[1:]):
                    state.current_turn = 0  # Defenders remain stationary for the baseline.
                    self.assertIn((start, end), state.get_valid_moves(0))
                    make_puzzle_move(state, start, end)
                self.assertEqual(state.winner, 0)

        self.assertEqual(PRECONFIGURED_STAGES_6X6['stage_6x6_01'].s_optimal, 5)
        self.assertEqual(PRECONFIGURED_STAGES_6X6['stage_6x6_06'].s_optimal, 4)

    def test_minimum_counts_obstacle_detour_and_ignores_stale_saved_count(self) -> None:
        pieces = [(3, 0, 0, 'H')] + [(1, c, 1, 'E') for c in range(3)]
        scenario = PuzzleScenario.from_dict(dict(
            id='detour', board_size=4, pieces=pieces, s_optimal=6,
            optimal_path=[(3, 0), (0, 3)]))
        # Three diagonal moves would have to pass through blocked (1, 2).
        self.assertEqual(scenario.s_optimal, 4)
        self.assertEqual(len(scenario.optimal_path), 5)
        self.assertEqual(scenario.s_max, 12)
        self.assertNotIn((1, 2), scenario.optimal_path)
        self.assertEqual(PuzzleScenario('old', 'Old', '', 4, 6, pieces).s_optimal, 4)

        pieces_without_obstacles = [(3, 0, 0, 'H')]
        steps, _, _ = find_optimal_winning_path(4, pieces_without_obstacles)
        self.assertEqual(steps, 3)

    def test_static_minimum_respects_cyclic_capture_rules(self) -> None:
        for enemy, expected in [('A', 2), ('H', 3), ('E', 3)]:
            with self.subTest(enemy=enemy):
                steps, path, _ = find_optimal_winning_path(
                    3, [(2, 0, 0, 'H'), (1, 1, 1, enemy)])
                self.assertEqual(steps, expected)
                self.assertEqual((1, 1) in path, enemy == 'A')

    def test_unreachable_corner_does_not_fall_back_to_six_steps(self) -> None:
        scenario = PuzzleScenario.from_dict(dict(
            id='blocked', board_size=3,
            pieces=[(2, 0, 0, 'H'), (0, 2, 1, 'E')]))
        self.assertIsNone(scenario.s_optimal)
        self.assertEqual(scenario.optimal_path, [])
        self.assertEqual(scenario.step_summary, 'No route (fixed enemies)')

    def test_minimum_selects_best_player_piece(self) -> None:
        steps, path, piece = find_optimal_winning_path(
            6, [(5, 0, 0, 'H'), (2, 3, 0, 'E')])
        self.assertEqual(steps, 2)
        self.assertEqual(piece, (2, 3, 'E'))
        self.assertEqual(path[0], (2, 3))
        self.assertEqual(path[-1], (0, 5))

    def test_random_winnable_generator(self) -> None:
        for _ in range(3):
            scenario = generate_winnable_puzzle(board_size=6, min_steps=5, max_steps=8)
            target = (0, scenario.board_size - 1)
            d, path, best_pc = find_optimal_winning_path(scenario.board_size, scenario.pieces, target)
            self.assertIsNotNone(path)
            self.assertIsNotNone(d)
            self.assertGreaterEqual(d, 3)


class TestStorageCRUD(unittest.TestCase):
    # Tests custom stages CRUD operations and stage leaderboard storage
    def setUp(self) -> None:
        self.test_stage_id = "test_unit_stage_crud"

    def tearDown(self) -> None:
        storage.delete_custom_stage(self.test_stage_id)

    def test_custom_stage_crud_lifecycle(self) -> None:
        stage_data: Dict[str, Any] = {
            'id': self.test_stage_id,
            'title': 'Unit Test Stage',
            'board_size': 6,
            's_optimal': 5,
            's_max': 15,
            'player_pieces': [{'r': 5, 'c': 0, 'type': 'H'}],
            'ai_pieces': [{'r': 0, 'c': 0, 'type': 'E'}]
        }
        save_ok = storage.save_custom_stage(stage_data)
        self.assertTrue(save_ok)

        custom_stages = storage.get_custom_stages()
        matching = [s for s in custom_stages if s.get('id') == self.test_stage_id]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]['title'], 'Unit Test Stage')

        del_ok = storage.delete_custom_stage(self.test_stage_id)
        self.assertTrue(del_ok)
        custom_stages_after = storage.get_custom_stages()
        matching_after = [s for s in custom_stages_after if s.get('id') == self.test_stage_id]
        self.assertEqual(len(matching_after), 0)

    def test_stage_leaderboard_recording(self) -> None:
        test_key = "test_stage_lb"
        res_id = storage.save_stage_score(
            stage_id=test_key,
            username="Tester",
            steps=7,
            time_spent=12,
            undos=0,
            delay_margin=2
        )
        self.assertIsInstance(res_id, str)

        lb = storage.get_stage_leaderboard(test_key)
        self.assertGreaterEqual(len(lb), 1)
        self.assertEqual(lb[0]['username'], "Tester")
        self.assertEqual(lb[0]['steps'], 7)

        storage.clear_stage_leaderboard(test_key)
        lb_empty = storage.get_stage_leaderboard(test_key)
        self.assertEqual(len(lb_empty), 0)


class TestAIEngine(unittest.TestCase):
    # Tests non-transitive heuristic scoring and minimax search execution
    def test_non_transitive_evaluation(self) -> None:
        state = GameState(board_size=6)
        state.board = [[None for _ in range(6)] for _ in range(6)]
        state.board[5][0] = Piece(0, 'H')
        state.board[1][4] = Piece(1, 'E')

        score = evaluate_non_transitive(state, DEFAULT_EVALUATION_WEIGHTS)
        self.assertIsInstance(score, (int, float))

    def test_defender_move_selection(self) -> None:
        state = GameState(board_size=6)
        state.board = [[None for _ in range(6)] for _ in range(6)]
        state.board[4][0] = Piece(0, 'H')
        state.board[2][2] = Piece(1, 'E')
        state.current_turn = 1

        move, score, tele = get_defender_move(state, agent_model='proposed_d6', depth=2)
        self.assertIsNotNone(move)
        self.assertLess(tele.t_turn, 2.0)


if __name__ == '__main__':
    unittest.main()

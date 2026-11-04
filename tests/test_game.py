import unittest
import os
import json
from typing import List, Tuple, Dict, Any, Optional
from game_logic import GameState, Piece, BEATS, PREDATORS, TARGET_CORNERS
from puzzle_logic import (
    bfs_safe_path,
    find_optimal_winning_path,
    make_puzzle_move,
    verify_puzzle,
    puzzle_position_key,
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
    # Tests minimum-step verification and the benchmark puzzle generator
    def test_minimum_counts_obstacle_detour_and_ignores_stale_saved_count(self) -> None:
        pieces = [(3, 0, 0, 'H')] + [(1, c, 1, 'E') for c in range(3)]
        scenario = PuzzleScenario.from_dict(dict(
            id='detour', board_size=4, pieces=pieces, s_optimal=6,
            optimal_path=[(3, 0), (0, 3)]))
        # Three diagonal moves would have to pass through blocked (1, 2).
        self.assertIsNone(scenario.s_optimal)
        self.assertEqual(scenario.optimal_path, [])
        self.assertEqual(scenario.s_max, 12)
        self.assertIsNone(PuzzleScenario('old', 'Old', '', 4, 6, pieces).s_optimal)
        static_steps, static_path, _ = find_optimal_winning_path(4, pieces)
        self.assertEqual(static_steps, 4)
        self.assertNotIn((1, 2), static_path)

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
        self.assertEqual(scenario.step_summary, 'Minimum: unverified')

    def test_verified_minimum_is_loaded_without_recalculating(self) -> None:
        from unittest.mock import patch
        pieces = [(2, 0, 0, 'H'), (0, 0, 1, 'H')]
        result = verify_puzzle(3, pieces, max_steps=3)
        payload = dict(id='verified', board_size=3, pieces=pieces,
                       s_optimal=result['steps'], optimal_path=result['path'],
                       optimal_moves=result['moves'], verification_status=result['status'],
                       verification_method=result['method'], verification_key=result['position_key'])
        with patch('puzzle_logic.verify_puzzle') as verify, \
                patch('puzzle_logic.find_optimal_winning_path') as static:
            scenario = PuzzleScenario.from_dict(payload)
        verify.assert_not_called()
        static.assert_not_called()
        self.assertEqual(scenario.s_optimal, 2)
        self.assertEqual(scenario.s_max, 6)
        self.assertTrue(scenario.optimal_moves)
        self.assertEqual(scenario.to_dict()['verification_key'], puzzle_position_key(3, pieces))
        self.assertEqual(PuzzleScenario.from_dict(scenario.to_dict()).s_optimal, 2)
        payload['s_max'] = 1
        self.assertEqual(PuzzleScenario.from_dict(payload).s_max, 6)

        payload['pieces'] = [(2, 0, 0, 'H'), (0, 1, 1, 'E')]
        stale = PuzzleScenario.from_dict(payload)
        self.assertIsNone(stale.s_optimal)
        self.assertEqual(stale.verification_status, 'UNVERIFIED')
        self.assertEqual(stale.optimal_path, [])

    def test_minimum_selects_best_player_piece(self) -> None:
        steps, path, piece = find_optimal_winning_path(
            6, [(5, 0, 0, 'H'), (2, 3, 0, 'E')])
        self.assertEqual(steps, 2)
        self.assertEqual(piece, (2, 3, 'E'))
        self.assertEqual(path[0], (2, 3))
        self.assertEqual(path[-1], (0, 5))



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

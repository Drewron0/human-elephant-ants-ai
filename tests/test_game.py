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
    PuzzleScenario,
)
from ai_engine import evaluate_non_transitive, get_defender_move, DEFAULT_PROPOSAL_WEIGHTS
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
    def test_all_10_preset_stages_winnable(self) -> None:
        for stage_key, scenario in PRECONFIGURED_STAGES_6X6.items():
            target = (0, scenario.board_size - 1)
            d, path, best_pc = find_optimal_winning_path(scenario.board_size, scenario.pieces, target)
            self.assertIsNotNone(
                path,
                f"Preset stage '{stage_key}' must have a valid winning path"
            )
            self.assertIsNotNone(d)
            self.assertGreaterEqual(d, 1)

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

        score = evaluate_non_transitive(state, DEFAULT_PROPOSAL_WEIGHTS)
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

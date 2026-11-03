import math
import unittest
from unittest.mock import patch

from ai_engine import get_defender_move
from game_logic import GameState, Piece


class TestSearchCompliance(unittest.TestCase):
    def position(self):
        state = GameState(6, custom_setup=True)
        state.board[4][1] = Piece(1, 'H')
        state.board[0][0] = Piece(0, 'A')
        state.current_turn = 1
        return state

    def test_random_agent_does_not_prefer_an_immediate_win(self):
        state = self.position()
        other = ((4, 1), (3, 1))
        with patch('ai_engine.random.choice', return_value=other) as choose:
            move, _, telemetry = get_defender_move(state, 'baseline_1_random')
        choose.assert_called_once_with(state.get_valid_moves(1))
        self.assertEqual(move, other)
        self.assertEqual(telemetry.pruning_efficiency, 0)
        self.assertEqual(telemetry.nodes_evaluated, 0)

    def test_timeout_returns_finite_legal_fallback_without_changing_board(self):
        state = self.position()
        before = state.to_dict()
        move, score, telemetry = get_defender_move(state, time_budget=0)
        self.assertIn(move, state.get_valid_moves(1))
        self.assertTrue(math.isfinite(score))
        self.assertTrue(telemetry.timed_out)
        self.assertEqual(telemetry.completed_depth, 0)
        self.assertEqual(telemetry.pruning_efficiency, 0)
        self.assertEqual(state.to_dict(), before)

    def test_timeout_during_recursion_restores_board(self):
        state = self.position()
        before = state.to_dict()
        # Enter the root and one child, then expire inside the recursive call.
        with patch('ai_engine.time.perf_counter', side_effect=[0, 0, 0, 10, 10]):
            move, score, telemetry = get_defender_move(state, time_budget=1)
        self.assertEqual(state.to_dict(), before)
        self.assertIn(move, state.get_valid_moves(1))
        self.assertTrue(math.isfinite(score))
        self.assertTrue(telemetry.timed_out)

    def test_completed_search_reports_depth_and_real_cutoffs(self):
        state = self.position()
        move, _, telemetry = get_defender_move(state, depth=3)
        self.assertEqual(move[1], state.target_corners[1])
        self.assertEqual(telemetry.completed_depth, 3)
        self.assertFalse(telemetry.timed_out)
        self.assertGreater(telemetry.nodes_pruned, 0)
        self.assertEqual(telemetry.nodes_generated,
                         telemetry.nodes_evaluated + telemetry.nodes_pruned)
        _, _, baseline = get_defender_move(state, 'baseline_2_vanilla', depth=3)
        self.assertEqual(baseline.pruning_efficiency, 0)


if __name__ == '__main__':
    unittest.main()

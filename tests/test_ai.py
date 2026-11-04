import unittest
from src.core.game_logic import GameState
from src.ai.evaluation import evaluate_board
from src.ai.search import get_defender_move, BASELINE_RANDOM, BASELINE_VANILLA


class TestAI(unittest.TestCase):
    def test_evaluate_initial_board(self):
        """Initial symmetric board should evaluate to 0 for both players."""
        state = GameState(6)
        score_p0 = evaluate_board(state, 0)
        score_p1 = evaluate_board(state, 1)
        self.assertEqual(score_p0, 0.0)
        self.assertEqual(score_p1, 0.0)

    def test_defender_move_selection(self):
        """Verify defender returns a valid move and telemetry data for player 1."""
        state = GameState(6)
        # Test random baseline
        move, score, telemetry = get_defender_move(state, BASELINE_RANDOM, 1)
        self.assertIsNotNone(move)
        valid_moves = state.get_valid_moves(1)
        self.assertIn(move, valid_moves)
        self.assertGreaterEqual(telemetry.t_turn, 0.0)

        # Test minimax vanilla baseline
        move_v, score_v, telemetry_v = get_defender_move(state, BASELINE_VANILLA, depth=1)
        self.assertIsNotNone(move_v)
        self.assertIn(move_v, valid_moves)
        self.assertGreaterEqual(telemetry_v.nodes_evaluated, 1)


if __name__ == '__main__':
    unittest.main()

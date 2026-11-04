import unittest
from src.core.game_logic import GameState, Piece, BEATS, PREDATORS, PIECE_NAMES


class TestGameLogic(unittest.TestCase):
    def test_sut_cycle(self):
        """Verify the rock-paper-scissors cycle: Elephant beats Human, Human beats Ant, Ant beats Elephant."""
        self.assertEqual(BEATS['E'], 'H')
        self.assertEqual(BEATS['H'], 'A')
        self.assertEqual(BEATS['A'], 'E')
        self.assertEqual(PREDATORS['H'], 'E')
        self.assertEqual(PREDATORS['A'], 'H')
        self.assertEqual(PREDATORS['E'], 'A')

    def test_initial_board_setup(self):
        """Verify starting board piece placement."""
        state = GameState(6)
        pieces = state.get_pieces()
        self.assertEqual(len(pieces), 12)  # 6 pieces for p0, 6 for p1
        p0_pieces = [p for p in pieces if p[2] == 0]
        p1_pieces = [p for p in pieces if p[2] == 1]
        self.assertEqual(len(p0_pieces), 6)
        self.assertEqual(len(p1_pieces), 6)

    def test_move_and_undo(self):
        """Verify making a move and undoing it restores identical state."""
        state = GameState(6)
        initial_pieces = set(state.get_pieces())
        moves = state.get_valid_moves(0)
        self.assertTrue(len(moves) > 0)

        move = moves[0]
        state.make_move(move[0], move[1])
        self.assertEqual(state.current_turn, 1)

        state.undo()
        self.assertEqual(state.current_turn, 0)
        self.assertEqual(set(state.get_pieces()), initial_pieces)

    def test_win_condition_reaches_target_corner(self):
        """Verify win occurs immediately when a piece reaches the opponent's star corner."""
        state = GameState(6, custom_setup=True)
        # Place player 0 piece one step away from corner (0, 5)
        state.board[1][5] = Piece(0, 'H')
        state.current_turn = 0

        self.assertIsNone(state.winner)
        state.make_move((1, 5), (0, 5))
        self.assertEqual(state.winner, 0)


if __name__ == '__main__':
    unittest.main()

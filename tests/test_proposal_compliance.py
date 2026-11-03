import math
import unittest
from unittest.mock import patch, Mock

from ai_engine import get_defender_move
from game_logic import GameState, Piece
from puzzle_logic import (generate_benchmark_corpus, verify_puzzle, bfs_safe_path,
                          ShortestPathScriptedPlayer, run_simulation_benchmark,
                          make_puzzle_move, PuzzleSession)
from run_benchmark import parse_args
from views.puzzle_game_view import PuzzleGameView


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

    def test_defender_delays_an_unavoidable_corner_win(self):
        state = GameState(3, custom_setup=True)
        state.board[0][1] = Piece(0, 'H')
        state.board[1][2] = Piece(1, 'H')
        state.current_turn = 1
        move, _, telemetry = get_defender_move(state, depth=5)
        # Other moves allow an immediate win. Occupying the corner forces a detour.
        self.assertEqual(move, ((1, 2), (0, 2)))
        self.assertEqual(telemetry.completed_depth, 5)


class TestVerificationCompliance(unittest.TestCase):
    def test_static_route_does_not_prove_win_against_moving_predator(self):
        pieces = [(2, 0, 0, 'H'), (0, 1, 1, 'E')]
        static_steps, _ = bfs_safe_path(3, pieces, (2, 0), (0, 2), 'H', False)
        self.assertEqual(static_steps, 2)
        result = verify_puzzle(3, pieces, max_steps=3)
        self.assertEqual(result['status'], 'NO_WIN_WITHIN_LIMIT')
        self.assertIsNone(result['steps'])

    def test_adversarial_solver_finds_shortest_forced_win(self):
        pieces = [(2, 0, 0, 'H'), (0, 0, 1, 'H')]
        result = verify_puzzle(3, pieces, max_steps=3)
        self.assertEqual(result['status'], 'VERIFIED')
        self.assertEqual(result['method'], 'adversarial')
        self.assertEqual(result['steps'], 2)
        self.assertEqual(result['path'], [(2, 0), (1, 1), (0, 2)])
        self.assertEqual(verify_puzzle(3, pieces, max_steps=1)['status'],
                         'NO_WIN_WITHIN_LIMIT')

    def test_budget_exhaustion_is_unknown_not_unwinnable(self):
        result = verify_puzzle(3, [(2, 0, 0, 'H'), (0, 0, 1, 'H')], node_budget=0)
        self.assertEqual(result['status'], 'UNVERIFIED')
        self.assertIsNone(result['steps'])

    def test_random_corpus_is_reproducible_diverse_and_exactly_ten_steps(self):
        first = generate_benchmark_corpus(20, seed=42)
        second = generate_benchmark_corpus(20, seed=42)
        self.assertEqual([s.to_dict() for s in first], [s.to_dict() for s in second])
        self.assertGreater(len({s.id for s in first}), 1)
        for scenario in first:
            proof = verify_puzzle(scenario.board_size, scenario.pieces, max_steps=10)
            self.assertEqual(proof['status'], 'VERIFIED')
            self.assertEqual(proof['steps'], 10)
            self.assertEqual(len(scenario.optimal_path) - 1, 10)
            self.assertEqual(verify_puzzle(scenario.board_size, scenario.pieces,
                                          max_steps=9)['status'], 'NO_WIN_WITHIN_LIMIT')

    def test_invalid_positions_are_rejected(self):
        with self.assertRaises(ValueError):
            verify_puzzle(3, [(1, 1, 0, 'H'), (1, 1, 1, 'E')])
        with self.assertRaises(ValueError):
            generate_benchmark_corpus(1, board_size=6)


class TestBenchmarkCompliance(unittest.TestCase):
    def test_cli_and_simulator_really_accept_one_thousand_games(self):
        self.assertEqual(parse_args([]).games, 1000)
        corpus = generate_benchmark_corpus(1000)
        progress = Mock()
        # All attempts fail immediately: exercise the actual 1,000-game loop
        # and undefined delay margin, without running a lengthy experiment.
        with patch.object(ShortestPathScriptedPlayer, 'select_move', return_value=None):
            result = run_simulation_benchmark('baseline_1_random', corpus=corpus,
                                              progress_callback=progress)
        self.assertEqual(result['total_games'], 1000)
        self.assertEqual(result['neutralized_count'], 1000)
        self.assertEqual(result['neutralization_rate'], 100)
        self.assertIsNone(result['delay_margin'])
        self.assertEqual(progress.call_count, 1000)
        progress.assert_called_with(1000, 1000)

    def test_unverified_or_wrong_length_corpus_is_rejected(self):
        corpus = generate_benchmark_corpus(1)
        corpus[0].pieces[0] = (9, 8, 0, 'H')
        with self.assertRaises(ValueError):
            run_simulation_benchmark('baseline_1_random', num_games=1, corpus=corpus)

    def test_shortest_player_avoids_the_old_greedy_detour(self):
        state = GameState(6, custom_setup=True)
        state.board[5][0] = Piece(0, 'H')
        blockers = [(2, 4), (0, 3), (1, 2), (0, 4), (2, 5), (4, 4),
                    (3, 1), (0, 2), (4, 1), (3, 5), (2, 1), (5, 4)]
        for r, c in blockers:
            state.board[r][c] = Piece(1, 'H')
        self.assertEqual(ShortestPathScriptedPlayer().select_move(state), ((5, 0), (5, 1)))

    def test_capturing_last_defender_still_requires_reaching_the_corner(self):
        state = GameState(3, custom_setup=True)
        state.board[2][0] = Piece(0, 'H')
        state.board[1][1] = Piece(1, 'A')
        make_puzzle_move(state, (2, 0), (1, 1))
        self.assertIsNone(state.winner)
        self.assertEqual(state.current_turn, 0)
        make_puzzle_move(state, (1, 1), (0, 2))
        self.assertEqual(state.winner, 0)


class TestPuzzleControls(unittest.TestCase):
    def test_undo_pending_reply_preserves_the_previous_round(self):
        view = object.__new__(PuzzleGameView)
        view.config = {'undo_enabled': True}
        view.is_game_active = True
        scenario = generate_benchmark_corpus(1)[0]
        view.session = PuzzleSession(scenario)
        view.state = GameState(6, custom_setup=True)
        view.state.board[5][0] = Piece(0, 'H')
        view.state.board[0][0] = Piece(1, 'A')
        make_puzzle_move(view.state, (5, 0), (4, 1))
        make_puzzle_move(view.state, (0, 0), (0, 1))
        expected = view.state.to_dict()
        make_puzzle_move(view.state, (4, 1), (3, 2))
        view.session.current_attempt_steps = 2
        view.ai_timer_id = 'pending-reply'
        view.after_cancel = Mock()
        view._update_ui_state = Mock()
        view._on_undo()
        view.after_cancel.assert_called_once_with('pending-reply')
        self.assertEqual(view.state.current_turn, 0)
        self.assertEqual(view.state.to_dict()['board'], expected['board'])
        self.assertEqual(view.session.current_attempt_steps, 1)
        self.assertIsNone(view.ai_timer_id)


if __name__ == '__main__':
    unittest.main()

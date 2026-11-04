import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import storage
from ai_engine import SearchTelemetry
from competition import CompetitionAttempt, calculate_score, challenge_key
from game_logic import GameState
from puzzle_logic import generate_benchmark_corpus, PuzzleSession
from views.puzzle_game_view import PuzzleGameView
from views.competition_view import CompetitionView


class TestCompetition(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.db = Path(directory.name) / 'scores.json'
        patcher = patch.multiple(storage, DB_FILE=str(self.db),
                                 CONFIG_FILE=str(Path(directory.name) / 'profiles.json'))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.now = [0.0]
        self.attempt = CompetitionAttempt(clock=lambda: self.now[0])

    def test_score_and_strict_four_minute_boundary(self):
        self.assertEqual(calculate_score(True, 10, 30), 900)
        self.assertEqual(calculate_score(True, 14, 20), 860)
        self.assertEqual(calculate_score(False, 1, 10), 0)
        self.assertEqual(calculate_score(True, 10, 239.999), 900)
        self.assertEqual(calculate_score(True, 10, 240), 0)
        self.now[0] = 240
        self.assertTrue(self.attempt.expired)
        result = self.attempt.finish(True, 10)
        self.assertFalse(result['solved'])
        self.assertEqual(result['score'], 0)
        self.now[0] = 300
        self.assertEqual(self.attempt.elapsed_seconds, 240)

    def test_standings_prioritize_score_then_time_and_preserve_old_data(self):
        old = {'pvp': {'Archived Player': {'wins': 2}}, 'pve': [{'id': 'old'}]}
        self.db.write_text(json.dumps(old), encoding='utf-8')
        storage.save_competition_score('round', 'A', 10, 30, True)
        storage.save_competition_score('round', 'B', 14, 10, True)
        storage.save_competition_score('round', 'C', 10, 20, True)
        storage.save_competition_score('round', 'D', 0, 1, False)
        rows = storage.get_competition_leaderboard('round')
        self.assertEqual([r['username'] for r in rows], ['C', 'A', 'B', 'D'])
        with self.assertRaises(ValueError):
            storage.save_competition_score('round', ' a ', 5, 5, True)
        storage.save_competition_score('other-round', 'A', 10, 20, True)
        storage.clear_competition_round('round')
        self.assertEqual(storage.get_competition_leaderboard('round'), [])
        self.assertEqual(len(storage.get_competition_leaderboard('other-round')), 1)
        db = json.loads(self.db.read_text(encoding='utf-8'))
        self.assertEqual(db['pvp'], old['pvp'])
        self.assertEqual(db['pve'], old['pve'])

    def make_view(self):
        view = object.__new__(PuzzleGameView)
        view.is_competition = True
        view.is_game_active = True
        view.competition_attempt = self.attempt
        view.competition_result = None
        view.competition_timer_id = None
        view.ai_timer_id = None
        view._resize_job = None
        view.scenario = generate_benchmark_corpus(1)[0]
        view.session = PuzzleSession(view.scenario)
        view.config = {'p1_name': 'A'}
        view.state = GameState(3)
        view._handle_puzzle_finish = Mock()
        return view

    def test_expired_input_is_rejected_before_the_board_changes(self):
        view = self.make_view()
        self.now[0] = 240
        before = view.state.to_dict()
        view._execute_player_move((2, 0), (1, 1))
        self.assertEqual(view.state.to_dict(), before)
        view._handle_puzzle_finish.assert_called_once_with(False, 'Time limit reached')

    def test_ai_overrun_cannot_apply_a_late_move(self):
        view = self.make_view()
        view.state.current_turn = 1
        view.after = Mock()
        before = view.state.to_dict()
        self.now[0] = 239.5

        def finish_search(**kwargs):
            self.now[0] = 240.1
            return ((0, 2), (1, 1)), 0, SearchTelemetry()

        with patch('views.puzzle_game_view.get_defender_move', side_effect=finish_search) as search:
            view._trigger_ai_move()
        self.assertAlmostEqual(search.call_args.kwargs['time_budget'], 0.45)
        self.assertEqual(view.state.to_dict(), before)
        view.after.assert_not_called()
        view._handle_puzzle_finish.assert_called_once_with(False, 'Time limit reached')

    def test_cleanup_records_a_forfeit_once_and_controls_cannot_reset(self):
        view = self.make_view()
        view._unbind_hotkeys = Mock()
        view.after_cancel = Mock()
        self.now[0] = 10
        view._on_undo()
        view._on_reset_attempt()
        self.assertEqual(view.competition_attempt.started_at, 0)
        view._cleanup()
        view._cleanup()
        records = storage.get_competition_leaderboard(challenge_key(view.scenario))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['score'], 0)
        self.assertEqual(records[0]['reason'], 'Left game')

    def test_setup_rejects_repeat_player_and_uses_fixed_ai(self):
        view = object.__new__(CompetitionView)
        view.challenges = generate_benchmark_corpus(3)
        view.var_challenge = Mock(get=Mock(return_value='Challenge 1'))
        view.var_name = Mock(get=Mock(return_value=' A '))
        view.lbl_status = Mock()
        view.app = Mock()
        view._start_game()
        config = view.app.start_puzzle.call_args.args[0]
        self.assertTrue(config['competition'])
        self.assertEqual(config['p1_name'], 'A')
        self.assertEqual((config['agent_model'], config['search_depth']), ('proposed_d6', 6))
        storage.save_competition_score(challenge_key(view.challenges[0]), 'A', 10, 30, True)
        view.app.reset_mock()
        view._start_game()
        view.app.start_puzzle.assert_not_called()


if __name__ == '__main__':
    unittest.main()

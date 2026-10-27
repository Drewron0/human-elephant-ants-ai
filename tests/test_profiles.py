import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import storage
from game_logic import GameState
from views.config_view import ConfigView
from views.game_view import GameView
from views.leaderboard_view import LeaderboardView


class TestProfiles(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.db = Path(directory.name) / 'leaderboard.json'
        self.saves = Path(directory.name) / 'saved_games.json'
        paths = patch.multiple(storage, DB_FILE=str(self.db), SAVES_FILE=str(self.saves),
                               CONFIG_FILE=str(Path(directory.name) / 'app_config.json'))
        paths.start()
        self.addCleanup(paths.stop)

    def test_scores_remember_all_names_as_normal_profiles(self):
        for name in ('Player 2', 'Guest_1234', '   '):
            with self.subTest(name=name):
                expected = name.strip() or 'Player'
                record_id = storage.save_pve_score(name, 10, 30, 0)
                record = next(r for r in storage.get_pve_leaderboard() if r['id'] == record_id)
                self.assertEqual(record['username'], expected)
                self.assertNotIn('is_guest', record)
                self.assertEqual(storage.get_last_username(), expected)

                record_id = storage.save_stage_score('stage', name, 6, 15, 0, 0)
                record = next(r for r in storage.get_stage_leaderboard('stage') if r['id'] == record_id)
                self.assertEqual(record['username'], expected)
                self.assertNotIn('is_guest', record)
                self.assertIn(expected, storage.get_recent_profiles())

    def test_adding_scores_preserves_old_records(self):
        old = {'id': 'old', 'username': 'Guest_1234', 'is_guest': True,
               'turns': 10, 'steps': 6, 'time_spent': 15, 'time_left': 30,
               'undos': 0, 'delay_margin': 0, 'timestamp': '2026-10-27 12:00'}
        self.db.write_text(json.dumps({'pve': [old], 'stages': {'stage': [old]}}), encoding='utf-8')
        storage.save_pve_score('Felix', 12, 20, 0)
        storage.save_stage_score('stage', 'Felix', 7, 20, 0, 1)
        self.assertIn(old, storage.get_pve_leaderboard())
        self.assertIn(old, storage.get_stage_leaderboard('stage'))
        self.assertEqual(len(storage.get_pve_leaderboard()), 2)
        self.assertEqual(len(storage.get_stage_leaderboard('stage')), 2)

    def test_old_leaderboard_flags_do_not_add_badges(self):
        old = {'id': 'old', 'username': 'Guest_1234', 'is_guest': True,
               'turns': 10, 'time_left': 30, 'undos': 0, 'timestamp': '2026-10-27 12:00'}
        self.db.write_text(json.dumps({'pve': [old]}), encoding='utf-8')
        view = object.__new__(LeaderboardView)
        view.tree = MagicMock()
        view.tree.get_children.return_value = []
        view.current_tab = 'pve'
        view.sort_by = 'turns'
        view.difficulty_category = 'all'
        view._refresh_table()
        self.assertEqual(view.tree.insert.call_args.kwargs['values'][1], 'Guest_1234')

    def test_old_saved_games_keep_names_and_load(self):
        original = {
            'config': {'mode': 'PvP', 'pvp_type': 'Local', 'p1_name': 'Guest_1234',
                       'p2_name': 'Felix', 'is_guest_1': True, 'is_guest_2': False},
            'state': GameState().to_dict(), 'p1_time': 80, 'p2_time': 90
        }
        self.saves.write_text(json.dumps({'old': original}), encoding='utf-8')
        loaded = storage.get_saved_slots()['old']
        with patch('tkinter.Frame.__init__', return_value=None), \
                patch.object(GameView, '_build_ui'), patch.object(GameView, '_bind_hotkeys'), \
                patch.object(GameView, '_start_timer'):
            view = GameView(None, Mock(), loaded['config'], saved_state=loaded)
        self.assertEqual(view.config['p1_name'], 'Guest_1234')
        self.assertEqual(view.state.to_dict(), original['state'])
        self.assertEqual((view.time_p1, view.time_p2), (80, 90))
        self.assertEqual(json.loads(self.saves.read_text(encoding='utf-8'))['old'], original)

    def test_match_setup_remembers_names_without_guest_handling(self):
        view = SimpleNamespace(mode='PvE', app=Mock())
        for field, value in {
            'var_p1_name': 'Guest_1234', 'var_p1_color': 'Emerald Green',
            'var_p2_color': 'Ruby Red', 'var_time': '2 Minutes', 'var_undo': True,
            'var_pve_engine': 'Standard Minimax', 'seg_difficulty': 'Normal'
        }.items():
            setattr(view, field, Mock(get=Mock(return_value=value)))
        ConfigView._start_game(view)
        config = view.app.start_game.call_args.args[0]
        self.assertEqual(config['p1_name'], 'Guest_1234')
        self.assertNotIn('is_guest_1', config)
        self.assertNotIn('is_guest_2', config)
        self.assertEqual(storage.get_last_username(), 'Guest_1234')


if __name__ == '__main__':
    unittest.main()

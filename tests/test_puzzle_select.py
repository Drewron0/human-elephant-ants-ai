import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import storage
from puzzle_logic import get_all_puzzles, verify_puzzle
from views.puzzle_select_view import PuzzleSelectView
from views.puzzle_game_view import PuzzleGameView


class TestPuzzleSelect(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.app = SimpleNamespace(show_view=Mock(), start_puzzle=Mock())
        paths = patch.multiple(storage,
            CUSTOM_STAGES_FILE=str(Path(directory.name) / 'stages.json'),
            CONFIG_FILE=str(Path(directory.name) / 'profiles.json'),
            DB_FILE=str(Path(directory.name) / 'scores.json'))
        paths.start()
        self.addCleanup(paths.stop)
        for name in ('tk.Label', 'tk.Frame', 'tk.Canvas', 'draw_board_thumbnail', 'bind_mousewheel'):
            patcher = patch('views.puzzle_select_view.' + name)
            patcher.start()
            self.addCleanup(patcher.stop)
        pieces = [(2, 0, 0, 'H'), (0, 0, 1, 'H')]
        proof = verify_puzzle(3, pieces, max_steps=3)
        self.payload = dict(id='my_stage', title='My Stage', board_size=3, pieces=pieces,
            s_optimal=proof['steps'], optimal_path=proof['path'], optimal_moves=proof['moves'],
            verification_status=proof['status'], verification_method=proof['method'],
            verification_key=proof['position_key'], is_custom=True)

    def make_view(self):
        view = object.__new__(PuzzleSelectView)
        view.app = self.app
        view.scrollable_grid = Mock()
        view.scrollable_grid.winfo_children.return_value = []
        view.grid_canvas = Mock()
        view.card_widgets = {}
        view.selected_puzzle_id = ''
        view.btn_play = Mock()
        view.lbl_selected_title = Mock()
        view.lbl_selected_desc = Mock()
        view.lbl_selected_stats = Mock()
        view.frame_custom_actions = Mock()
        view.box_leaderboard = Mock()
        view.box_leaderboard.winfo_children.return_value = []
        view.var_player_name = Mock(get=Mock(return_value='Felix'))
        view.var_ai_model = Mock(get=Mock(return_value='Optimized (Alpha-Beta d=6)'))
        view.var_show_metrics = Mock(get=Mock(return_value=False))
        return view

    def test_empty_storage_never_offers_a_builtin_or_random_stage(self):
        self.assertEqual(get_all_puzzles(), {})
        view = self.make_view()
        view.selected_puzzle_id = 'stage_6x6_01'
        view._populate_grid()
        self.assertEqual(view.card_widgets, {})
        self.assertEqual(view.selected_puzzle_id, '')
        view.btn_play.config.assert_called_with(state='disabled')
        view.lbl_selected_stats.config.assert_called_with(text='')
        view._start_selected_stage()
        self.app.start_puzzle.assert_not_called()

    def test_only_saved_custom_stages_are_listed_and_can_be_launched(self):
        storage.save_custom_stage(self.payload)
        view = self.make_view()
        view._populate_grid()
        self.assertEqual(list(view.card_widgets), ['my_stage'])
        self.assertEqual(view.selected_puzzle_id, 'my_stage')
        view.btn_play.config.assert_called_with(state='normal')
        view._start_selected_stage()
        config = self.app.start_puzzle.call_args.args[0]
        self.assertEqual(config['puzzle_scenario'], 'my_stage')
        self.assertEqual(config['custom_scenario_obj'].pieces, self.payload['pieces'])
        self.assertEqual(config['p1_name'], 'Felix')
        self.assertEqual(config['search_depth'], 6)
        self.assertEqual(storage.get_last_username(), 'Felix')

    def test_unverified_custom_stage_can_be_edited_but_not_played(self):
        storage.save_custom_stage(dict(self.payload, verification_key='stale'))
        view = self.make_view()
        view._populate_grid()
        view.btn_play.config.assert_called_with(state='disabled')
        self.assertIn('verify', view.lbl_selected_stats.config.call_args.kwargs['text'])
        view._start_selected_stage()
        self.app.start_puzzle.assert_not_called()
        view._edit_selected_stage()
        self.app.show_view.assert_called_once()
        self.assertEqual(self.app.show_view.call_args.args[0], 'stage_editor')
        self.assertEqual(self.app.show_view.call_args.kwargs['edit_stage']['id'], 'my_stage')

    def test_create_action_opens_the_editor(self):
        self.make_view()._open_stage_editor()
        self.app.show_view.assert_called_once_with('stage_editor')

    def test_delete_last_stage_returns_to_the_empty_state(self):
        storage.save_custom_stage(self.payload)
        view = self.make_view()
        view._populate_grid()
        with patch('views.puzzle_select_view.ThemedModal'), \
                patch('views.puzzle_select_view.ButtonSecondary'), \
                patch('views.puzzle_select_view.ButtonDanger') as delete_button:
            view._delete_selected_stage()
            delete_button.call_args.kwargs['command']()
        self.assertEqual(storage.get_custom_stages(), [])
        self.assertEqual(view.card_widgets, {})
        self.assertEqual(view.selected_puzzle_id, '')
        view.btn_play.config.assert_called_with(state='disabled')
        view.frame_custom_actions.pack_forget.assert_called()

    def test_saved_stage_source_is_custom_even_for_older_metadata(self):
        storage.save_custom_stage(dict(self.payload, is_custom=False))
        catalog = get_all_puzzles()
        self.assertEqual(list(catalog), ['my_stage'])
        self.assertTrue(catalog['my_stage'].is_custom)

    def test_game_launch_has_no_preset_or_random_fallback(self):
        with patch.object(PuzzleGameView.__bases__[0], '__init__', return_value=None):
            with self.assertRaisesRegex(ValueError, 'existing custom stage'):
                PuzzleGameView(None, self.app, {'puzzle_scenario': 'stage_6x6_01'})


if __name__ == '__main__':
    unittest.main()

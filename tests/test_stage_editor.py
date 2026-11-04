import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from puzzle_logic import PuzzleScenario
from views.stage_editor_view import StageEditorView


class TestStageEditor(unittest.TestCase):
    def make_editor(self):
        editor = object.__new__(StageEditorView)
        editor.board_size = 6
        editor.current_sq_size = 70
        editor.placed_pieces = {(5, 0): (0, 'H'), (2, 3): (1, 'E')}
        editor.active_tool = 'P1_E'
        editor.var_minimum_steps = Mock(get=Mock(return_value='6'))
        editor.lbl_save_error = Mock()
        editor.entry_minimum_steps = Mock()
        editor._draw_board = Mock()
        editor.var_title = Mock(get=Mock(return_value='Test Stage'))
        editor.var_desc = Mock(get=Mock(return_value='Test description'))
        editor.edit_stage_id = None
        editor.app = Mock()
        return editor

    def test_new_minimum_is_blank_and_editing_prefills_saved_value(self):
        with patch('tkinter.Frame.__init__', return_value=None), \
                patch.object(StageEditorView, '_build_ui'), \
                patch.object(StageEditorView, '_bind_shortcuts'), \
                patch('puzzle_logic.verify_puzzle') as verify:
            new = StageEditorView(None, Mock())
            saved = StageEditorView(None, Mock(), edit_stage=dict(
                id='saved', s_optimal=6, pieces=[[5, 0, 0, 'H']]))
        self.assertEqual(new.stage_minimum, '')
        self.assertEqual(saved.stage_minimum, '6')
        self.assertEqual(saved.edit_stage_id, 'saved')
        verify.assert_not_called()

    @patch('views.stage_editor_view.storage.save_custom_stage')
    @patch('puzzle_logic.find_optimal_winning_path', side_effect=AssertionError('Static search called'))
    @patch('puzzle_logic.verify_puzzle', side_effect=AssertionError('Verification called'))
    def test_save_uses_the_entered_minimum_without_searching(self, verify, static, save):
        editor = self.make_editor()
        editor._save_stage()
        save.assert_called_once()
        payload = save.call_args.args[0]
        self.assertEqual(payload['s_optimal'], 6)
        self.assertEqual(payload['minimum_source'], 'manual')
        self.assertNotIn('verification_key', payload)
        self.assertNotIn('verification_status', payload)
        loaded = PuzzleScenario.from_dict(payload)
        self.assertEqual(loaded.s_optimal, 6)
        self.assertEqual(loaded.s_max, 18)
        self.assertEqual(loaded.step_summary, 'Minimum (user-entered): 6 steps')
        self.assertEqual(PuzzleScenario.from_dict(loaded.to_dict()).s_optimal, 6)
        verify.assert_not_called()
        static.assert_not_called()
        editor.app.show_view.assert_called_once_with('puzzle_select')

    @patch('views.stage_editor_view.storage.save_custom_stage')
    def test_edit_saves_the_new_count_under_the_existing_stage_id(self, save):
        editor = self.make_editor()
        editor.edit_stage_id = 'saved'
        editor.var_minimum_steps.get.return_value = ' 7 '
        editor._save_stage()
        self.assertEqual(save.call_args.args[0]['id'], 'saved')
        self.assertEqual(save.call_args.args[0]['s_optimal'], 7)

    @patch('views.stage_editor_view.storage.save_custom_stage')
    def test_invalid_minimum_does_not_save(self, save):
        for value in ('', '0', '-1', '2.5', 'abc'):
            with self.subTest(value=value):
                editor = self.make_editor()
                editor.var_minimum_steps.get.return_value = value
                editor._save_stage()
                self.assertIn('positive whole number', editor.lbl_save_error.config.call_args.kwargs['text'])
                editor.entry_minimum_steps.focus_set.assert_called_once()
                editor.app.show_view.assert_not_called()
        save.assert_not_called()

    @patch('views.stage_editor_view.storage.save_custom_stage')
    def test_board_still_requires_a_player_piece(self, save):
        editor = self.make_editor()
        editor.placed_pieces = {(2, 3): (1, 'E')}
        editor._save_stage()
        save.assert_not_called()
        self.assertIn('player piece', editor.lbl_save_error.config.call_args.kwargs['text'])

    def test_board_changes_leave_the_entered_minimum_alone(self):
        event = SimpleNamespace(x=3 * 70, y=2 * 70)
        for action in ('place', 'erase', 'right_click', 'resize', 'reset'):
            with self.subTest(action=action):
                editor = self.make_editor()
                if action in ('place', 'erase'):
                    editor.active_tool = 'P0_A' if action == 'place' else 'ERASER'
                    editor._on_canvas_click(event)
                elif action == 'right_click':
                    editor._on_canvas_right_click(event)
                elif action == 'resize':
                    editor.var_size = Mock(get=Mock(return_value='7x7'))
                    editor.left_pane = Mock()
                    editor.left_pane.winfo_width.return_value = 500
                    editor.left_pane.winfo_height.return_value = 500
                    editor._apply_pane_resize = Mock()
                    editor._on_size_change()
                else:
                    editor._clear_board()
                editor.var_minimum_steps.set.assert_not_called()

    def test_typing_numbers_in_text_fields_does_not_change_board_tool(self):
        editor = self.make_editor()
        editor._set_tool = Mock()
        for widget_class in ('Entry', 'TEntry', 'TCombobox'):
            editor._on_tool_key(SimpleNamespace(widget=Mock(winfo_class=Mock(return_value=widget_class))), 'P0_H')
        editor._set_tool.assert_not_called()
        editor._on_tool_key(SimpleNamespace(widget=Mock(winfo_class=Mock(return_value='Canvas'))), 'P0_H')
        editor._set_tool.assert_called_once_with('P0_H')


if __name__ == '__main__':
    unittest.main()

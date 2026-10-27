import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from views.stage_editor_view import StageEditorView


class TestStageEditor(unittest.TestCase):
    def make_editor(self):
        editor = object.__new__(StageEditorView)
        editor.board_size = 6
        editor.current_sq_size = 70
        editor.placed_pieces = {(5, 0): (0, 'H'), (2, 3): (1, 'E')}
        editor.active_tool = 'P1_E'
        editor.last_verification = {'winnable': True, 's_optimal': 5}
        editor.lbl_verify_status = Mock()
        editor.lbl_verify_detail = Mock()
        editor._draw_board = Mock()
        return editor

    @patch('views.stage_editor_view.find_optimal_winning_path')
    def test_opening_editor_does_not_solve(self, solve):
        with patch('tkinter.Frame.__init__', return_value=None), \
                patch.object(StageEditorView, '_build_ui'), \
                patch.object(StageEditorView, '_bind_shortcuts'):
            editor = StageEditorView(None, Mock())
        solve.assert_not_called()
        self.assertIsNone(editor.last_verification)

    @patch('views.stage_editor_view.find_optimal_winning_path')
    def test_board_changes_invalidate_result_without_solving(self, solve):
        event = SimpleNamespace(x=3 * 70, y=2 * 70)
        for action in ('place', 'erase', 'right_click', 'resize', 'reset'):
            with self.subTest(action=action):
                editor = self.make_editor()
                if action in ('place', 'erase'):
                    editor.active_tool = 'P0_A' if action == 'place' else 'ERASER'
                    editor._on_canvas_click(event)
                    self.assertEqual(editor.placed_pieces.get((2, 3)),
                                     (0, 'A') if action == 'place' else None)
                elif action == 'right_click':
                    editor._on_canvas_right_click(event)
                    self.assertNotIn((2, 3), editor.placed_pieces)
                elif action == 'resize':
                    editor.var_size = Mock(get=Mock(return_value='7x7'))
                    editor.left_pane = Mock()
                    editor.left_pane.winfo_width.return_value = 500
                    editor.left_pane.winfo_height.return_value = 500
                    editor._apply_pane_resize = Mock()
                    editor._on_size_change()
                    self.assertEqual(editor.board_size, 7)
                else:
                    editor._clear_board()
                    self.assertEqual(len(editor.placed_pieces), 5)
                self.assertIsNone(editor.last_verification)
                self.assertIn('Unverified', editor.lbl_verify_status.config.call_args.kwargs['text'])
                solve.assert_not_called()

    @patch('views.stage_editor_view.storage.save_custom_stage')
    @patch('views.stage_editor_view.find_optimal_winning_path',
           return_value=(5, [(5, 0), (0, 5)], (5, 0, 'H')))
    def test_manual_check_and_save_still_verify(self, solve, save):
        editor = self.make_editor()
        self.assertTrue(editor._verify_winnability(silent=True))
        solve.assert_called_once()
        self.assertEqual(editor.last_verification['s_optimal'], 5)

        editor._invalidate_verification()
        editor.var_title = Mock(get=Mock(return_value='Test Stage'))
        editor.var_desc = Mock(get=Mock(return_value='Test description'))
        editor.edit_stage_id = None
        editor.app = Mock()
        editor._save_stage()
        self.assertEqual(solve.call_count, 2)
        self.assertEqual(save.call_args.args[0]['s_optimal'], 5)


if __name__ == '__main__':
    unittest.main()

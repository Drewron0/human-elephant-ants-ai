import unittest
from queue import Queue
from threading import Thread, get_ident
from types import SimpleNamespace
from unittest.mock import Mock, patch

from views.stage_editor_view import StageEditorView, _verify_stage
from puzzle_logic import verify_puzzle, puzzle_position_key


class TestStageEditor(unittest.TestCase):
    def make_editor(self):
        editor = object.__new__(StageEditorView)
        editor.board_size = 6
        editor.current_sq_size = 70
        editor.placed_pieces = {(5, 0): (0, 'H'), (2, 3): (1, 'E')}
        editor.active_tool = 'P1_E'
        editor.last_verification = None
        editor._verification_queue = Queue()
        editor._verification_running = False
        editor._verification_poll_id = None
        editor._verification_key = None
        editor._save_after_verification = False
        editor._closed = False
        editor.after = Mock(return_value='poll')
        editor.after_cancel = Mock()
        editor.lbl_verify_status = Mock()
        editor.lbl_verify_detail = Mock()
        editor._draw_board = Mock()
        editor.var_title = Mock(get=Mock(return_value='Test Stage'))
        editor.var_desc = Mock(get=Mock(return_value='Test description'))
        editor.edit_stage_id = None
        editor.app = Mock()
        return editor

    def winning_editor(self):
        editor = self.make_editor()
        editor.board_size = 3
        editor.placed_pieces = {(2, 0): (0, 'H'), (0, 0): (1, 'H')}
        return editor

    def deliver(self, editor, result):
        pieces = [(r, c, owner, pt) for (r, c), (owner, pt) in editor.placed_pieces.items()]
        editor._verification_queue.put((puzzle_position_key(editor.board_size, pieces), result))
        editor._poll_verification()

    @patch('views.stage_editor_view.verify_puzzle')
    def test_opening_editor_does_not_solve(self, solve):
        with patch('tkinter.Frame.__init__', return_value=None), \
                patch.object(StageEditorView, '_build_ui'), \
                patch.object(StageEditorView, '_bind_shortcuts'):
            editor = StageEditorView(None, Mock())
        solve.assert_not_called()
        self.assertIsNone(editor.last_verification)

    @patch('views.stage_editor_view.verify_puzzle')
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
    @patch('views.stage_editor_view.threading.Thread')
    def test_save_verifies_first_and_persists_the_exact_result(self, thread, save):
        editor = self.winning_editor()
        editor._save_stage()
        save.assert_not_called()
        thread.return_value.start.assert_called_once()
        result = verify_puzzle(3, [(2, 0, 0, 'H'), (0, 0, 1, 'H')], max_steps=3)
        self.deliver(editor, result)
        payload = save.call_args.args[0]
        self.assertEqual(payload['s_optimal'], 2)
        self.assertEqual(payload['verification_status'], 'VERIFIED')
        self.assertEqual(payload['verification_key'], result['position_key'])
        self.assertEqual(payload['optimal_moves'], result['moves'])
        editor.app.show_view.assert_called_once_with('puzzle_select')

    @patch('views.stage_editor_view.storage.save_custom_stage')
    @patch('views.stage_editor_view.threading.Thread')
    def test_manual_verification_is_reused_when_saving(self, thread, save):
        editor = self.winning_editor()
        editor._verify_winnability()
        result = verify_puzzle(3, [(2, 0, 0, 'H'), (0, 0, 1, 'H')], max_steps=3)
        self.deliver(editor, result)
        save.assert_not_called()
        editor._save_stage()
        save.assert_called_once()
        thread.assert_called_once()

    @patch('views.stage_editor_view.storage.save_custom_stage')
    @patch('views.stage_editor_view.threading.Thread')
    def test_unknown_and_negative_results_cannot_save(self, thread, save):
        for status in ('UNVERIFIED', 'NO_WIN_WITHIN_LIMIT', 'ERROR'):
            with self.subTest(status=status):
                editor = self.winning_editor()
                editor._save_stage()
                self.deliver(editor, dict(status=status, reason='No forced-win proof'))
                self.assertIsNone(editor.last_verification)
                self.assertIn('No minimum assigned', editor.lbl_verify_detail.config.call_args.kwargs['text'])
        save.assert_not_called()

    @patch('views.stage_editor_view.storage.save_custom_stage')
    @patch('views.stage_editor_view.threading.Thread')
    def test_board_edit_discards_in_flight_result_and_does_not_save(self, thread, save):
        editor = self.winning_editor()
        editor._save_stage()
        pieces = [(2, 0, 0, 'H'), (0, 0, 1, 'H')]
        result = verify_puzzle(3, pieces, max_steps=3)
        editor._verification_queue.put((puzzle_position_key(3, pieces), result))
        editor.placed_pieces[(0, 1)] = (1, 'E')
        editor._poll_verification()
        self.assertIsNone(editor.last_verification)
        save.assert_not_called()

    @patch('views.stage_editor_view.verify_puzzle')
    def test_creation_verification_runs_off_ui_thread(self, verify):
        thread_ids = []
        result = dict(status='UNVERIFIED', reason='Budget exhausted')
        def check(*args, **kwargs):
            thread_ids.append(get_ident())
            return result
        verify.side_effect = check
        results = Queue()
        worker = Thread(target=_verify_stage, args=(results, 3, [(2, 0, 0, 'H')]))
        worker.start()
        _, actual = results.get(timeout=2)
        worker.join(timeout=2)
        self.assertIs(actual, result)
        self.assertNotEqual(thread_ids[0], get_ident())
        self.assertEqual(verify.call_args.kwargs['time_budget'], 120.0)
        self.assertEqual(verify.call_args.kwargs['node_budget'], 3000000)

    @patch('views.stage_editor_view.storage.save_custom_stage')
    def test_closing_editor_ignores_late_result(self, save):
        editor = self.winning_editor()
        editor._closed = True
        editor._save_after_verification = True
        result = verify_puzzle(3, [(2, 0, 0, 'H'), (0, 0, 1, 'H')], max_steps=3)
        self.deliver(editor, result)
        save.assert_not_called()

    @patch('views.stage_editor_view.threading.Thread')
    def test_worker_start_failure_clears_busy_state(self, thread):
        thread.return_value.start.side_effect = RuntimeError('Cannot start worker')
        editor = self.winning_editor()
        editor._verify_winnability(silent=True)
        self.assertFalse(editor._verification_running)
        self.assertFalse(editor._save_after_verification)
        self.assertIsNone(editor.last_verification)
        editor.after.assert_not_called()
        self.assertIn('UNVERIFIED', editor.lbl_verify_status.config.call_args.kwargs['text'])


if __name__ == '__main__':
    unittest.main()

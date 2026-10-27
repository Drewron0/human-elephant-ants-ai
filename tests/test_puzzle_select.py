import unittest
from queue import Queue
from threading import Thread, get_ident
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from puzzle_logic import PRECONFIGURED_STAGES_6X6
from views.puzzle_select_view import PuzzleSelectView, _generate_random_challenges


class TestPuzzleSelect(unittest.TestCase):
    def setUp(self):
        self.app = SimpleNamespace(
            random_challenge_queue=Queue(), random_challenge_loading=False,
            random_challenges=None, random_challenge_error=None, start_puzzle=Mock()
        )
        self.puzzles = list(PRECONFIGURED_STAGES_6X6.values())[:3]
        self.mocks = {}
        for name in ('tk.Label', 'tk.Frame', 'tk.Canvas', 'draw_board_thumbnail',
                     'bind_mousewheel', 'threading.Thread', 'get_all_puzzles'):
            patcher = patch('views.puzzle_select_view.' + name)
            self.mocks[name] = patcher.start()
            self.addCleanup(patcher.stop)
        self.mocks['get_all_puzzles'].return_value = PRECONFIGURED_STAGES_6X6

    def make_view(self):
        view = object.__new__(PuzzleSelectView)
        view.app = self.app
        view.active_category = 'preset_6x6'
        view._random_poll_id = None
        view._closed = False
        view.scrollable_grid = Mock()
        view.scrollable_grid.winfo_children.return_value = [Mock()]
        view.grid_canvas = Mock()
        view.card_widgets = {}
        view.selected_puzzle_id = ''
        view._highlight_active_tab = Mock()
        view.after = Mock(return_value='poll')
        view.after_cancel = Mock()
        view._refresh_card_highlights = Mock()
        view._refresh_stage_leaderboard = Mock()
        view.btn_play = Mock()
        view.lbl_selected_title = Mock()
        view.lbl_selected_desc = Mock()
        view.lbl_selected_stats = Mock()
        view.frame_custom_actions = Mock()
        view.box_leaderboard = Mock()
        view.box_leaderboard.winfo_children.return_value = [Mock()]
        return view

    @patch('views.puzzle_select_view.generate_winnable_puzzle')
    def test_random_tab_returns_without_generating_on_ui_thread(self, generate):
        view = self.make_view()
        view._set_category('random')

        generate.assert_not_called()
        self.mocks['threading.Thread'].assert_called_once_with(
            target=_generate_random_challenges,
            args=(self.app.random_challenge_queue,), daemon=True)
        self.mocks['threading.Thread'].return_value.start.assert_called_once()
        self.assertEqual(self.mocks['tk.Label'].call_args.kwargs['text'],
                         'Creating Random Challenge.....')
        self.assertTrue(self.app.random_challenge_loading)
        view.after.assert_called_once_with(100, view._poll_random_challenges)
        view.btn_play.config.assert_called_with(state='disabled')
        view.lbl_selected_stats.config.assert_called_with(text='')
        view.frame_custom_actions.pack_forget.assert_called_once()
        view.box_leaderboard.winfo_children.return_value[0].destroy.assert_called_once()
        view._start_selected_stage()
        self.app.start_puzzle.assert_not_called()

    def test_switching_tabs_keeps_navigation_and_reuses_running_job(self):
        view = self.make_view()
        view._set_category('random')
        view._set_category('preset_6x6')
        view.btn_play.config.assert_called_with(state='normal')
        self.assertEqual(len(view.card_widgets), len(PRECONFIGURED_STAGES_6X6))
        view._set_category('random')
        self.mocks['threading.Thread'].assert_called_once()
        view.after.assert_called_once()

    def test_completion_displays_cards_and_enables_play(self):
        view = self.make_view()
        view._set_category('random')
        self.app.random_challenge_queue.put((self.puzzles, None))
        view.after.call_args.args[1]()

        self.assertIs(self.app.random_challenges, self.puzzles)
        self.assertFalse(self.app.random_challenge_loading)
        self.assertEqual(len(view.card_widgets), 3)
        self.assertEqual(view.selected_puzzle_id, self.puzzles[0].id)
        view.btn_play.config.assert_called_with(state='normal')
        self.assertIsNone(view._random_poll_id)
        view._set_category('random')
        self.mocks['threading.Thread'].assert_called_once()

    def test_completion_on_another_tab_only_caches_results(self):
        view = self.make_view()
        view._set_category('random')
        view._set_category('preset_6x6')
        cards = dict(view.card_widgets)
        self.app.random_challenge_queue.put((self.puzzles, None))
        view.after.call_args.args[1]()

        self.assertEqual(view.active_category, 'preset_6x6')
        self.assertEqual(view.card_widgets, cards)
        view._set_category('random')
        self.assertEqual(len(view.card_widgets), 3)
        self.mocks['threading.Thread'].assert_called_once()

    def test_leaving_screen_cancels_poll_and_new_screen_collects_result(self):
        old_view = self.make_view()
        old_view._set_category('random')
        old_view._cleanup()
        old_view.after_cancel.assert_called_once_with('poll')
        old_view._cleanup()
        old_view.after_cancel.assert_called_once()

        self.app.random_challenge_queue.put((self.puzzles, None))
        old_view._poll_random_challenges()
        self.assertIsNone(self.app.random_challenges)
        self.assertFalse(self.app.random_challenge_queue.empty())

        new_view = self.make_view()
        new_view._set_category('random')
        self.assertEqual(len(new_view.card_widgets), 3)
        self.assertIs(self.app.random_challenges, self.puzzles)
        self.mocks['threading.Thread'].assert_called_once()

    def test_cached_results_survive_reopening_screen(self):
        self.app.random_challenges = self.puzzles
        view = self.make_view()
        view._set_category('random')
        self.assertEqual(len(view.card_widgets), 3)
        self.mocks['threading.Thread'].assert_not_called()
        view.after.assert_not_called()

    @patch('views.puzzle_select_view.storage.save_last_username')
    def test_starting_puzzle_remembers_any_player_name(self, save_name):
        self.app.random_challenges = self.puzzles
        view = self.make_view()
        view._set_category('random')
        view.var_player_name = Mock(get=Mock(return_value='Guest_1234'))
        view.var_ai_model = Mock(get=Mock(return_value='Proposed: Optimized (Alpha-Beta d=6)'))
        view.var_show_metrics = Mock(get=Mock(return_value=False))
        view._start_selected_stage()
        save_name.assert_called_once_with('Guest_1234')
        config = self.app.start_puzzle.call_args.args[0]
        self.assertEqual(config['p1_name'], 'Guest_1234')
        self.assertNotIn('is_guest_1', config)

    def test_generation_failure_is_visible_and_allows_retry(self):
        view = self.make_view()
        view._set_category('random')
        self.app.random_challenge_queue.put((None, 'Test generation failure'))
        view.after.call_args.args[1]()

        self.assertFalse(self.app.random_challenge_loading)
        message = self.mocks['tk.Label'].call_args.kwargs['text']
        self.assertIn('Test generation failure', message)
        self.assertIn('retry', message)
        view._start_selected_stage()
        self.app.start_puzzle.assert_not_called()
        view._set_category('random')
        self.assertEqual(self.mocks['threading.Thread'].call_count, 2)
        self.assertTrue(self.app.random_challenge_loading)
        self.assertIsNone(self.app.random_challenge_error)

    def test_worker_start_failure_does_not_leave_loading_stuck(self):
        self.mocks['threading.Thread'].return_value.start.side_effect = RuntimeError('Cannot start')
        view = self.make_view()
        view._set_category('random')
        self.assertFalse(self.app.random_challenge_loading)
        self.assertIn('Cannot start', self.mocks['tk.Label'].call_args.kwargs['text'])

    @patch('views.puzzle_select_view.generate_winnable_puzzle')
    def test_worker_generates_same_batch_off_main_thread(self, generate):
        worker_threads = []
        puzzles = iter(self.puzzles)

        def generate_puzzle(**kwargs):
            worker_threads.append(get_ident())
            return next(puzzles)

        generate.side_effect = generate_puzzle
        worker = Thread(target=_generate_random_challenges,
                        args=(self.app.random_challenge_queue,), daemon=True)
        worker.start()
        result, error = self.app.random_challenge_queue.get(timeout=2)
        worker.join(timeout=2)

        self.assertEqual(result, self.puzzles)
        self.assertIsNone(error)
        self.assertTrue(all(thread_id != get_ident() for thread_id in worker_threads))
        self.assertEqual(generate.call_args_list, [
            call(board_size=6, min_steps=5, max_steps=7),
            call(board_size=6, min_steps=6, max_steps=8),
            call(board_size=6, min_steps=7, max_steps=10),
        ])

    @patch('views.puzzle_select_view.generate_winnable_puzzle', side_effect=ValueError('Bad board'))
    def test_worker_returns_errors_through_queue(self, generate):
        _generate_random_challenges(self.app.random_challenge_queue)
        self.assertEqual(self.app.random_challenge_queue.get_nowait(), (None, 'Bad board'))


if __name__ == '__main__':
    unittest.main()

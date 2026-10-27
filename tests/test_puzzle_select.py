import unittest
from unittest.mock import Mock, call, patch

from puzzle_logic import PRECONFIGURED_STAGES_6X6
from views.puzzle_select_view import PuzzleSelectView


class TestPuzzleSelect(unittest.TestCase):
    def make_view(self):
        view = object.__new__(PuzzleSelectView)
        view.scrollable_grid = Mock()
        view.scrollable_grid.winfo_children.return_value = [Mock()]
        view.grid_canvas = Mock()
        view.card_widgets = {}
        view.selected_puzzle_id = ''
        view._highlight_active_tab = Mock()
        view.update_idletasks = Mock()
        view._refresh_card_highlights = Mock()
        view._update_sidebar = Mock()
        return view

    @patch('views.puzzle_select_view.bind_mousewheel')
    @patch('views.puzzle_select_view.draw_board_thumbnail')
    @patch('views.puzzle_select_view.tk.Canvas')
    @patch('views.puzzle_select_view.tk.Frame')
    @patch('views.puzzle_select_view.tk.Label')
    @patch('views.puzzle_select_view.generate_winnable_puzzle')
    def test_random_tab_paints_loading_message_before_generation(
            self, generate, label, frame, canvas, draw, bind):
        view = self.make_view()
        loading = Mock()
        label.side_effect = lambda *args, **kwargs: (
            loading if kwargs.get('text') == 'Creating Random Challenge.....' else Mock()
        )
        puzzles = iter(list(PRECONFIGURED_STAGES_6X6.values())[:3])

        def generate_puzzle(**kwargs):
            self.assertEqual(view.active_category, 'random')
            view._highlight_active_tab.assert_called_once()
            view.scrollable_grid.winfo_children.return_value[0].destroy.assert_called_once()
            loading.grid.assert_called_once()
            view.grid_canvas.yview_moveto.assert_called_once_with(0)
            view.update_idletasks.assert_called_once()
            loading.destroy.assert_not_called()
            return next(puzzles)

        generate.side_effect = generate_puzzle
        view._set_category('random')

        self.assertEqual(generate.call_args_list, [
            call(board_size=6, min_steps=5, max_steps=7),
            call(board_size=6, min_steps=6, max_steps=8),
            call(board_size=6, min_steps=7, max_steps=10),
        ])
        loading.destroy.assert_called_once()
        self.assertEqual(len(view.card_widgets), 3)
        view._update_sidebar.assert_called_once()


if __name__ == '__main__':
    unittest.main()

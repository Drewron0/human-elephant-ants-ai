import unittest
from src.ui.app import GameApp


class TestUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = GameApp()
        cls.app.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.app.destroy()

    def test_app_view_navigation(self):
        """Test transitions across all major views in GameApp."""
        views = [
            'menu',
            'config',
            'puzzle_select',
            'stage_editor',
            'benchmark',
            'leaderboard',
            'tutorial'
        ]
        for view_name in views:
            self.app.show_view(view_name)
            self.app.update()
            self.assertIsNotNone(self.app.current_view)


if __name__ == '__main__':
    unittest.main()

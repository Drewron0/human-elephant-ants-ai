import tkinter as tk
from typing import Dict, Any, Optional
from ui_theme import THEME, setup_ttk_styles
from views.menu_view import MainMenuView
from views.config_view import ConfigView
from views.game_view import GameView
from views.leaderboard_view import LeaderboardView
from views.saves_view import SavedGamesView
from views.tutorial_view import TutorialView


class GameApp(tk.Tk):
    """
    Main Application Controller following Single Responsibility Principle.
    Hosts all screens inside a single maximized window.
    """
    def __init__(self):
        super().__init__()
        self.title("Human Elephant Ant: 9x9 Board Game")

        # Open maximized by default on Windows so all contents fit without cutoffs
        try:
            self.state('zoomed')
        except Exception:
            self.geometry("1200x820")

        self.minsize(1050, 720)
        self.configure(bg=THEME['bg'])

        # Initialize dark theme styling for ttk widgets
        setup_ttk_styles(self)

        self.container = tk.Frame(self, bg=THEME['bg'])
        self.container.pack(fill=tk.BOTH, expand=True)

        self.current_view: Optional[tk.Frame] = None
        self.show_view('menu')

    def show_view(self, view_name: str, **kwargs):
        if self.current_view:
            if hasattr(self.current_view, '_cleanup'):
                self.current_view._cleanup()
            self.current_view.destroy()
            self.current_view = None

        if view_name == 'menu':
            self.current_view = MainMenuView(self.container, self)
        elif view_name == 'config':
            mode = kwargs.get('mode', 'PvE')
            self.current_view = ConfigView(self.container, self, mode=mode)
        elif view_name == 'game':
            config = kwargs.get('config', {})
            saved_state = kwargs.get('saved_state', None)
            self.current_view = GameView(self.container, self, config=config, saved_state=saved_state)
        elif view_name == 'leaderboard':
            self.current_view = LeaderboardView(self.container, self)
        elif view_name == 'saves':
            self.current_view = SavedGamesView(self.container, self)
        elif view_name == 'tutorial':
            self.current_view = TutorialView(self.container, self)

        if self.current_view:
            self.current_view.pack(fill=tk.BOTH, expand=True)

    def open_config(self, mode: str):
        self.show_view('config', mode=mode)

    def start_game(self, config: Dict[str, Any], saved_state: Optional[Dict[str, Any]] = None):
        self.show_view('game', config=config, saved_state=saved_state)
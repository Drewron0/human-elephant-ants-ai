"""Application window: view routing, display density and shared UI resources."""

import logging
import tkinter as tk
from collections.abc import Callable
from typing import Any

from PIL import ImageTk

from src.ui import art
from src.ui.dialogs import Dialog
from src.ui.scene import SceneView
from src.ui.theme import (
    BASE_DPI,
    COLORS,
    DEFAULT_WINDOW,
    METRICS,
    MIN_WINDOW,
    create_fonts,
    rescale_fonts,
)
from src.ui.views.benchmark_view import BenchmarkView
from src.ui.views.config_view import ConfigView
from src.ui.views.game_view import GameView
from src.ui.views.leaderboard_view import LeaderboardView
from src.ui.views.menu_view import MainMenuView
from src.ui.views.puzzle_game_view import PuzzleGameView
from src.ui.views.puzzle_select_view import PuzzleSelectView
from src.ui.views.stage_editor_view import StageEditorView
from src.ui.views.tutorial_view import TutorialView
from src.ui.widgets import refresh_controls

logger = logging.getLogger(__name__)

APP_TITLE = "Chess-Sut"
VIEW_FACTORIES: dict[str, Callable[..., SceneView]] = {
    "menu": MainMenuView,
    "config": ConfigView,
    "game": GameView,
    "puzzle_select": PuzzleSelectView,
    "puzzle_game": PuzzleGameView,
    "stage_editor": StageEditorView,
    "benchmark": BenchmarkView,
    "leaderboard": LeaderboardView,
    "tutorial": TutorialView,
}


class GameApp(tk.Tk):
    """Hosts one screen at a time inside a single resizable window."""

    def __init__(self) -> None:
        super().__init__()
        METRICS.dpi_factor = self.winfo_fpixels("1i") / BASE_DPI
        self.title(APP_TITLE)
        self.configure(bg=COLORS["page"])
        self.geometry(self._initial_geometry())
        self.minsize(METRICS.window(MIN_WINDOW[0]), METRICS.window(MIN_WINDOW[1]))
        self.fonts = create_fonts(self)
        self._icon = ImageTk.PhotoImage(art.window_icon(), master=self)
        self.iconphoto(True, self._icon)  # type: ignore[arg-type]

        self.container = tk.Frame(self, bg=COLORS["page"])
        self.container.pack(fill=tk.BOTH, expand=True)
        self.current_view: SceneView | None = None
        self.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.bind("<Configure>", self._on_window_resize)
        self.show_view("menu")

    def _initial_geometry(self) -> str:
        """Open at a comfortable size that fits the display, centered."""
        width = min(METRICS.window(DEFAULT_WINDOW[0]), self.winfo_screenwidth() - 40)
        height = min(METRICS.window(DEFAULT_WINDOW[1]), self.winfo_screenheight() - 90)
        x = (self.winfo_screenwidth() - width) // 2
        y = max(0, (self.winfo_screenheight() - height) // 2 - 20)
        return f"{width}x{height}+{x}+{y}"

    def show_view(self, view_name: str, **options: Any) -> None:
        """Replace the current screen with a registered view."""
        if view_name not in VIEW_FACTORIES:
            raise ValueError(f"Unknown view: {view_name}")
        Dialog.dismiss_active()
        if self.current_view is not None:
            self.current_view.cleanup()
            self.current_view.destroy()
            self.current_view = None
        self.current_view = VIEW_FACTORIES[view_name](self.container, self, **options)
        self.current_view.pack(fill=tk.BOTH, expand=True)

    def quit_app(self) -> None:
        """Stop background work, then close the window."""
        if self.current_view is not None:
            self.current_view.cleanup()
        self.destroy()

    def _on_window_resize(self, event: tk.Event) -> None:
        if event.widget is not self:
            return
        density = METRICS.density_for(event.width, event.height)
        if density == METRICS.density:
            return
        METRICS.density = density
        rescale_fonts(self.fonts)
        refresh_controls()
        if self.current_view is not None:
            self.current_view.refresh_layout()

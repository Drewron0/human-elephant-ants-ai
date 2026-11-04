"""Main menu: a centered title with a top-to-bottom stack of raised game buttons."""

import tkinter as tk
from collections.abc import Callable
from functools import partial
from typing import TYPE_CHECKING

from PIL import ImageTk

from src.ui import art
from src.ui.scene import SceneView
from src.ui.theme import COLORS, MARGIN, METRICS, SPACE_L, SPACE_S, font
from src.ui.widgets import RaisedButton, Variant

if TYPE_CHECKING:
    from src.ui.app import GameApp

MENU_WIDTH = 360
TOKEN_SIZE = 54
ITEM_GAP = 12
TITLE = "Chess-Sut"
TAGLINE = "Elephant, Human, Ant. Every piece has a rival."


class MainMenuView(SceneView):
    """The hub: buttons respond to the mouse, Tab, arrow keys, Return and Space."""

    def __init__(self, parent: tk.Misc, app: "GameApp") -> None:
        super().__init__(parent, app)
        self.column = tk.Frame(self.stage, bg=COLORS["page"])
        self._column_item = self.stage.create_window(0, 0, window=self.column)
        self.crest = tk.Frame(self.column, bg=COLORS["page"])
        self._token_photos: list[ImageTk.PhotoImage] = []
        for piece in "EHA":
            photo = ImageTk.PhotoImage(
                art.token_image(piece, 0, COLORS["line_strong"], METRICS.px(TOKEN_SIZE)),
                master=self.crest,
            )
            self._token_photos.append(photo)
            tk.Label(self.crest, image=photo, bg=COLORS["page"]).pack(
                side=tk.LEFT, padx=METRICS.px(5)
            )
        self.title_label = tk.Label(
            self.column, text=TITLE, font=font("hero"), bg=COLORS["page"], fg=COLORS["ink"]
        )
        self.title_label.pack()
        tk.Label(
            self.column,
            text=TAGLINE,
            font=font("body"),
            bg=COLORS["page"],
            fg=COLORS["ink_muted"],
        ).pack(pady=(METRICS.px(SPACE_S), METRICS.px(MARGIN)))

        entries: tuple[tuple[str, Callable[[], None], Variant, str, bool], ...] = (
            ("Versus AI", partial(app.show_view, "config"), "gold", "play", True),
            ("Tactical Puzzles", partial(app.show_view, "puzzle_select"), "primary", "play", True),
            ("Stage Editor", partial(app.show_view, "stage_editor"), "secondary", "edit", False),
            ("Simulation Lab", partial(app.show_view, "benchmark"), "secondary", "chart", False),
            ("Leaderboard", partial(app.show_view, "leaderboard"), "secondary", "trophy", False),
            ("How to Play", partial(app.show_view, "tutorial"), "secondary", "help", False),
            ("Quit", app.quit_app, "secondary", "close", False),
        )
        self.items: list[RaisedButton] = []
        for index, (text, command, variant, icon, tall) in enumerate(entries):
            button = RaisedButton(self.column, text, command, variant, icon, tall)
            button.pack(fill=tk.X, pady=(0, METRICS.px(ITEM_GAP)))
            button.bind("<Up>", partial(self._on_arrow, index, -1))
            button.bind("<Down>", partial(self._on_arrow, index, 1))
            self.items.append(button)
        self.stage.configure(takefocus=1)
        self.stage.bind("<Down>", lambda _e: self.items[0].focus_set())
        self.stage.bind("<Up>", lambda _e: self.items[-1].focus_set())
        self.stage.after_idle(self.stage.focus_set)

    def _on_arrow(self, index: int, delta: int, _event: tk.Event) -> None:
        self.items[(index + delta) % len(self.items)].focus_set()

    def layout(self, width: int, height: int) -> None:
        """Center the column, leaving out the characters when the window is short."""
        margin = METRICS.px(MARGIN)
        self.stage.coords(self._column_item, width // 2, height // 2)
        self.stage.itemconfigure(
            self._column_item, width=min(METRICS.px(MENU_WIDTH), width - margin * 2)
        )
        self.crest.pack(pady=(0, METRICS.px(SPACE_L)), before=self.title_label)
        self.column.update_idletasks()
        if self.column.winfo_reqheight() > height - margin * 2:
            self.crest.pack_forget()

"""Versus-AI match setup."""

import tkinter as tk
from typing import TYPE_CHECKING

from config import settings
from src import storage
from src.ai.practice import OPTIMIZED_DIFFICULTY
from src.ui.fields import Field
from src.ui.scene import HeaderBar, Panel, SceneView
from src.ui.scrolling import ScrollArea
from src.ui.theme import (
    DEFAULT_AI_COLOR,
    DEFAULT_PLAYER_COLOR,
    GUTTER,
    METRICS,
    SPACE_M,
    SPACE_S,
    TEAM_COLORS,
    font,
)
from src.ui.widgets import PillButton, SegmentedControl, Switch, WrapLabel, field_label

if TYPE_CHECKING:
    from src.ui.app import GameApp

FORM_WIDTH = 560
AI_ENGINES = {
    "Optimized Alpha-Beta (d=6)": OPTIMIZED_DIFFICULTY,
    "Standard Minimax": "standard",
}


class ConfigView(SceneView):
    """Collects the player name, opponent, clock and team colors."""

    def __init__(self, parent: tk.Misc, app: "GameApp") -> None:
        super().__init__(parent, app)
        self.header = HeaderBar(
            self, "Match Setup", "Player vs AI", "Menu", lambda: self.app.show_view("menu")
        )
        PillButton(
            self.header.actions, "Start Game", self._start_game, variant="primary", icon="play"
        ).pack()
        self.form = Panel(self)
        scroll = ScrollArea(self.form.body)
        scroll.pack(fill=tk.BOTH, expand=True)
        self.form_content = scroll.content
        self._build_form(self.form_content)

    def _add_field(self, parent: tk.Misc, label: str) -> tk.Frame:
        row = tk.Frame(parent, bg=parent.cget("bg"))
        row.pack(fill=tk.X, pady=(0, METRICS.px(SPACE_M)))
        field_label(row, label).pack(fill=tk.X, pady=(0, METRICS.px(SPACE_S)))
        return row

    def _build_form(self, form: tk.Frame) -> None:
        self.var_p1_name = tk.StringVar(value=storage.get_last_username())
        self.var_engine = tk.StringVar(value=next(iter(AI_ENGINES)))
        self.var_time = tk.StringVar(value=settings.DEFAULT_TIME_LABEL)
        self.var_undo = tk.BooleanVar(value=True)
        self.var_p1_color = tk.StringVar(value=DEFAULT_PLAYER_COLOR)
        self.var_p2_color = tk.StringVar(value=DEFAULT_AI_COLOR)

        Field(
            self._add_field(form, "Player name"),
            self.var_p1_name,
            storage.get_recent_profiles(),
        ).pack(fill=tk.X)
        Field(
            self._add_field(form, "AI engine"),
            self.var_engine,
            list(AI_ENGINES),
            editable=False,
            on_select=lambda _value: self._sync_difficulty(),
        ).pack(fill=tk.X)

        self.difficulty_row = self._add_field(form, "Difficulty")
        self.seg_difficulty = SegmentedControl(
            self.difficulty_row,
            [("Easy", "easy"), ("Normal", "normal"), ("Hard", "hard")],
            "normal",
        )
        self.seg_difficulty.pack(fill=tk.X)
        self.lbl_difficulty = WrapLabel(self.difficulty_row, "", font=font("caption"))

        Field(
            self._add_field(form, "Timer per side"),
            self.var_time,
            list(settings.TIME_LIMIT_CHOICES),
            editable=False,
        ).pack(fill=tk.X)

        colors = tk.Frame(form, bg=form.cget("bg"))
        colors.pack(fill=tk.X, pady=(0, METRICS.px(SPACE_M)))
        colors.columnconfigure((0, 1), weight=1, uniform="colors")
        for column, (label, variable) in enumerate(
            (("Your color", self.var_p1_color), ("AI color", self.var_p2_color))
        ):
            box = tk.Frame(colors, bg=form.cget("bg"))
            box.grid(
                row=0,
                column=column,
                sticky="ew",
                padx=(0, METRICS.px(GUTTER)) if column == 0 else 0,
            )
            field_label(box, label).pack(fill=tk.X, pady=(0, METRICS.px(SPACE_S)))
            Field(box, variable, list(TEAM_COLORS), editable=False).pack(fill=tk.X)
        Switch(form, "Allow undo (Ctrl+Z)", self.var_undo).pack(anchor="w")

    def _sync_difficulty(self) -> None:
        optimized = AI_ENGINES[self.var_engine.get()] == OPTIMIZED_DIFFICULTY
        if optimized:
            self.seg_difficulty.pack_forget()
            self.lbl_difficulty.configure(text="Uses the 1.95-second iterative deepening search.")
            self.lbl_difficulty.pack(fill=tk.X)
        else:
            self.lbl_difficulty.pack_forget()
            self.seg_difficulty.pack(fill=tk.X)
        self.refresh_layout()

    def layout(self, width: int, height: int) -> None:
        """Center the form below the header, scrolling when the window is short."""
        top = self.header.place_top(width)
        margin = top - self.header.height()
        form_w = min(METRICS.px(FORM_WIDTH), width - margin * 2)
        form_h = min(self.form.fit_height(self.form_content), height - top - margin)
        self.form.place((width - form_w) // 2, top, form_w, form_h)

    def _start_game(self) -> None:
        name = self.var_p1_name.get().strip() or settings.DEFAULT_PLAYER_NAME
        storage.save_last_username(name)
        engine = AI_ENGINES[self.var_engine.get()]
        self.app.show_view(
            "game",
            config={
                "p1_name": name,
                "p2_name": "AI",
                "difficulty": (
                    OPTIMIZED_DIFFICULTY
                    if engine == OPTIMIZED_DIFFICULTY
                    else self.seg_difficulty.get()
                ),
                "time_limit": settings.TIME_LIMIT_CHOICES[self.var_time.get()],
                "undo_enabled": self.var_undo.get(),
                "p1_color": TEAM_COLORS[self.var_p1_color.get()],
                "p2_color": TEAM_COLORS[self.var_p2_color.get()],
            },
        )

"""Versus-AI records with difficulty filters and sorting."""

import tkinter as tk
from typing import TYPE_CHECKING

from src import storage
from src.ai.practice import DIFFICULTY_LABELS
from src.ui.dialogs import confirm
from src.ui.scene import HeaderBar, Panel, SceneView
from src.ui.table import DataTable, TableColumn
from src.ui.theme import COLORS, GUTTER, METRICS, SPACE_M, SPACE_S
from src.ui.widgets import PillButton, SegmentedControl, field_label

if TYPE_CHECKING:
    from src.ui.app import GameApp

COLUMNS: tuple[TableColumn, ...] = (
    TableColumn("rank", "Rank", 60, "center"),
    TableColumn("player", "Player", 190, "w"),
    TableColumn("difficulty", "Difficulty", 110, "center"),
    TableColumn("turns", "Turns", 80, "center"),
    TableColumn("time_left", "Time left", 110, "center"),
    TableColumn("undos", "Undos", 80, "center"),
    TableColumn("date", "Date", 150, "center"),
)
FILTER_STACK_WIDTH = 1040
EMPTY_TEXT = "No wins recorded yet."


class LeaderboardView(SceneView):
    """Lists Versus-AI wins; records can be removed one by one or by category."""

    def __init__(self, parent: tk.Misc, app: "GameApp") -> None:
        super().__init__(parent, app)
        self.sort_by = "turns"
        self.difficulty_category = "all"
        self.header = HeaderBar(
            self, "Leaderboard", "Versus-AI wins", "Menu", lambda: self.app.show_view("menu")
        )
        self.filters = Panel(self)
        self._difficulty_box = tk.Frame(self.filters.body, bg=COLORS["card"])
        self._sort_box = tk.Frame(self.filters.body, bg=COLORS["card"])
        label_gap = (0, METRICS.px(SPACE_S))
        field_label(self._difficulty_box, "Difficulty").pack(fill=tk.X, pady=label_gap)
        options = [("All", "all")] + [
            (label, label.lower()) for label in DIFFICULTY_LABELS.values()
        ]
        SegmentedControl(self._difficulty_box, options, "all", self._set_difficulty_filter).pack(
            fill=tk.X
        )
        field_label(self._sort_box, "Sort by").pack(fill=tk.X, pady=label_gap)
        SegmentedControl(
            self._sort_box,
            [("Turns", "turns"), ("Time left", "time"), ("Undos", "undos")],
            "turns",
            self._set_sort,
        ).pack(fill=tk.X)

        self.table_panel = Panel(self)
        body = self.table_panel.body
        actions = tk.Frame(body, bg=COLORS["card"])
        actions.pack(side=tk.BOTTOM, fill=tk.X, pady=(METRICS.px(SPACE_M), 0))
        self.table = DataTable(
            body, COLUMNS, EMPTY_TEXT, on_select=lambda _row: self._sync_actions()
        )
        self.table.pack(fill=tk.BOTH, expand=True)
        self.btn_delete = PillButton(actions, "Delete Entry", self._delete_selected, icon="trash")
        self.btn_delete.pack(side=tk.LEFT, padx=(0, METRICS.px(SPACE_S)))
        PillButton(actions, "Clear Category", self._clear_category).pack(side=tk.LEFT)
        PillButton(actions, "Clear All", self._clear_all, variant="destructive", icon="trash").pack(
            side=tk.RIGHT
        )
        self._refresh_table()

    def layout(self, width: int, height: int) -> None:
        """Place filters side by side, or stacked when the window is narrow."""
        top = self.header.place_top(width)
        margin = top - self.header.height()
        gutter = METRICS.px(GUTTER)
        stacked = width < METRICS.px(FILTER_STACK_WIDTH)
        self._difficulty_box.grid(row=0, column=0, sticky="ew")
        self._sort_box.grid(
            row=1 if stacked else 0,
            column=0 if stacked else 1,
            sticky="ew",
            padx=(0 if stacked else gutter, 0),
            pady=(METRICS.px(SPACE_M) if stacked else 0, 0),
        )
        self.filters.body.columnconfigure(0, weight=3)
        self.filters.body.columnconfigure(1, weight=0 if stacked else 2)
        filter_h = self.filters.fit_height()
        self.filters.place(margin, top, width - margin * 2, filter_h)
        table_top = top + filter_h + gutter
        self.table_panel.place(margin, table_top, width - margin * 2, height - table_top - margin)

    def _set_difficulty_filter(self, difficulty: str) -> None:
        self.difficulty_category = difficulty
        self._refresh_table()

    def _set_sort(self, sort_by: str) -> None:
        self.sort_by = sort_by
        self._refresh_table()

    def _sync_actions(self) -> None:
        self.btn_delete.set_enabled(self.table.selected is not None)

    def _refresh_table(self) -> None:
        rows = []
        records = storage.get_pve_leaderboard(self.sort_by, self.difficulty_category)
        for index, record in enumerate(records):
            seconds = record.get("time_left", 0)
            time_text = f"{seconds // 60}:{seconds % 60:02d}" if seconds >= 0 else "No timer"
            rows.append(
                (
                    record["id"],
                    (
                        index + 1,
                        record["username"],
                        record.get("difficulty", "Normal"),
                        record["turns"],
                        time_text,
                        record["undos"],
                        record["timestamp"],
                    ),
                )
            )
        self.table.set_rows(rows)
        self._sync_actions()

    def _delete_selected(self) -> None:
        if self.table.selected:
            storage.delete_pve_score(self.table.selected)
            self._refresh_table()

    def _clear_category(self) -> None:
        category = self.difficulty_category

        def clear() -> None:
            storage.clear_pve_leaderboard(category)
            self._refresh_table()

        name = "all difficulties" if category == "all" else f"{category.capitalize()} difficulty"
        confirm(
            self,
            "Clear Category?",
            f"This removes the records for {name} and cannot be undone.",
            "Clear",
            clear,
        )

    def _clear_all(self) -> None:
        def clear() -> None:
            storage.clear_pve_leaderboard("all")
            self._refresh_table()

        confirm(
            self,
            "Clear All Records?",
            "This removes every Versus-AI record and cannot be undone.",
            "Clear All",
            clear,
        )

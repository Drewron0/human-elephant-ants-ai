"""Stage catalog with previews, defender selection and per-stage records."""

import tkinter as tk
from functools import partial
from typing import TYPE_CHECKING, Any

from PIL import ImageTk

from config import settings
from src import storage
from src.ai.agents import PUZZLE_AGENTS
from src.puzzle.scenario import PuzzleScenario, get_all_puzzles
from src.ui import art
from src.ui.dialogs import confirm
from src.ui.fields import Field
from src.ui.scene import HeaderBar, Panel, SceneView
from src.ui.scrolling import ScrollArea
from src.ui.theme import (
    COLORS,
    DEFAULT_AI_COLOR,
    DEFAULT_PLAYER_COLOR,
    GUTTER,
    METRICS,
    SPACE_L,
    SPACE_M,
    SPACE_S,
    TEAM_COLORS,
    font,
)
from src.ui.widgets import (
    PillButton,
    RoundedCard,
    Switch,
    WrapLabel,
    divider,
    field_label,
    section_title,
)

if TYPE_CHECKING:
    from src.ui.app import GameApp

THUMBNAIL = 160
CARD_PADDING = 14
SIDEBAR_WIDTH = 380
PORTRAIT_RATIO = 1.12


class PuzzleSelectView(SceneView):
    """Browse, play, edit and delete the stages saved by users."""

    def __init__(self, parent: tk.Misc, app: "GameApp") -> None:
        super().__init__(parent, app)
        self.selected_puzzle_id = ""
        self.card_widgets: dict[str, dict[str, Any]] = {}
        self._photos: list[ImageTk.PhotoImage] = []
        self._columns = 0
        self.header = HeaderBar(
            self,
            "Puzzle Stages",
            back_text="Menu",
            on_back=lambda: self.app.show_view("menu"),
        )
        PillButton(
            self.header.actions,
            "New Stage",
            lambda: self.app.show_view("stage_editor"),
            variant="primary",
            icon="plus",
        ).pack()
        self.catalog = Panel(self)
        catalog_scroll = ScrollArea(self.catalog.body)
        catalog_scroll.pack(fill=tk.BOTH, expand=True)
        self.grid_frame = catalog_scroll.content
        self.details = Panel(self)
        details_scroll = ScrollArea(self.details.body)
        details_scroll.pack(fill=tk.BOTH, expand=True)
        self._build_details(details_scroll.content)
        self._populate_grid()

    def _build_details(self, content: tk.Frame) -> None:
        small = (0, METRICS.px(SPACE_S))
        medium = (0, METRICS.px(SPACE_M))
        self.lbl_selected_title = tk.Label(
            content,
            text="",
            font=font("title"),
            bg=COLORS["card"],
            fg=COLORS["ink"],
            anchor="w",
        )
        self.lbl_selected_title.pack(fill=tk.X, pady=small)
        self.lbl_selected_desc = WrapLabel(content, "", fg=COLORS["ink_muted"])
        self.lbl_selected_desc.pack(fill=tk.X, pady=small)
        self.lbl_selected_stats = WrapLabel(content, "", fg=COLORS["ink_muted"])
        self.lbl_selected_stats.pack(fill=tk.X, pady=medium)

        self.btn_play = PillButton(
            content,
            "Play Stage",
            self._start_selected_stage,
            variant="primary",
            icon="play",
        )
        self.btn_play.pack(fill=tk.X, pady=small)
        self.frame_custom_actions = tk.Frame(content, bg=COLORS["card"])
        self.frame_custom_actions.columnconfigure((0, 1), weight=1, uniform="stage")
        half_gap = METRICS.px(SPACE_S) // 2
        PillButton(self.frame_custom_actions, "Edit", self._edit_selected_stage, icon="edit").grid(
            row=0, column=0, sticky="ew", padx=(0, half_gap)
        )
        PillButton(
            self.frame_custom_actions,
            "Delete",
            self._delete_selected_stage,
            variant="destructive",
            icon="trash",
        ).grid(row=0, column=1, sticky="ew", padx=(half_gap, 0))
        self.frame_custom_actions.pack(fill=tk.X)

        divider(content).pack(fill=tk.X, pady=METRICS.px(SPACE_L))
        field_label(content, "Player").pack(fill=tk.X, pady=small)
        self.var_player_name = tk.StringVar(value=storage.get_last_username())
        Field(content, self.var_player_name, storage.get_recent_profiles()).pack(
            fill=tk.X, pady=medium
        )
        field_label(content, "Defender").pack(fill=tk.X, pady=small)
        self.var_ai_model = tk.StringVar(value=PUZZLE_AGENTS[0].label)
        Field(
            content,
            self.var_ai_model,
            [agent.label for agent in PUZZLE_AGENTS],
            editable=False,
        ).pack(fill=tk.X, pady=medium)
        self.var_show_metrics = tk.BooleanVar(value=False)
        Switch(content, "Show AI metrics", self.var_show_metrics).pack(anchor="w")

        divider(content).pack(fill=tk.X, pady=METRICS.px(SPACE_L))
        section_title(content, "Best records").pack(fill=tk.X, pady=small)
        self.box_leaderboard = tk.Frame(content, bg=COLORS["card"])
        self.box_leaderboard.pack(fill=tk.X)

    def layout(self, width: int, height: int) -> None:
        """Show catalog and details side by side, or stacked in portrait windows."""
        top = self.header.place_top(width)
        margin = top - self.header.height() - self.header.geometry[1]
        gutter = METRICS.px(GUTTER)
        available_h = height - top - margin
        if width >= height * PORTRAIT_RATIO:
            side_w = min(METRICS.px(SIDEBAR_WIDTH), width // 2)
            catalog_w = width - margin * 2 - gutter - side_w
            self.catalog.place(margin, top, catalog_w, available_h)
            self.details.place(margin + catalog_w + gutter, top, side_w, available_h)
        else:
            catalog_h = available_h // 2
            catalog_w = width - margin * 2
            self.catalog.place(margin, top, catalog_w, catalog_h)
            self.details.place(
                margin,
                top + catalog_h + gutter,
                catalog_w,
                available_h - catalog_h - gutter,
            )
        slot = self._card_width() + METRICS.px(SPACE_M)
        columns = max(1, (catalog_w - self.catalog.inset() * 2) // slot)
        if columns != self._columns:
            self._columns = columns
            self._arrange_cards()

    def _card_width(self) -> int:
        return METRICS.px(THUMBNAIL) + METRICS.px(CARD_PADDING) * 2

    def _arrange_cards(self) -> None:
        columns = max(1, self._columns)
        for index, item in enumerate(self.card_widgets.values()):
            item["card"].grid(
                row=index // columns,
                column=index % columns,
                padx=(0, METRICS.px(SPACE_M)),
                pady=(0, METRICS.px(SPACE_M)),
                sticky="nw",
            )

    def _populate_grid(self) -> None:
        for widget in self.grid_frame.winfo_children():
            widget.destroy()
        self.card_widgets.clear()
        self._photos.clear()
        puzzles = list(get_all_puzzles().values())
        if not puzzles:
            self.selected_puzzle_id = ""
            WrapLabel(
                self.grid_frame,
                "No stages yet. Choose New Stage to build your first one.",
                fg=COLORS["ink_muted"],
                justify=tk.CENTER,
                anchor="center",
            ).pack(fill=tk.X, pady=METRICS.px(40))
            self._update_sidebar()
            return
        if self.selected_puzzle_id not in (puzzle.id for puzzle in puzzles):
            self.selected_puzzle_id = puzzles[0].id
        for puzzle in puzzles:
            self._add_card(puzzle)
        self._arrange_cards()
        self._refresh_card_highlights()
        self._update_sidebar()

    def _add_card(self, puzzle: PuzzleScenario) -> None:
        card = RoundedCard(self.grid_frame, padding=CARD_PADDING)
        card.configure(width=self._card_width(), takefocus=1, cursor="hand2")
        photo = ImageTk.PhotoImage(
            art.board_thumbnail(
                puzzle.board_size,
                puzzle.pieces,
                METRICS.px(THUMBNAIL),
                TEAM_COLORS[DEFAULT_PLAYER_COLOR],
                TEAM_COLORS[DEFAULT_AI_COLOR],
            ),
            master=card,
        )
        self._photos.append(photo)
        thumbnail = tk.Label(card.body, image=photo, bg=COLORS["card"], cursor="hand2")
        thumbnail.pack(pady=(0, METRICS.px(SPACE_S)))
        title = tk.Label(
            card.body,
            text=puzzle.title,
            font=font("heading"),
            bg=COLORS["card"],
            fg=COLORS["ink"],
            cursor="hand2",
        )
        title.pack(fill=tk.X)
        minimum = f"{puzzle.s_optimal} steps" if puzzle.s_optimal is not None else "No minimum"
        subtitle = tk.Label(
            card.body,
            text=f"{puzzle.board_size}x{puzzle.board_size}, {minimum}",
            font=font("caption"),
            bg=COLORS["card"],
            fg=COLORS["ink_muted"],
            cursor="hand2",
        )
        subtitle.pack(fill=tk.X)
        choose = partial(self._on_card_event, puzzle.id)
        for widget in (card, card.body, thumbnail, title, subtitle):
            widget.bind("<Button-1>", choose)
        card.bind("<Return>", choose)
        card.bind("<space>", choose)
        self.card_widgets[puzzle.id] = {"card": card, "puzzle": puzzle}

    def _on_card_event(self, puzzle_id: str, _event: tk.Event) -> None:
        self._select_stage(puzzle_id)

    def _select_stage(self, puzzle_id: str) -> None:
        self.selected_puzzle_id = puzzle_id
        self._refresh_card_highlights()
        self._update_sidebar()

    def _refresh_card_highlights(self) -> None:
        for puzzle_id, item in self.card_widgets.items():
            item["card"].set_active(puzzle_id == self.selected_puzzle_id)

    def _selected_puzzle(self) -> PuzzleScenario | None:
        return self.card_widgets.get(self.selected_puzzle_id, {}).get("puzzle")

    def _update_sidebar(self) -> None:
        puzzle = self._selected_puzzle()
        if puzzle is None:
            self.lbl_selected_title.configure(text="No Stage Selected")
            self.lbl_selected_desc.configure(text="Create a stage to start playing.")
            self.lbl_selected_stats.configure(text="")
            self.btn_play.set_enabled(False)
            self.frame_custom_actions.pack_forget()
            self._refresh_stage_leaderboard()
            return
        self.lbl_selected_title.configure(text=puzzle.title)
        self.lbl_selected_desc.configure(text=puzzle.description or "Tactical puzzle.")
        details = f"{puzzle.step_summary}\nMove limit: {puzzle.s_max}"
        if puzzle.s_optimal is None:
            details += "\nEdit this stage to enter its minimum steps."
        self.lbl_selected_stats.configure(text=details)
        self.btn_play.set_enabled(puzzle.s_optimal is not None)
        self.frame_custom_actions.pack(fill=tk.X, after=self.btn_play)
        self._refresh_stage_leaderboard()

    def _refresh_stage_leaderboard(self) -> None:
        for widget in self.box_leaderboard.winfo_children():
            widget.destroy()
        records = storage.get_stage_leaderboard(self.selected_puzzle_id)
        if not records:
            WrapLabel(
                self.box_leaderboard,
                "No records yet. Be the first to solve this stage.",
                font=font("caption"),
                fg=COLORS["ink_muted"],
            ).pack(fill=tk.X)
            return
        for rank, record in enumerate(records[: settings.STAGE_LEADERBOARD_PREVIEW], 1):
            row = tk.Frame(self.box_leaderboard, bg=COLORS["card"])
            row.pack(fill=tk.X, pady=(0, METRICS.px(SPACE_S) // 2))
            tk.Label(
                row,
                text=f"{rank}. {record.get('username', 'Player')}",
                font=font("caption"),
                bg=COLORS["card"],
                fg=COLORS["ink"],
            ).pack(side=tk.LEFT)
            tk.Label(
                row,
                text=f"{record.get('steps', 0)} moves, {record.get('undos', 0)} undos",
                font=font("caption"),
                bg=COLORS["card"],
                fg=COLORS["ink_muted"],
            ).pack(side=tk.RIGHT)

    def _edit_selected_stage(self) -> None:
        puzzle = self._selected_puzzle()
        if puzzle:
            self.app.show_view("stage_editor", edit_stage=puzzle.to_dict())

    def _delete_selected_stage(self) -> None:
        puzzle = self._selected_puzzle()
        if puzzle is None:
            return

        def delete() -> None:
            storage.delete_custom_stage(puzzle.id)
            self._populate_grid()

        confirm(
            self,
            "Delete Stage?",
            f'"{puzzle.title}" and its records will be removed permanently.',
            "Delete",
            delete,
        )

    def _start_selected_stage(self) -> None:
        puzzle = self._selected_puzzle()
        if puzzle is None or puzzle.s_optimal is None:
            return
        name = self.var_player_name.get().strip() or settings.DEFAULT_PLAYER_NAME
        storage.save_last_username(name)
        agent = next(a for a in PUZZLE_AGENTS if a.label == self.var_ai_model.get())
        self.app.show_view(
            "puzzle_game",
            config={
                "p1_name": name,
                "scenario": puzzle,
                "agent_model": agent.model,
                "agent_label": agent.label.split(" (")[0].replace("Practice: ", ""),
                "search_depth": agent.depth,
                "show_metrics": self.var_show_metrics.get(),
                "colors": {
                    0: TEAM_COLORS[DEFAULT_PLAYER_COLOR],
                    1: TEAM_COLORS[DEFAULT_AI_COLOR],
                },
            },
        )

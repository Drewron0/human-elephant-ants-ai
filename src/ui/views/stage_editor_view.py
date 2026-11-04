"""Visual editor for creating and changing custom puzzle stages."""

import tkinter as tk
from functools import partial
from typing import TYPE_CHECKING, Any

from config import settings
from src import storage
from src.core.game_logic import PIECE_NAMES, Coord
from src.puzzle.scenario import validate_stage
from src.ui.board import BoardFrame, BoardLayer
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
    SPACE_M,
    SPACE_S,
    TEAM_COLORS,
    font,
)
from src.ui.widgets import PillButton, WrapLabel, field_label, section_title

if TYPE_CHECKING:
    from src.ui.app import GameApp

SIDEBAR_WIDTH = 360
MIN_BOARD = 260
LANDSCAPE_RATIO = 1.12
PORTRAIT_BOARD_SHARE = 0.55
ERASER = "ERASER"
TOOL_KEYS = {
    "1": "P0_H",
    "2": "P0_E",
    "3": "P0_A",
    "4": "P1_H",
    "5": "P1_E",
    "6": "P1_A",
    "0": ERASER,
}
TEXT_WIDGET_CLASSES = ("Entry",)
DEFAULT_SQUAD: tuple[tuple[int, int, int, str], ...] = (
    (-1, 0, 0, "H"),
    (-1, 1, 0, "E"),
    (-2, 0, 0, "A"),
    (2, 3, 1, "E"),
    (1, 4, 1, "H"),
)


class StageEditorView(SceneView):
    """Places pieces on the board and saves the stage with its author-entered minimum."""

    def __init__(
        self, parent: tk.Misc, app: "GameApp", edit_stage: dict[str, Any] | None = None
    ) -> None:
        super().__init__(parent, app)
        stage = edit_stage or {}
        self.edit_stage_id: str | None = stage.get("id")
        self.board_size: int = stage.get("board_size", settings.EDITOR_DEFAULT_BOARD_SIZE)
        minimum = stage.get("s_optimal")
        self.placed_pieces: dict[Coord, tuple[int, str]] = {
            (p[0], p[1]): (p[2], p[3]) for p in stage.get("pieces", [])
        }
        if not stage:
            self._place_default_squad()
        self.active_tool = "P1_E"
        self.board = BoardLayer(
            self.stage, self.board_size, self._on_square, self._on_secondary_square
        )
        self.header = HeaderBar(
            self,
            "Edit Stage" if self.edit_stage_id else "New Stage",
            "Click squares to place pieces; right-click to erase",
            "Cancel",
            lambda: self.app.show_view("puzzle_select"),
        )
        PillButton(
            self.header.actions,
            "Save Stage",
            self._save_stage,
            variant="primary",
            icon="check",
        ).pack()
        self.sidebar = Panel(self)
        scroll = ScrollArea(self.sidebar.body)
        scroll.pack(fill=tk.BOTH, expand=True)
        self._build_form(
            scroll.content,
            stage.get("title", "My Custom Stage"),
            stage.get("description", "Custom tactical puzzle."),
            "" if minimum is None else str(minimum),
        )
        for key, tool in TOOL_KEYS.items():
            self.app.bind(f"<Key-{key}>", partial(self._on_tool_key, tool))

    def _place_default_squad(self) -> None:
        self.placed_pieces = {}
        size = self.board_size
        for r, c, owner, piece_type in DEFAULT_SQUAD:
            self.placed_pieces[(r % size, c)] = (owner, piece_type)

    def _entry(self, parent: tk.Misc, label: str, variable: tk.StringVar) -> Field:
        field_label(parent, label).pack(fill=tk.X, pady=(0, METRICS.px(SPACE_S)))
        field = Field(parent, variable)
        field.pack(fill=tk.X, pady=(0, METRICS.px(SPACE_M)))
        return field

    def _build_form(self, form: tk.Frame, title: str, description: str, minimum: str) -> None:
        self.var_title = tk.StringVar(value=title)
        self.var_desc = tk.StringVar(value=description)
        self.var_minimum_steps = tk.StringVar(value=minimum)
        self.var_size = tk.StringVar(value=f"{self.board_size}x{self.board_size}")
        self._entry(form, "Title", self.var_title)
        self._entry(form, "Description", self.var_desc)
        self.entry_minimum_steps = self._entry(form, "Minimum steps", self.var_minimum_steps)
        self.lbl_save_error = WrapLabel(form, "", font=font("caption"), fg=COLORS["danger"])
        self.size_label = field_label(form, "Board size")
        self.size_label.pack(fill=tk.X, pady=(0, METRICS.px(SPACE_S)))
        Field(
            form,
            self.var_size,
            [f"{s}x{s}" for s in settings.EDITOR_BOARD_SIZES],
            editable=False,
            on_select=self._on_size_change,
        ).pack(fill=tk.X, pady=(0, METRICS.px(SPACE_M) * 3 // 2))

        section_title(form, "Pieces").pack(fill=tk.X, pady=(0, METRICS.px(SPACE_S)))
        palette = tk.Frame(form, bg=COLORS["card"])
        palette.pack(fill=tk.X)
        palette.columnconfigure((0, 1), weight=1, uniform="palette")
        gap = METRICS.px(SPACE_S) // 2
        self.palette_buttons: dict[str, PillButton] = {}
        for column, (owner, side) in enumerate(((0, "You"), (1, "AI"))):
            for row, piece_type in enumerate("HEA"):
                code = f"P{owner}_{piece_type}"
                button = PillButton(
                    palette,
                    f"{side}: {PIECE_NAMES[piece_type]}",
                    partial(self._set_tool, code),
                )
                button.grid(row=row, column=column, sticky="ew", padx=gap, pady=gap)
                self.palette_buttons[code] = button
        eraser = PillButton(palette, "Eraser", lambda: self._set_tool(ERASER), icon="close")
        eraser.grid(row=3, column=0, sticky="ew", padx=gap, pady=gap)
        self.palette_buttons[ERASER] = eraser
        PillButton(palette, "Reset", self._clear_board, icon="restart").grid(
            row=3, column=1, sticky="ew", padx=gap, pady=gap
        )
        WrapLabel(
            form,
            "Keys 1-3 pick your pieces, 4-6 the AI pieces, 0 the eraser.",
            font=font("caption"),
            fg=COLORS["ink_muted"],
        ).pack(fill=tk.X, pady=(METRICS.px(SPACE_M), METRICS.px(SPACE_M)))
        if self.edit_stage_id:
            PillButton(
                form,
                "Delete Stage",
                self._delete_stage,
                variant="destructive",
                icon="trash",
            ).pack(fill=tk.X)
        self._refresh_palette_highlight()

    def layout(self, width: int, height: int) -> None:
        """Keep the board large and the form beside or below it."""
        top = self.header.place_top(width)
        margin = top - self.header.height() - self.header.geometry[1]
        gutter = METRICS.px(GUTTER)
        available_h = height - top - margin
        if width >= height * LANDSCAPE_RATIO:
            side_w = min(METRICS.px(SIDEBAR_WIDTH), width // 2 - margin)
            area = width - side_w - margin * 2 - gutter
            dimension = max(METRICS.px(MIN_BOARD), min(area, available_h))
            self.board.place(
                margin + (area - dimension) // 2,
                top + (available_h - dimension) // 2,
                dimension,
            )
            self.sidebar.place(width - margin - side_w, top, side_w, available_h)
        else:
            dimension = max(
                METRICS.px(MIN_BOARD),
                min(width - margin * 2, round(available_h * PORTRAIT_BOARD_SHARE)),
            )
            self.board.place((width - dimension) // 2, top, dimension)
            panel_top = top + dimension + gutter
            self.sidebar.place(margin, panel_top, width - margin * 2, height - panel_top - margin)
        self._render_board()

    def _render_board(self) -> None:
        self.board.render(
            BoardFrame(
                pieces=[
                    (r, c, owner, kind) for (r, c), (owner, kind) in self.placed_pieces.items()
                ],
                colors={
                    0: TEAM_COLORS[DEFAULT_PLAYER_COLOR],
                    1: TEAM_COLORS[DEFAULT_AI_COLOR],
                },
            )
        )

    def _on_tool_key(self, tool: str, event: tk.Event) -> None:
        if str(event.widget.winfo_class()) not in TEXT_WIDGET_CLASSES:
            self._set_tool(tool)

    def _set_tool(self, tool_code: str) -> None:
        self.active_tool = tool_code
        self._refresh_palette_highlight()

    def _refresh_palette_highlight(self) -> None:
        for code, button in self.palette_buttons.items():
            button.set_variant("primary" if code == self.active_tool else "secondary")

    def _on_size_change(self, _value: str | None = None) -> None:
        new_size = int(self.var_size.get().split("x")[0])
        if new_size == self.board_size:
            return
        self.board_size = new_size
        self.placed_pieces = {
            coord: piece
            for coord, piece in self.placed_pieces.items()
            if coord[0] < new_size and coord[1] < new_size
        }
        self.board.set_board_size(new_size)
        self.refresh_layout()

    def _on_secondary_square(self, square: Coord) -> None:
        if self.placed_pieces.pop(square, None) is not None:
            self._render_board()

    def _on_square(self, square: Coord) -> None:
        if self.active_tool == ERASER:
            self.placed_pieces.pop(square, None)
        else:
            owner = 0 if self.active_tool.startswith("P0") else 1
            self.placed_pieces[square] = (owner, self.active_tool.split("_")[1])
        self._render_board()

    def _clear_board(self) -> None:
        self._place_default_squad()
        self._render_board()

    def _save_stage(self) -> None:
        pieces = [(r, c, owner, kind) for (r, c), (owner, kind) in self.placed_pieces.items()]
        problem = validate_stage(self.board_size, pieces, self.var_minimum_steps.get())
        if problem:
            self.lbl_save_error.configure(text=problem)
            self.lbl_save_error.pack(
                fill=tk.X, pady=(0, METRICS.px(SPACE_M)), before=self.size_label
            )
            return
        self.lbl_save_error.pack_forget()
        storage.save_custom_stage(
            {
                "id": self.edit_stage_id,
                "title": self.var_title.get().strip() or "Custom Stage",
                "description": self.var_desc.get().strip() or "Custom tactical puzzle.",
                "board_size": self.board_size,
                "s_optimal": int(self.var_minimum_steps.get().strip()),
                "minimum_source": "manual",
                "pieces": pieces,
                "is_custom": True,
            }
        )
        self.app.show_view("puzzle_select")

    def _delete_stage(self) -> None:
        stage_id = self.edit_stage_id
        if not stage_id:
            return

        def delete() -> None:
            storage.delete_custom_stage(stage_id)
            self.app.show_view("puzzle_select")

        confirm(
            self,
            "Delete Stage?",
            "This stage and its records will be removed permanently.",
            "Delete",
            delete,
        )

    def cleanup(self) -> None:
        """Release the palette shortcuts."""
        super().cleanup()
        for key in TOOL_KEYS:
            self.app.unbind(f"<Key-{key}>")

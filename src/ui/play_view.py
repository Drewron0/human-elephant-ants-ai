"""Shared game screen: responsive board plus sidebar, selection and keyboard play."""

import tkinter as tk
from abc import abstractmethod
from collections.abc import Callable
from functools import partial
from typing import TYPE_CHECKING

from PIL import ImageTk

from src.core.game_logic import Coord, GameState, MoveTuple
from src.ui import art
from src.ui.board import BoardFrame, BoardLayer
from src.ui.dialogs import Dialog
from src.ui.scene import HeaderBar, Panel, SceneView
from src.ui.scrolling import ScrollArea, ThinScrollbar
from src.ui.theme import (
    COLORS,
    GUTTER,
    HOTKEYS,
    MARGIN,
    METRICS,
    SPACE_L,
    SPACE_M,
    SPACE_S,
    font,
)
from src.ui.widgets import RoundedCard, WrapLabel, field_label, section_title

if TYPE_CHECKING:
    from src.ui.app import GameApp

SIDEBAR_WIDTH = 360
MIN_BOARD = 280
PORTRAIT_BOARD_SHARE = 0.6
HISTORY_ROWS = 5
CARD_TOKEN = 36
CYCLE_THUMBNAIL = 92
LANDSCAPE_RATIO = 1.12
ARROW_STEPS = {"Up": (-1, 0), "Down": (1, 0), "Left": (0, -1), "Right": (0, 1)}
CYCLE_TEXT = "Elephant beats Human\nHuman beats Ant\nAnt beats Elephant"


class PlayerCard(RoundedCard):
    """A player row showing the token, the name and a value such as the clock."""

    def __init__(self, parent: tk.Misc, name: str, piece: str, owner: int, color: str) -> None:
        super().__init__(parent)
        size = METRICS.px(CARD_TOKEN)
        self._token = ImageTk.PhotoImage(art.token_image(piece, owner, color, size), master=self)
        tk.Label(self.body, image=self._token, bg=COLORS["card"]).pack(side=tk.LEFT)
        tk.Label(
            self.body,
            text=name,
            font=font("body"),
            bg=COLORS["card"],
            fg=COLORS["ink"],
            anchor="w",
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(METRICS.px(SPACE_S), 0))
        self.value_label = tk.Label(
            self.body, font=font("heading"), bg=COLORS["card"], fg=COLORS["ink"]
        )
        self.value_label.pack(side=tk.RIGHT)

    def set_value(self, text: str, warning: bool = False) -> None:
        """Show the card's value, tinted when it needs attention."""
        self.value_label.configure(text=text, fg=COLORS["danger"] if warning else COLORS["ink"])


class PlayView(SceneView):
    """Lays out a board with a sidebar; landscape side by side, portrait stacked."""

    def __init__(self, parent: tk.Misc, app: "GameApp", board_size: int) -> None:
        super().__init__(parent, app)
        self.state: GameState
        self.selected_sq: Coord | None = None
        self.valid_targets: list[Coord] = []
        self.last_move: MoveTuple | None = None
        self.cursor: Coord | None = None
        self.board = BoardLayer(self.stage, board_size, self._on_square)
        self.header: HeaderBar
        self.sidebar = Panel(self)
        self.action_bar = tk.Frame(self.sidebar.body, bg=COLORS["card"])
        self.action_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(METRICS.px(SPACE_M), 0))
        self.action_bar.columnconfigure((0, 1), weight=1, uniform="actions")
        scroll = ScrollArea(self.sidebar.body)
        scroll.pack(fill=tk.BOTH, expand=True)
        self.side = scroll.content
        self.stage.configure(takefocus=1)
        self.stage.bind("<Return>", lambda _e: self._activate_cursor())
        self.stage.bind("<space>", lambda _e: self._activate_cursor())
        for key, step in ARROW_STEPS.items():
            self.stage.bind(f"<{key}>", partial(self._on_arrow, step))
        self.stage.after_idle(self.stage.focus_set)

    @abstractmethod
    def _can_interact(self) -> bool:
        """Return whether the player may act on the board now."""

    @abstractmethod
    def _commit_move(self, start: Coord, end: Coord) -> None:
        """Apply the player's chosen move."""

    @abstractmethod
    def _player_colors(self) -> dict[int, str]:
        """Return each side's team color."""

    def layout(self, width: int, height: int) -> None:
        """Keep the board as large as possible beside or above the sidebar."""
        top = self.header.place_top(width)
        margin = METRICS.px(MARGIN)
        gutter = METRICS.px(GUTTER)
        available_h = height - top - margin
        if width >= height * LANDSCAPE_RATIO:
            sidebar_w = min(METRICS.px(SIDEBAR_WIDTH), width // 2 - margin)
            board_area = width - sidebar_w - margin * 2 - gutter
            dimension = max(METRICS.px(MIN_BOARD), min(board_area, available_h))
            self.board.place(
                margin + (board_area - dimension) // 2,
                top + (available_h - dimension) // 2,
                dimension,
            )
            self.sidebar.place(width - margin - sidebar_w, top, sidebar_w, available_h)
        else:
            dimension = max(
                METRICS.px(MIN_BOARD),
                min(width - margin * 2, round(available_h * PORTRAIT_BOARD_SHARE)),
            )
            self.board.place((width - dimension) // 2, top, dimension)
            panel_top = top + dimension + gutter
            self.sidebar.place(margin, panel_top, width - margin * 2, height - panel_top - margin)

    def render_board(self) -> None:
        """Redraw the board from the current selection and position."""
        moves: list[Coord] = []
        captures: list[Coord] = []
        for coord in self.valid_targets:
            occupied = self.state.board[coord[0]][coord[1]] is not None
            (captures if occupied else moves).append(coord)
        self.board.render(
            BoardFrame(
                pieces=self.state.get_pieces(),
                selected=self.selected_sq,
                move_targets=moves,
                capture_targets=captures,
                last_move=self.last_move,
                cursor=self.cursor,
                colors=self._player_colors(),
            )
        )

    def clear_selection(self) -> None:
        """Deselect the current piece."""
        self.selected_sq = None
        self.valid_targets = []

    def _on_square(self, square: Coord) -> None:
        self.stage.focus_set()
        if not self._can_interact():
            return
        if self.selected_sq and square in self.valid_targets:
            self._commit_move(self.selected_sq, square)
            return
        piece = self.state.board[square[0]][square[1]]
        if piece and piece.owner == self.state.current_turn:
            self.selected_sq = square
            self.valid_targets = [move[1] for move in self.state.get_valid_moves_for_piece(*square)]
        else:
            self.clear_selection()
        self.render_board()

    def _on_arrow(self, delta: tuple[int, int], _event: tk.Event) -> None:
        self._move_cursor(delta)

    def _move_cursor(self, delta: tuple[int, int]) -> None:
        size = self.state.board_size
        current = self.cursor or self.selected_sq or (size - 1, 0)
        self.cursor = (
            max(0, min(size - 1, current[0] + delta[0])),
            max(0, min(size - 1, current[1] + delta[1])),
        )
        self.render_board()

    def _activate_cursor(self) -> None:
        if self.cursor is not None:
            self._on_square(self.cursor)

    def add_cycle_card(self) -> None:
        """Add the compact reminder of which piece beats which."""
        row = tk.Frame(self.side, bg=COLORS["card"])
        row.pack(fill=tk.X, pady=(METRICS.px(SPACE_L), 0))
        image = art.cycle_diagram_image(METRICS.px(CYCLE_THUMBNAIL), COLORS["ink_muted"])
        self._cycle_photo = ImageTk.PhotoImage(image, master=row)
        tk.Label(row, image=self._cycle_photo, bg=COLORS["card"]).pack(side=tk.LEFT)
        tk.Label(
            row,
            text=CYCLE_TEXT,
            font=font("caption"),
            bg=COLORS["card"],
            fg=COLORS["ink_muted"],
            justify=tk.LEFT,
        ).pack(side=tk.LEFT, padx=(METRICS.px(SPACE_M), 0))

    def add_history(self) -> None:
        """Add the scrolling move list."""
        section_title(self.side, "Moves").pack(
            fill=tk.X, pady=(METRICS.px(SPACE_L), METRICS.px(SPACE_S))
        )
        box = RoundedCard(self.side)
        box.pack(fill=tk.X)
        self.list_notation = tk.Listbox(
            box.body,
            bg=COLORS["card"],
            fg=COLORS["ink"],
            font=font("body"),
            bd=0,
            height=HISTORY_ROWS,
            highlightthickness=0,
            activestyle="none",
            selectbackground=COLORS["card"],
            selectforeground=COLORS["ink"],
            takefocus=0,
        )
        self.list_notation.pack(fill=tk.BOTH, expand=True)
        scroll = ThinScrollbar(box.body, self.list_notation.yview)
        self.list_notation.configure(yscrollcommand=scroll.set)

    def refresh_history(self) -> None:
        """Show the moves played so far, numbered per round."""
        self.list_notation.delete(0, tk.END)
        for index, notation in enumerate(self.state.notation):
            prefix = f"{index // 2 + 1}. " if index % 2 == 0 else "    "
            self.list_notation.insert(tk.END, f"{prefix}{notation}")
        self.list_notation.yview(tk.END)

    def add_status(self) -> tk.Label:
        """Add the single line that tells the player what is happening."""
        label = WrapLabel(self.side, font=font("heading"))
        label.pack(fill=tk.X, pady=(0, METRICS.px(SPACE_M)))
        return label

    def bind_hotkey(self, name: str, command: Callable[[], None]) -> None:
        """Bind a shortcut on the window for the lifetime of this view."""
        self.app.bind(HOTKEYS[name]["seq"], lambda _e: command())

    def unbind_hotkeys(self) -> None:
        """Remove every shortcut bound by this view."""
        for hotkey in HOTKEYS.values():
            self.app.unbind(hotkey["seq"])

    def show_rules(self, extra: str = "") -> None:
        """Show the rules in an alert."""
        text = (
            "Move any piece into the star corner of your opponent to win.\n\n"
            "Every piece moves one square in any of the 8 directions.\n\n"
            f"{CYCLE_TEXT}\n\n"
            "Matching pieces cannot capture each other.\n"
            "Green dots mark moves. A red outline marks a capture."
        )
        dialog = Dialog(self, "How to Play", f"{text}\n\n{extra}" if extra else text)
        dialog.add_action("Close", variant="primary", default=True, cancel=True)
        dialog.present()


def stat_line(parent: tk.Misc, caption: str) -> tk.Label:
    """Add a captioned value row and return the value label."""
    row = tk.Frame(parent, bg=parent.cget("bg"))
    row.pack(fill=tk.X, pady=(0, METRICS.px(SPACE_S)))
    field_label(row, caption).pack(side=tk.LEFT)
    value = tk.Label(row, font=font("body"), bg=parent.cget("bg"), fg=COLORS["ink"])
    value.pack(side=tk.RIGHT)
    return value

"""Shared board renderer drawn directly on a page canvas, used by every board screen."""

import tkinter as tk
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from PIL import Image, ImageTk

from src.core.game_logic import Coord, PieceSpec
from src.ui import art
from src.ui.theme import COLORS, font

LABEL_RATIO = 0.045
MIN_LABEL_ROOM = 14
BASE_TAG = "board-base"
DYNAMIC_TAG = "board-dynamic"

SquareHandler = Callable[[Coord], None]


@dataclass
class BoardFrame:
    """Everything needed to draw one board frame."""

    pieces: Iterable[PieceSpec] = ()
    selected: Coord | None = None
    move_targets: Iterable[Coord] = ()
    capture_targets: Iterable[Coord] = ()
    last_move: tuple[Coord, Coord] | None = None
    cursor: Coord | None = None
    colors: dict[int, str] = field(default_factory=dict)


class BoardLayer:
    """Draws the board at any size and translates pointer and keyboard input to squares."""

    def __init__(
        self,
        stage: tk.Canvas,
        board_size: int,
        on_square: SquareHandler,
        on_secondary: SquareHandler | None = None,
    ) -> None:
        self.stage = stage
        self.board_size = board_size
        self.on_square = on_square
        self.on_secondary = on_secondary
        self.origin: tuple[int, int] = (0, 0)
        self.square = 0
        self.label_room = 0
        self.frame = BoardFrame()
        self._photos: dict[object, ImageTk.PhotoImage] = {}
        self._base_photo: ImageTk.PhotoImage | None = None
        for tag in (BASE_TAG, DYNAMIC_TAG):
            stage.tag_bind(tag, "<Button-1>", self._on_click)
            stage.tag_bind(tag, "<Button-2>", self._on_secondary_click)
            stage.tag_bind(tag, "<Button-3>", self._on_secondary_click)

    def set_board_size(self, board_size: int) -> None:
        """Switch to another board size; the next ``place`` redraws it."""
        self.board_size = board_size

    def place(self, x: int, y: int, dimension: int) -> None:
        """Fit the board and its edge labels into a square area at (x, y)."""
        self.label_room = max(MIN_LABEL_ROOM, round(dimension * LABEL_RATIO))
        self.square = max(8, (dimension - self.label_room) // self.board_size)
        grid = self.square * self.board_size
        total = grid + self.label_room
        self.origin = (
            x + (dimension - total) // 2 + self.label_room,
            y + (dimension - total) // 2,
        )
        self._draw_base()
        self.render(self.frame)

    def extent(self) -> tuple[int, int, int, int]:
        """Return the drawn board rectangle including its edge labels."""
        grid = self.square * self.board_size
        left, top = self.origin
        return left - self.label_room, top, left + grid, top + grid + self.label_room

    def _draw_base(self) -> None:
        stage = self.stage
        stage.delete(BASE_TAG)
        image = art.board_base_image(self.board_size, self.square)
        self._base_photo = ImageTk.PhotoImage(image, master=stage)
        stage.create_image(*self.origin, anchor="nw", image=self._base_photo, tags=BASE_TAG)
        grid = self.square * self.board_size
        for index in range(self.board_size):
            center = self.square * index + self.square // 2
            stage.create_text(
                self.origin[0] + center,
                self.origin[1] + grid + self.label_room // 2,
                text=chr(65 + index),
                fill=COLORS["ink_muted"],
                font=font("caption"),
                tags=BASE_TAG,
            )
            stage.create_text(
                self.origin[0] - self.label_room // 2,
                self.origin[1] + center,
                text=str(self.board_size - index),
                fill=COLORS["ink_muted"],
                font=font("caption"),
                tags=BASE_TAG,
            )

    def _square_origin(self, coord: Coord) -> tuple[int, int]:
        return self.origin[0] + coord[1] * self.square, self.origin[1] + coord[0] * self.square

    def _photo(self, key: object, image_factory: Callable[[], Image.Image]) -> ImageTk.PhotoImage:
        if key not in self._photos:
            self._photos[key] = ImageTk.PhotoImage(image_factory(), master=self.stage)
        return self._photos[key]

    def _draw_overlay(self, kind: str, coord: Coord) -> None:
        x, y = self._square_origin(coord)
        photo = self._photo((kind, self.square), lambda: art.overlay_image(kind, self.square))
        self.stage.create_image(x, y, anchor="nw", image=photo, tags=DYNAMIC_TAG)

    def _draw_token(self, piece: PieceSpec, colors: dict[int, str]) -> None:
        r, c, owner, piece_type = piece
        color = colors.get(owner, COLORS["accent"])
        photo = self._photo(
            (piece_type, owner, color, self.square),
            lambda: art.token_image(piece_type, owner, color, self.square),
        )
        x, y = self._square_origin((r, c))
        self.stage.create_image(x, y, anchor="nw", image=photo, tags=DYNAMIC_TAG)

    def render(self, frame: BoardFrame) -> None:
        """Redraw markers and pieces for the given frame."""
        self.frame = frame
        if self.square == 0:
            return
        self.stage.delete(DYNAMIC_TAG)
        if frame.last_move:
            self._draw_overlay("last", frame.last_move[0])
            self._draw_overlay("last", frame.last_move[1])
        if frame.selected:
            self._draw_overlay("select", frame.selected)
        for piece in frame.pieces:
            self._draw_token(piece, frame.colors)
        for coord in frame.capture_targets:
            self._draw_overlay("capture", coord)
        for coord in frame.move_targets:
            self._draw_overlay("move", coord)
        if frame.cursor:
            self._draw_overlay("cursor", frame.cursor)

    def square_at(self, x: int, y: int) -> Coord | None:
        """Convert page coordinates to a board square, or None outside the grid."""
        if self.square == 0:
            return None
        row = (y - self.origin[1]) // self.square
        col = (x - self.origin[0]) // self.square
        if 0 <= row < self.board_size and 0 <= col < self.board_size:
            return row, col
        return None

    def _on_click(self, event: tk.Event) -> None:
        square = self.square_at(event.x, event.y)
        if square is not None:
            self.on_square(square)

    def _on_secondary_click(self, event: tk.Event) -> None:
        square = self.square_at(event.x, event.y)
        if square is not None and self.on_secondary is not None:
            self.on_secondary(square)

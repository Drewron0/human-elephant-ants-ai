"""A rounded data table with sticky header, hover, selection and thin scrollbars."""

import tkinter as tk
from collections.abc import Callable, Sequence
from tkinter import font as tkfont
from typing import Literal, NamedTuple

from PIL import ImageTk

from src.ui import art
from src.ui.scrolling import ThinScrollbar
from src.ui.theme import COLORS, METRICS, RADIUS, SPACE_M, SPACE_S, font

HEADER_HEIGHT = 40
ROW_HEIGHT = 44
SIDE_PADDING = SPACE_M
ELLIPSIS = "..."


class TableColumn(NamedTuple):
    """A column: stable key, title, minimum width and text alignment."""

    key: str
    title: str
    width: int
    anchor: Literal["w", "center"]


class DataTable(tk.Frame):
    """Shows rows of text and keeps one selected row."""

    def __init__(
        self,
        parent: tk.Misc,
        columns: Sequence[TableColumn],
        empty_text: str,
        on_select: Callable[[str | None], None] | None = None,
    ) -> None:
        super().__init__(parent, bg=parent.cget("bg"))
        self.columns = list(columns)
        self.empty_text = empty_text
        self.on_select = on_select
        self.rows: list[tuple[str, Sequence[object]]] = []
        self.selected: str | None = None
        self._hover: int | None = None
        self._widths: list[int] = []
        self._photos: dict[str, ImageTk.PhotoImage] = {}
        background = self.cget("bg")
        self.head = tk.Canvas(self, bg=background, highlightthickness=0, height=1, takefocus=0)
        self.head.pack(fill=tk.X)
        self.list_area = tk.Frame(self, bg=background)
        self.list_area.pack(fill=tk.BOTH, expand=True)
        self.rows_canvas = tk.Canvas(
            self.list_area, bg=background, highlightthickness=0, takefocus=0
        )
        self.rows_canvas.pack(fill=tk.BOTH, expand=True)
        self.vertical = ThinScrollbar(self.list_area, self.rows_canvas.yview)
        self.horizontal = ThinScrollbar(self.list_area, self._scroll_x, vertical=False)
        self.rows_canvas.configure(
            yscrollcommand=self.vertical.set, xscrollcommand=self._on_x_changed
        )
        self.rows_canvas.bind("<Configure>", lambda _e: self._render())
        self.rows_canvas.bind("<Motion>", self._on_motion)
        self.rows_canvas.bind("<Leave>", lambda _e: self._set_hover(None))
        self.rows_canvas.bind("<Button-1>", self._on_click)
        self.rows_canvas.bind("<MouseWheel>", self._on_wheel)

    def set_rows(self, rows: Sequence[tuple[str, Sequence[object]]]) -> None:
        """Replace the table contents, keeping the selection when its row remains."""
        self.rows = list(rows)
        if self.selected not in self.get_children():
            self.selected = None
        self._render()

    def get_children(self) -> list[str]:
        """Return the row identifiers in display order."""
        return [row_id for row_id, _ in self.rows]

    def values(self, row_id: str) -> Sequence[object]:
        """Return the cell values of a row."""
        return next(cells for candidate, cells in self.rows if candidate == row_id)

    def select(self, row_id: str | None) -> None:
        """Select a row and notify the listener."""
        self.selected = row_id
        self._draw_highlights()
        if self.on_select:
            self.on_select(row_id)

    def _row_height(self) -> int:
        return METRICS.px(ROW_HEIGHT)

    def _column_widths(self, available: int) -> list[int]:
        base = [METRICS.px(column.width) for column in self.columns]
        spread = max(1.0, available / sum(base))
        return [int(width * spread) for width in base]

    def _fit_text(self, text: str, width: int, typeface: tkfont.Font) -> str:
        if typeface.measure(text) <= width:
            return text
        while text and typeface.measure(text + ELLIPSIS) > width:
            text = text[:-1]
        return text + ELLIPSIS

    def _cell_position(self, index: int, left: int) -> tuple[int, Literal["w", "center"]]:
        pad = METRICS.px(SIDE_PADDING)
        if self.columns[index].anchor == "center":
            return left + self._widths[index] // 2, "center"
        return left + pad, "w"

    def _render(self) -> None:
        available = self.rows_canvas.winfo_width()
        if available <= 1:
            return
        self._widths = self._column_widths(available)
        total = sum(self._widths)
        self._draw_header(total)
        self._draw_rows(total, available)
        self._draw_highlights()

    def _draw_header(self, total: int) -> None:
        head = self.head
        height = METRICS.px(HEADER_HEIGHT)
        head.configure(height=height + METRICS.px(SPACE_S), scrollregion=(0, 0, total, height))
        head.delete("all")
        photo = ImageTk.PhotoImage(
            art.panel_image(
                total, height, METRICS.px(RADIUS), COLORS["card_alt"], COLORS["card_alt"]
            ),
            master=head,
        )
        self._photos["head"] = photo
        head.create_image(0, 0, anchor="nw", image=photo)
        left = 0
        for index, column in enumerate(self.columns):
            x, anchor = self._cell_position(index, left)
            head.create_text(
                x,
                height / 2,
                text=column.title,
                anchor=anchor,
                font=font("caption"),
                fill=COLORS["ink_muted"],
            )
            left += self._widths[index]

    def _draw_rows(self, total: int, available: int) -> None:
        canvas = self.rows_canvas
        canvas.delete("all")
        row_height = self._row_height()
        if not self.rows:
            canvas.configure(scrollregion=(0, 0, available, 1))
            canvas.create_text(
                available / 2,
                canvas.winfo_height() / 2,
                text=self.empty_text,
                font=font("body"),
                fill=COLORS["ink_muted"],
            )
            return
        typeface = tkfont.Font(root=self, name=font("body"), exists=True)
        pad = METRICS.px(SIDE_PADDING)
        canvas.configure(scrollregion=(0, 0, total, row_height * len(self.rows)))
        for row, (_, cells) in enumerate(self.rows):
            center = row * row_height + row_height / 2
            left = 0
            for index, cell in enumerate(cells):
                x, anchor = self._cell_position(index, left)
                canvas.create_text(
                    x,
                    center,
                    text=self._fit_text(str(cell), self._widths[index] - pad, typeface),
                    anchor=anchor,
                    font=font("body"),
                    fill=COLORS["ink"],
                    tags="cell",
                )
                left += self._widths[index]
            if row < len(self.rows) - 1:
                bottom = (row + 1) * row_height
                canvas.create_line(0, bottom, total, bottom, fill=COLORS["line"], tags="rule")

    def _highlight_photo(self, name: str, color: str, width: int) -> ImageTk.PhotoImage:
        photo = ImageTk.PhotoImage(
            art.panel_image(width, self._row_height(), METRICS.px(RADIUS), color, color),
            master=self.rows_canvas,
        )
        self._photos[name] = photo
        return photo

    def _draw_highlights(self) -> None:
        canvas = self.rows_canvas
        canvas.delete("highlight")
        if not self._widths:
            return
        total = sum(self._widths)
        row_height = self._row_height()
        marks: list[tuple[int, str, str]] = []
        children = self.get_children()
        if self._hover is not None and self._hover < len(children):
            marks.append((self._hover, "hover", COLORS["card_alt"]))
        if self.selected in children:
            marks.append((children.index(self.selected), "selected", COLORS["accent_soft"]))
        for row, name, color in marks:
            canvas.create_image(
                0,
                row * row_height,
                anchor="nw",
                image=self._highlight_photo(name, color, total),
                tags="highlight",
            )
            canvas.tag_lower("highlight")

    def _row_at(self, event: tk.Event) -> int | None:
        y = int(self.rows_canvas.canvasy(event.y))
        row = y // self._row_height()
        return row if 0 <= row < len(self.rows) else None

    def _set_hover(self, row: int | None) -> None:
        if row != self._hover:
            self._hover = row
            self._draw_highlights()

    def _on_motion(self, event: tk.Event) -> None:
        self._set_hover(self._row_at(event))

    def _on_click(self, event: tk.Event) -> None:
        row = self._row_at(event)
        if row is not None:
            self.select(self.rows[row][0])

    def _on_wheel(self, event: tk.Event) -> None:
        if self.rows_canvas.yview() != (0.0, 1.0):
            self.rows_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def _scroll_x(self, *arguments: object) -> None:
        self.rows_canvas.xview(*arguments)

    def _on_x_changed(self, first: float, last: float) -> None:
        self.horizontal.set(first, last)
        self.head.xview_moveto(first)

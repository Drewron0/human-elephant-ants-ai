"""Thin rounded scrollbars and the scrolling container used across the screens."""

import tkinter as tk
from collections.abc import Callable
from typing import Any

from src.ui.theme import COLORS, METRICS

BAR_THICKNESS = 6
SCROLL_GUTTER = 16


class ThinScrollbar(tk.Canvas):
    """An overlay scrollbar drawn as a rounded thumb; it hides when nothing scrolls."""

    def __init__(
        self,
        parent: tk.Misc,
        command: Callable[..., Any],
        vertical: bool = True,
    ) -> None:
        thickness = METRICS.px(BAR_THICKNESS)
        super().__init__(
            parent,
            bg=parent.cget("bg"),
            highlightthickness=0,
            bd=0,
            width=thickness if vertical else 1,
            height=1 if vertical else thickness,
            cursor="arrow",
        )
        self.command = command
        self.vertical = vertical
        self.first = 0.0
        self.last = 1.0
        self._grab_offset = 0.0
        self.bind("<Configure>", lambda _e: self._render())
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)

    def set(self, first: float, last: float) -> None:
        """Receive the visible range from the scrolled widget."""
        self.first, self.last = float(first), float(last)
        needed = self.first > 0.0 or self.last < 1.0
        if needed and not self.winfo_ismapped():
            if self.vertical:
                self.place(relx=1.0, rely=0.0, relheight=1.0, anchor="ne")
            else:
                self.place(relx=0.0, rely=1.0, relwidth=1.0, anchor="sw")
        elif not needed and self.winfo_ismapped():
            self.place_forget()
        self._render()

    def _length(self) -> int:
        return self.winfo_height() if self.vertical else self.winfo_width()

    def _render(self) -> None:
        self.delete("all")
        thickness = int(self.cget("width" if self.vertical else "height"))
        length = self._length()
        if length <= 1:
            return
        cap = thickness / 2
        start = cap + self.first * (length - thickness)
        end = max(start, cap + self.last * (length - thickness))
        points = (cap, start, cap, end) if self.vertical else (start, cap, end, cap)
        self.create_line(
            *points,
            width=thickness,
            capstyle=tk.ROUND,
            fill=COLORS["scroll_thumb"],
        )

    def _position(self, event: tk.Event) -> float:
        offset = event.y if self.vertical else event.x
        return offset / max(1, self._length())

    def _on_press(self, event: tk.Event) -> None:
        position = self._position(event)
        inside = self.first <= position <= self.last
        self._grab_offset = position - self.first if inside else (self.last - self.first) / 2
        self.command("moveto", position - self._grab_offset)

    def _on_drag(self, event: tk.Event) -> None:
        self.command("moveto", self._position(event) - self._grab_offset)


class ScrollArea(tk.Frame):
    """A vertical scroll container; its overlay bar never changes the content width."""

    def __init__(self, parent: tk.Misc) -> None:
        background = parent.cget("bg")
        super().__init__(parent, bg=background)
        self.canvas = tk.Canvas(self, bg=background, highlightthickness=0, takefocus=0)
        self.scrollbar = ThinScrollbar(self, self.canvas.yview)
        self.content = tk.Frame(self.canvas, bg=background)
        self._window = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.content.bind("<Configure>", lambda _e: self._sync_region())
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.bind("<Enter>", lambda _e: self._bind_wheel())
        self.bind("<Leave>", self._on_leave)
        self.bind("<Destroy>", self._on_destroy)

    def _sync_region(self) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_resize(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self._window, width=event.width - METRICS.px(SCROLL_GUTTER))

    def _bind_wheel(self) -> None:
        self.bind_all("<MouseWheel>", self._on_wheel)

    def _on_leave(self, event: tk.Event) -> None:
        """Keep wheel scrolling while the pointer is over a child of this area."""
        under = self.winfo_containing(event.x_root, event.y_root)
        if under is None or not str(under).startswith(str(self)):
            self._unbind_wheel()

    def _unbind_wheel(self) -> None:
        self.unbind_all("<MouseWheel>")

    def _on_destroy(self, event: tk.Event) -> None:
        if event.widget is self:
            self._unbind_wheel()

    def _on_wheel(self, event: tk.Event) -> None:
        if self.canvas.yview() != (0.0, 1.0):
            self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

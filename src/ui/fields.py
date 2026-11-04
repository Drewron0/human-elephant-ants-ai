"""Rounded text fields and dropdowns with one shared look."""

import tkinter as tk
from collections.abc import Callable, Sequence

from PIL import ImageTk

from src.ui import art
from src.ui.theme import COLORS, METRICS, RADIUS, SPACE_S, font
from src.ui.widgets import track_control

FIELD_PADDING = 14
CHEVRON_SIZE = 14
ROW_HEIGHT = 40
POPUP_GAP = 6
POPUP_PADDING = 6
WINDOW_EDGE = 16


class Field(tk.Canvas):
    """A rounded input: free text, a fixed dropdown, or text with suggestions."""

    def __init__(
        self,
        parent: tk.Misc,
        variable: tk.StringVar,
        options: Sequence[str] = (),
        editable: bool = True,
        on_select: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            bg=parent.cget("bg"),
            highlightthickness=0,
            bd=0,
            takefocus=0 if editable else 1,
            cursor="xterm" if editable else "hand2",
            height=METRICS.target(),
        )
        self.variable = variable
        self.options = list(options)
        self.editable = editable
        self.on_select = on_select
        self.popup: OptionPopup | None = None
        self._hover = False
        self._photos: list[ImageTk.PhotoImage] = []
        self.control: tk.Widget
        if editable:
            self.control = tk.Entry(
                self,
                textvariable=variable,
                font=font("body"),
                bd=0,
                relief=tk.FLAT,
                highlightthickness=0,
                bg=COLORS["card"],
                fg=COLORS["ink"],
                insertbackground=COLORS["ink"],
                selectbackground=COLORS["accent_soft"],
                selectforeground=COLORS["ink"],
            )
        else:
            self.control = tk.Label(
                self,
                textvariable=variable,
                font=font("body"),
                bg=COLORS["card"],
                fg=COLORS["ink"],
                anchor="w",
                padx=0,
                cursor="hand2",
            )
        self._window_item = self.create_window(0, 0, anchor="w", window=self.control)
        for widget in (self, self.control):
            widget.bind("<Enter>", lambda _e: self._set_hover(True), add="+")
            widget.bind("<Leave>", lambda _e: self._set_hover(False), add="+")
            widget.bind("<FocusIn>", lambda _e: self._render(), add="+")
            widget.bind("<FocusOut>", lambda _e: self._render(), add="+")
        self.bind("<Configure>", lambda _e: self._render())
        self.bind("<Button-1>", self._on_click)
        if not editable:
            self.control.bind("<Button-1>", self._on_click)
            self.bind("<space>", lambda _e: self.open_popup())
            self.bind("<Return>", lambda _e: self.open_popup())
        if options:
            target = self if not editable else self.control
            target.bind("<Down>", lambda _e: self.open_popup())
        track_control(self)

    def remeasure(self) -> None:
        """Keep the minimum target height at the current density."""
        self.configure(height=METRICS.target())
        self._render()

    def get(self) -> str:
        """Return the current value."""
        return self.variable.get()

    def _set_hover(self, hover: bool) -> None:
        self._hover = hover
        self._render()

    def _is_focused(self) -> bool:
        focused = self.focus_get()
        return focused is self or focused is self.control

    def _on_click(self, _event: tk.Event) -> None:
        if self.editable:
            self.control.focus_set()
            if self.options and _event.x >= self.winfo_width() - self._chevron_room():
                self.open_popup()
        else:
            self.focus_set()
            self.open_popup()

    def _chevron_room(self) -> int:
        return METRICS.px(CHEVRON_SIZE + FIELD_PADDING * 2) if self.options else 0

    def _render(self) -> None:
        width, height = self.winfo_width(), self.winfo_height()
        if width <= 1:
            return
        if self._is_focused():
            border = COLORS["focus"]
        elif self._hover:
            border = COLORS["line_strong"]
        else:
            border = COLORS["line"]
        self.delete("face")
        face = ImageTk.PhotoImage(
            art.panel_image(width, height, METRICS.px(RADIUS), COLORS["card"], border), master=self
        )
        self._photos = [face]
        self.create_image(0, 0, anchor="nw", image=face, tags="face")
        self.tag_lower("face")
        pad = METRICS.px(FIELD_PADDING)
        if self.options:
            size = METRICS.px(CHEVRON_SIZE)
            chevron = ImageTk.PhotoImage(
                art.icon_image("chevron", size, COLORS["ink_muted"]), master=self
            )
            self._photos.append(chevron)
            self.create_image(width - pad - size // 2, height / 2, image=chevron, tags="face")
        self.coords(self._window_item, pad, height / 2)
        self.itemconfigure(
            self._window_item,
            width=max(1, width - pad - max(pad, self._chevron_room())),
        )

    def open_popup(self) -> None:
        """Show the option list, or close it when it is already open."""
        if self.popup is not None:
            self.popup.close()
        elif self.options:
            self.popup = OptionPopup(self)

    def choose(self, value: str) -> None:
        """Apply a chosen option."""
        self.variable.set(value)
        if self.on_select:
            self.on_select(value)


class OptionPopup(tk.Canvas):
    """The dropdown list: a rounded overlay inside the window, above the current screen."""

    def __init__(self, field: Field) -> None:
        window = field.winfo_toplevel()
        self.field = field
        self.row_height = METRICS.px(ROW_HEIGHT)
        self.pad = METRICS.px(POPUP_PADDING)
        self.options = field.options
        current = field.get()
        self.active_row = self.options.index(current) if current in self.options else 0
        self._current = current
        self._width = field.winfo_width()
        self._height = self.row_height * len(self.options) + self.pad * 2
        self._photos: list[ImageTk.PhotoImage] = []
        super().__init__(
            window,
            bg=field.cget("bg"),
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            takefocus=1,
        )
        self._draw()
        self.place(
            x=field.winfo_rootx() - window.winfo_rootx(),
            y=self._top(window),
            width=self._width,
            height=self._height,
        )
        tk.Misc.tkraise(self)
        self.bind("<Motion>", self._on_motion)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Up>", lambda _e: self._step(-1))
        self.bind("<Down>", lambda _e: self._step(1))
        self.bind("<Return>", lambda _e: self._choose(self.active_row))
        self.bind("<space>", lambda _e: self._choose(self.active_row))
        self.bind("<Escape>", lambda _e: self.close())
        field.bind("<Destroy>", lambda _e: self.close(), add="+")
        self.update_idletasks()
        self.grab_set()
        self.focus_set()

    def _top(self, window: tk.Misc) -> int:
        field = self.field
        gap = METRICS.px(POPUP_GAP)
        edge = METRICS.px(WINDOW_EDGE)
        field_top = field.winfo_rooty() - window.winfo_rooty()
        below = field_top + field.winfo_height() + gap
        if below + self._height <= window.winfo_height() - edge:
            return below
        above = field_top - gap - self._height
        if above >= edge:
            return above
        return max(edge, window.winfo_height() - edge - self._height)

    def _draw(self) -> None:
        self.delete("all")
        radius = METRICS.px(RADIUS)
        self._photos = [
            ImageTk.PhotoImage(
                art.panel_image(
                    self._width, self._height, radius, COLORS["card"], COLORS["line_strong"]
                ),
                master=self,
            )
        ]
        self.create_image(0, 0, anchor="nw", image=self._photos[0])
        row_width = self._width - self.pad * 2
        top = self.pad + self.active_row * self.row_height
        highlight = ImageTk.PhotoImage(
            art.panel_image(
                row_width,
                self.row_height,
                METRICS.px(RADIUS - 4),
                COLORS["card_alt"],
                COLORS["card_alt"],
            ),
            master=self,
        )
        self._photos.append(highlight)
        self.create_image(self.pad, top, anchor="nw", image=highlight)
        text_x = self.pad + METRICS.px(SPACE_S)
        for row, option in enumerate(self.options):
            center = self.pad + row * self.row_height + self.row_height / 2
            self.create_text(
                text_x,
                center,
                text=option,
                anchor="w",
                font=font("body"),
                fill=COLORS["ink"],
            )
            if option == self._current:
                size = METRICS.px(14)
                check = ImageTk.PhotoImage(
                    art.icon_image("check", size, COLORS["ink"]), master=self
                )
                self._photos.append(check)
                self.create_image(
                    self._width - self.pad - METRICS.px(SPACE_S) - size // 2, center, image=check
                )

    def _row_at(self, y: int) -> int | None:
        row = (y - self.pad) // self.row_height
        return row if 0 <= row < len(self.options) else None

    def _is_inside(self, event: tk.Event) -> bool:
        return 0 <= event.x < self._width and 0 <= event.y < self._height

    def _on_motion(self, event: tk.Event) -> None:
        row = self._row_at(event.y) if self._is_inside(event) else None
        if row is not None and row != self.active_row:
            self.active_row = row
            self._draw()

    def _on_press(self, event: tk.Event) -> None:
        if not self._is_inside(event):
            self.close()

    def _on_release(self, event: tk.Event) -> None:
        """Choose on release; the release of the press that opened the list lands outside."""
        row = self._row_at(event.y) if self._is_inside(event) else None
        if row is not None:
            self._choose(row)

    def _step(self, delta: int) -> None:
        self.active_row = (self.active_row + delta) % len(self.options)
        self._draw()

    def _choose(self, row: int) -> None:
        value = self.options[row]
        self.close()
        self.field.choose(value)

    def close(self) -> None:
        """Remove the list and return focus to its field."""
        if not self.winfo_exists():
            return
        field = self.field
        field.popup = None
        self.grab_release()
        self.destroy()
        if field.winfo_exists():
            target = field.control if field.editable else field
            target.focus_set()

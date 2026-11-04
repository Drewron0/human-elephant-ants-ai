"""Shared controls with one look: buttons, cards, switches, progress and labels."""

import tkinter as tk
import weakref
from collections.abc import Callable, Sequence
from functools import partial
from tkinter import font as tkfont
from typing import Any, Literal, Protocol

from PIL import Image, ImageTk

from src.ui import art
from src.ui.theme import COLORS, METRICS, RADIUS, SPACE_S, font

BUTTON_PADDING = 18
ICON_SIZE = 16
ICON_GAP = 8
SWITCH_SIZE = (46, 28)
RAISE_DEPTH = 5
TALL_EXTRA = 8
PROGRESS_HEIGHT = 8
ACTIVE_BORDER = 2
TOOL_PADDING = 6

Variant = Literal["primary", "gold", "secondary", "destructive"]
VARIANTS: dict[str, dict[str, str]] = {
    "primary": {
        "fill": "accent",
        "hover": "accent_hover",
        "pressed": "accent_pressed",
        "border": "accent",
        "ink": "on_accent",
    },
    "gold": {
        "fill": "gold",
        "hover": "gold_hover",
        "pressed": "gold_pressed",
        "border": "gold",
        "ink": "ink",
    },
    "secondary": {
        "fill": "secondary",
        "hover": "secondary_hover",
        "pressed": "secondary_pressed",
        "border": "line_strong",
        "ink": "ink",
    },
    "destructive": {
        "fill": "secondary",
        "hover": "secondary_hover",
        "pressed": "secondary_pressed",
        "border": "danger",
        "ink": "danger",
    },
}
RAISED_LIPS: dict[str, str] = {
    "primary": "accent_pressed",
    "gold": "gold_pressed",
    "secondary": "line_strong",
    "destructive": "danger",
}


class Remeasurable(Protocol):
    """A control that recalculates its size when the density changes."""

    def remeasure(self) -> None:
        """Recompute the control's size."""

    def winfo_exists(self) -> int:
        """Return whether the widget still exists."""


_live_controls: "weakref.WeakSet[Any]" = weakref.WeakSet()


def track_control(control: Remeasurable) -> None:
    """Keep a control updated across density changes."""
    _live_controls.add(control)


def refresh_controls() -> None:
    """Remeasure every control after a density change."""
    for control in list(_live_controls):
        if control.winfo_exists():
            control.remeasure()


class PillButton(tk.Canvas):
    """The standard button, with hover, pressed, disabled and keyboard focus states."""

    def __init__(
        self,
        parent: tk.Misc,
        text: str,
        command: Callable[[], Any] | None = None,
        variant: Variant = "secondary",
        icon: str | None = None,
    ) -> None:
        super().__init__(
            parent,
            bg=parent.cget("bg"),
            highlightthickness=0,
            bd=0,
            takefocus=1,
            cursor="hand2",
        )
        self.text = text
        self.command = command
        self.variant = variant
        self.icon = icon
        self.enabled = True
        self._hover = False
        self._pressed = False
        self._images: list[ImageTk.PhotoImage] = []
        self.bind("<Enter>", lambda _e: self._set_hover(True))
        self.bind("<Leave>", lambda _e: self._set_hover(False))
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Configure>", lambda _e: self._render())
        self.bind("<FocusIn>", lambda _e: self._render())
        self.bind("<FocusOut>", lambda _e: self._render())
        self.bind("<Return>", lambda _e: self.invoke())
        self.bind("<space>", lambda _e: self.invoke())
        track_control(self)
        self.remeasure()

    def _text_width(self) -> int:
        return tkfont.Font(root=self, name=font("heading"), exists=True).measure(self.text)

    def remeasure(self) -> None:
        """Request a natural size from the text and icon at the current density."""
        icon_width = METRICS.px(ICON_SIZE + ICON_GAP) if self.icon else 0
        self.configure(
            width=self._text_width() + icon_width + METRICS.px(BUTTON_PADDING) * 2,
            height=self._control_height(),
        )
        self._render()

    def _control_height(self) -> int:
        return METRICS.target()

    def _face_image(
        self, width: int, height: int, fill: str, border: str, focused: bool
    ) -> Image.Image:
        return art.pill_image(width, height, METRICS.px(RADIUS), fill, border, focused)

    def _label_y(self, height: int) -> float:
        return height / 2

    def invoke(self) -> None:
        """Run the command when enabled, as a click would."""
        if self.enabled and self.command:
            self.command()

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the control, dimming it when disabled."""
        self.enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow", takefocus=1 if enabled else 0)
        self._render()

    def set_variant(self, variant: Variant) -> None:
        """Switch to another color role."""
        self.variant = variant
        self._render()

    def _set_hover(self, hover: bool) -> None:
        self._hover = hover
        if not hover:
            self._pressed = False
        self._render()

    def _on_press(self, _event: tk.Event) -> None:
        if self.enabled:
            self._pressed = True
            self.focus_set()
            self._render()

    def _on_release(self, event: tk.Event) -> None:
        was_pressed = self._pressed
        self._pressed = False
        self._render()
        if was_pressed and 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height():
            self.invoke()

    def _render(self) -> None:
        mapped = self.winfo_width() > 1
        width = self.winfo_width() if mapped else int(self.cget("width"))
        height = self.winfo_height() if mapped else int(self.cget("height"))
        scheme = VARIANTS[self.variant]
        if not self.enabled:
            fill, ink, border = COLORS["disabled"], COLORS["disabled_ink"], COLORS["disabled"]
        else:
            state = "pressed" if self._pressed else "hover" if self._hover else "fill"
            fill, ink, border = (
                COLORS[scheme[state]],
                COLORS[scheme["ink"]],
                COLORS[scheme["border"]],
            )
        focused = self.enabled and self.focus_get() is self
        photo = ImageTk.PhotoImage(
            self._face_image(width, height, fill, border, focused), master=self
        )
        self._images = [photo]
        self.delete("all")
        self.create_image(0, 0, anchor="nw", image=photo)

        center_y = self._label_y(height)
        center_x = width / 2
        if self.icon:
            measure = self._text_width()
            icon_px = METRICS.px(ICON_SIZE)
            gap = METRICS.px(ICON_GAP)
            start = center_x - (icon_px + gap + measure) / 2
            icon_photo = ImageTk.PhotoImage(art.icon_image(self.icon, icon_px, ink), master=self)
            self._images.append(icon_photo)
            self.create_image(start + icon_px / 2, center_y, image=icon_photo)
            center_x = start + icon_px + gap + measure / 2
        self.create_text(center_x, center_y, text=self.text, fill=ink, font=font("heading"))


class RaisedButton(PillButton):
    """A menu button with visible thickness; pressing sinks the face onto its lip."""

    def __init__(
        self,
        parent: tk.Misc,
        text: str,
        command: Callable[[], Any],
        variant: Variant,
        icon: str,
        tall: bool,
    ) -> None:
        self.tall = tall
        super().__init__(parent, text, command, variant, icon)

    def _depth(self) -> int:
        return METRICS.px(RAISE_DEPTH)

    def _control_height(self) -> int:
        return METRICS.target() + self._depth() + (METRICS.px(TALL_EXTRA) if self.tall else 0)

    def _face_image(
        self, width: int, height: int, fill: str, border: str, focused: bool
    ) -> Image.Image:
        return art.raised_button_image(
            width,
            height,
            METRICS.px(RADIUS),
            self._depth(),
            fill,
            COLORS[RAISED_LIPS[self.variant]],
            self._pressed,
            focused,
        )

    def _label_y(self, height: int) -> float:
        sink = self._depth() * art.PRESS_SINK if self._pressed else 0
        return (height - self._depth()) / 2 + sink


class ToolButton(tk.Canvas):
    """A square picture button that stays highlighted while it is the selected tool."""

    def __init__(
        self,
        parent: tk.Misc,
        picture: Callable[[int], Image.Image],
        command: Callable[[], Any],
    ) -> None:
        super().__init__(
            parent, bg=parent.cget("bg"), highlightthickness=0, bd=0, takefocus=1, cursor="hand2"
        )
        self.picture = picture
        self.command = command
        self.selected = False
        self._hover = False
        self._size = METRICS.target()
        self._images: list[ImageTk.PhotoImage] = []
        self.bind("<Enter>", lambda _e: self._set_hover(True))
        self.bind("<Leave>", lambda _e: self._set_hover(False))
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<FocusIn>", lambda _e: self._render())
        self.bind("<FocusOut>", lambda _e: self._render())
        self.bind("<Return>", lambda _e: self.command())
        self.bind("<space>", lambda _e: self.command())
        self.set_size(self._size)

    def set_size(self, size: int) -> None:
        """Resize the square button."""
        self._size = size
        self.configure(width=size, height=size)
        self._render()

    def set_selected(self, selected: bool) -> None:
        """Mark this button as the active tool."""
        self.selected = selected
        self._render()

    def _set_hover(self, hover: bool) -> None:
        self._hover = hover
        self._render()

    def _on_release(self, event: tk.Event) -> None:
        if 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height():
            self.command()

    def _render(self) -> None:
        size = self._size
        if self.selected:
            fill, border = COLORS["accent_soft"], COLORS["accent"]
        elif self._hover:
            fill, border = COLORS["card_alt"], COLORS["line_strong"]
        else:
            fill, border = COLORS["card"], COLORS["card"]
        if self.focus_get() is self:
            border = COLORS["focus"]
        edge = ACTIVE_BORDER if self.selected else 1
        face = ImageTk.PhotoImage(
            art.panel_image(size, size, METRICS.px(RADIUS), fill, border, edge), master=self
        )
        inner = max(1, size - METRICS.px(TOOL_PADDING) * 2)
        symbol = ImageTk.PhotoImage(self.picture(inner), master=self)
        self._images = [face, symbol]
        self.delete("all")
        self.create_image(0, 0, anchor="nw", image=face)
        self.create_image(size / 2, size / 2, image=symbol)


class RoundedCard(tk.Canvas):
    """A rounded container; children go into ``body`` and the card fits their height."""

    def __init__(self, parent: tk.Misc, padding: int = 12) -> None:
        pad = METRICS.px(padding)
        super().__init__(
            parent, bg=parent.cget("bg"), highlightthickness=0, bd=0, height=pad * 2 + 1
        )
        self.padding = padding
        self.border = COLORS["line"]
        self.border_width = 1
        self._photo: ImageTk.PhotoImage | None = None
        self._image_item = self.create_image(0, 0, anchor="nw")
        self.body = tk.Frame(self, bg=COLORS["card"])
        self._window_item = self.create_window(pad, pad, anchor="nw", window=self.body)
        self.body.bind("<Configure>", lambda _e: self.remeasure())
        self.bind("<Configure>", self._on_resize)
        track_control(self)

    def remeasure(self) -> None:
        """Fit the card to the height of its content."""
        pad = METRICS.px(self.padding)
        self.coords(self._window_item, pad, pad)
        height = self.body.winfo_reqheight() + pad * 2
        if int(self.cget("height")) != height:
            self.configure(height=height)

    def _on_resize(self, event: tk.Event) -> None:
        self.itemconfigure(
            self._window_item, width=max(1, event.width - METRICS.px(self.padding) * 2)
        )
        self._draw(event.width, event.height)

    def _draw(self, width: int, height: int) -> None:
        if width <= 1 or height <= 1:
            return
        image = art.panel_image(
            width,
            height,
            METRICS.px(RADIUS),
            COLORS["card"],
            self.border,
            self.border_width,
        )
        self._photo = ImageTk.PhotoImage(image, master=self)
        self.itemconfigure(self._image_item, image=self._photo)

    def set_active(self, active: bool) -> None:
        """Mark the card as current with a stronger accent border."""
        self.border = COLORS["accent"] if active else COLORS["line"]
        self.border_width = ACTIVE_BORDER if active else 1
        self._draw(self.winfo_width(), self.winfo_height())


class SegmentedControl(tk.Frame):
    """Mutually exclusive options; the selected segment uses the accent role."""

    def __init__(
        self,
        parent: tk.Misc,
        options: Sequence[tuple[str, str]],
        default_val: str,
        on_change: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent, bg=parent.cget("bg"))
        self.selected_val = default_val
        self.on_change = on_change
        self.buttons: dict[str, PillButton] = {}
        for index, (label, value) in enumerate(options):
            button = PillButton(self, label, command=partial(self.select, value))
            button.grid(
                row=0, column=index, sticky="ew", padx=(0 if index == 0 else METRICS.px(SPACE_S), 0)
            )
            self.columnconfigure(index, weight=1)
            self.buttons[value] = button
        self._update_appearance()

    def select(self, value: str) -> None:
        """Select an option and notify the listener when it changed."""
        if value == self.selected_val:
            return
        self.selected_val = value
        self._update_appearance()
        if self.on_change:
            self.on_change(value)

    def get(self) -> str:
        """Return the selected value."""
        return self.selected_val

    def _update_appearance(self) -> None:
        for value, button in self.buttons.items():
            button.set_variant("primary" if value == self.selected_val else "secondary")


class Switch(tk.Frame):
    """A labelled on/off toggle bound to a BooleanVar."""

    def __init__(self, parent: tk.Misc, text: str, variable: tk.BooleanVar) -> None:
        super().__init__(parent, bg=parent.cget("bg"))
        self.variable = variable
        self._photo: ImageTk.PhotoImage | None = None
        self.toggle_area = tk.Canvas(
            self,
            bg=parent.cget("bg"),
            highlightthickness=0,
            takefocus=1,
            cursor="hand2",
        )
        self.toggle_area.pack(side=tk.LEFT)
        label = tk.Label(
            self,
            text=text,
            font=font("body"),
            bg=parent.cget("bg"),
            fg=COLORS["ink"],
            cursor="hand2",
        )
        label.pack(side=tk.LEFT, padx=(METRICS.px(SPACE_S), 0))
        for widget in (self.toggle_area, label):
            widget.bind("<Button-1>", lambda _e: self.toggle())
        self.toggle_area.bind("<space>", lambda _e: self.toggle())
        self.toggle_area.bind("<Return>", lambda _e: self.toggle())
        self.toggle_area.bind("<FocusIn>", lambda _e: self._render())
        self.toggle_area.bind("<FocusOut>", lambda _e: self._render())
        self._render()

    def toggle(self) -> None:
        """Flip the switch."""
        self.variable.set(not self.variable.get())
        self._render()

    def _render(self) -> None:
        width, height = METRICS.target(), METRICS.px(SWITCH_SIZE[1])
        area_height = METRICS.target()
        canvas = self.toggle_area
        canvas.configure(width=width + 4, height=area_height)
        canvas.delete("all")
        top = (area_height - height) // 2
        on = self.variable.get()
        focused = canvas.focus_get() is canvas
        color = COLORS["accent"] if on else COLORS["line_strong"]
        image = art.pill_image(width, height, height // 2, color, color, focused)
        self._photo = ImageTk.PhotoImage(image, master=canvas)
        canvas.create_image(2, top, anchor="nw", image=self._photo)
        pad = 3
        x0 = 2 + width - height + pad if on else 2 + pad
        canvas.create_oval(
            x0,
            top + pad,
            x0 + height - pad * 2,
            top + height - pad,
            fill=COLORS["card"],
            outline="",
        )


class ProgressBar(tk.Canvas):
    """A slim rounded progress indicator."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(
            parent,
            bg=parent.cget("bg"),
            highlightthickness=0,
            bd=0,
            height=METRICS.px(PROGRESS_HEIGHT),
        )
        self.value = 0.0
        self.maximum = 1.0
        self.bind("<Configure>", lambda _e: self._render())

    def set(self, value: float, maximum: float | None = None) -> None:
        """Update the progress, optionally changing the total."""
        self.value = value
        if maximum is not None:
            self.maximum = max(1.0, maximum)
        self._render()

    def _render(self) -> None:
        self.delete("all")
        thickness = int(self.cget("height"))
        middle = thickness / 2
        start = thickness / 2
        end = max(start, self.winfo_width() - thickness / 2)
        self.create_line(
            start,
            middle,
            end,
            middle,
            width=thickness,
            capstyle=tk.ROUND,
            fill=COLORS["card_alt"],
        )
        if self.value > 0:
            filled = start + (end - start) * min(1.0, self.value / self.maximum)
            self.create_line(
                start,
                middle,
                filled,
                middle,
                width=thickness,
                capstyle=tk.ROUND,
                fill=COLORS["accent"],
            )


class WrapLabel(tk.Label):
    """A label that rewraps its text to the width it is given."""

    def __init__(self, parent: tk.Misc, text: str = "", **options: Any) -> None:
        options.setdefault("bg", parent.cget("bg"))
        options.setdefault("fg", COLORS["ink"])
        options.setdefault("font", font("body"))
        options.setdefault("justify", tk.LEFT)
        options.setdefault("anchor", "w")
        options.setdefault("padx", 0)
        super().__init__(parent, text=text, **options)
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event: tk.Event) -> None:
        if event.width > 1 and int(self.cget("wraplength")) != event.width:
            self.configure(wraplength=event.width)


def field_label(parent: tk.Misc, text: str) -> tk.Label:
    """Create a caption for a form field or statistic."""
    return tk.Label(
        parent,
        text=text,
        font=font("caption"),
        bg=parent.cget("bg"),
        fg=COLORS["ink_muted"],
        anchor="w",
        padx=0,
    )


def section_title(parent: tk.Misc, text: str) -> tk.Label:
    """Create a heading for a group of content."""
    return tk.Label(
        parent,
        text=text,
        font=font("heading"),
        bg=parent.cget("bg"),
        fg=COLORS["ink"],
        anchor="w",
        padx=0,
    )


def divider(parent: tk.Misc) -> tk.Frame:
    """Create a thin separator line."""
    return tk.Frame(parent, bg=COLORS["line"], height=max(1, round(METRICS.dpi_factor)))

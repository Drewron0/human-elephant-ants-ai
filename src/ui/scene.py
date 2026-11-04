"""Base screen: a plain page with a header bar and flat cards placed on it."""

import tkinter as tk
from collections.abc import Callable
from typing import TYPE_CHECKING

from PIL import ImageTk

from src.ui import art
from src.ui.theme import COLORS, MARGIN, METRICS, RADIUS, SPACE_L, font
from src.ui.widgets import PillButton

if TYPE_CHECKING:
    from src.ui.app import GameApp

RESIZE_DEBOUNCE_MS = 40
HEADER_HEIGHT = 76


class Panel:
    """A flat rounded card on the page holding ordinary Tk widgets in ``body``."""

    def __init__(self, view: "SceneView", fill: str = "card", padding: int = SPACE_L) -> None:
        self.view = view
        self.fill = COLORS[fill]
        self.padding = padding
        self.body = tk.Frame(view.stage, bg=self.fill)
        self._image_item = view.stage.create_image(0, 0, anchor="nw", state=tk.HIDDEN)
        self._window_item = view.stage.create_window(
            0, 0, anchor="nw", window=self.body, state=tk.HIDDEN
        )
        self._photo: ImageTk.PhotoImage | None = None
        self.geometry: tuple[int, int, int, int] = (0, 0, 0, 0)

    def inset(self) -> int:
        """Return the padding between the card edge and its content."""
        return METRICS.px(self.padding)

    def place(self, x: int, y: int, width: int, height: int) -> None:
        """Move and resize the card."""
        stage = self.view.stage
        inset = self.inset()
        if self.geometry[2:] != (width, height):
            image = art.panel_image(width, height, METRICS.px(RADIUS), self.fill, COLORS["line"])
            self._photo = ImageTk.PhotoImage(image, master=stage)
            stage.itemconfigure(self._image_item, image=self._photo)
        self.geometry = (x, y, width, height)
        stage.coords(self._image_item, x, y)
        stage.coords(self._window_item, x + inset, y + inset)
        stage.itemconfigure(self._window_item, width=width - inset * 2, height=height - inset * 2)
        stage.itemconfigure(self._image_item, state=tk.NORMAL)
        stage.itemconfigure(self._window_item, state=tk.NORMAL)

    def fit_height(self, content: tk.Misc | None = None) -> int:
        """Return the card height that exactly holds its content."""
        target = content or self.body
        target.update_idletasks()
        return target.winfo_reqheight() + self.inset() * 2


class SceneView(tk.Frame):
    """Base screen: calls ``layout`` on every size change."""

    def __init__(self, parent: tk.Misc, app: "GameApp") -> None:
        super().__init__(parent, bg=COLORS["page"])
        self.app = app
        self.stage = tk.Canvas(self, bg=COLORS["page"], highlightthickness=0, takefocus=0)
        self.stage.pack(fill=tk.BOTH, expand=True)
        self._resize_job: str | None = None
        self._laid_out = False
        self.stage.bind("<Configure>", self._on_stage_resize)

    def layout(self, width: int, height: int) -> None:
        """Position panels for the current size; subclasses override this."""

    def cleanup(self) -> None:
        """Cancel pending work before the view is destroyed."""
        if self._resize_job is not None:
            self.after_cancel(self._resize_job)
            self._resize_job = None

    def refresh_layout(self) -> None:
        """Lay the screen out again at the current size."""
        width, height = self.stage.winfo_width(), self.stage.winfo_height()
        if width > 1 and height > 1:
            self.layout(width, height)

    def _on_stage_resize(self, _event: tk.Event) -> None:
        if not self._laid_out:
            self._laid_out = True
            self.refresh_layout()
            return
        if self._resize_job is not None:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(RESIZE_DEBOUNCE_MS, self._apply_resize)

    def _apply_resize(self) -> None:
        self._resize_job = None
        self.refresh_layout()


class HeaderBar:
    """The navigation bar: back button, centered title and trailing actions."""

    def __init__(
        self,
        view: SceneView,
        title: str,
        subtitle: str = "",
        back_text: str = "Back",
        on_back: Callable[[], None] | None = None,
    ) -> None:
        self.view = view
        self.fill = COLORS["card"]
        self.frame = tk.Frame(view.stage, bg=self.fill)
        self._window_item = view.stage.create_window(0, 0, anchor="nw", window=self.frame)
        self.geometry: tuple[int, int, int, int] = (0, 0, 0, 0)
        self.frame.columnconfigure((0, 2), weight=1, uniform="sides")
        self.frame.rowconfigure(0, weight=1)
        pad = METRICS.px(MARGIN)
        self.back_button = PillButton(self.frame, back_text, command=on_back, icon="back")
        self.back_button.grid(row=0, column=0, sticky="w", padx=(pad, 0))
        text_box = tk.Frame(self.frame, bg=self.fill)
        text_box.grid(row=0, column=1, padx=pad)
        self.title_label = tk.Label(
            text_box, text=title, font=font("title"), bg=self.fill, fg=COLORS["ink"]
        )
        self.title_label.pack()
        self.subtitle_label = tk.Label(
            text_box, text=subtitle, font=font("caption"), bg=self.fill, fg=COLORS["ink_muted"]
        )
        if subtitle:
            self.subtitle_label.pack()
        self.actions = tk.Frame(self.frame, bg=self.fill)
        self.actions.grid(row=0, column=2, sticky="e", padx=(0, pad))
        tk.Frame(self.frame, bg=COLORS["line"], height=1).grid(
            row=1, column=0, columnspan=3, sticky="ew"
        )

    def height(self) -> int:
        """Return the bar height at the current density."""
        return max(METRICS.px(HEADER_HEIGHT), METRICS.target() + METRICS.px(SPACE_L))

    def place_top(self, width: int) -> int:
        """Span the top of the page and return the y position below it."""
        self.view.stage.coords(self._window_item, 0, 0)
        self.view.stage.itemconfigure(self._window_item, width=width, height=self.height())
        self.geometry = (0, 0, width, self.height())
        return self.height() + METRICS.px(MARGIN)

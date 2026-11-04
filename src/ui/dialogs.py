"""Modal alerts: Return confirms, Escape cancels, and only one is open at a time."""

import tkinter as tk
import weakref
from collections.abc import Callable

from src.ui.theme import COLORS, GUTTER, MARGIN, METRICS, SPACE_S, font
from src.ui.widgets import PillButton, Variant

DIALOG_WIDTH = 440
MESSAGE_WIDTH = 400


class Dialog(tk.Toplevel):
    """A centered modal alert."""

    active: "weakref.ReferenceType[Dialog] | None" = None

    def __init__(self, parent: tk.Misc, title: str, message: str = "") -> None:
        Dialog.dismiss_active()
        super().__init__(parent)
        Dialog.active = weakref.ref(self)
        self.title(title)
        self.configure(bg=COLORS["card"])
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self._default_action: Callable[[], None] | None = None
        self._cancel_action: Callable[[], None] = self.dismiss
        pad = METRICS.px(MARGIN)
        tk.Label(self, text=title, font=font("title"), bg=COLORS["card"], fg=COLORS["ink"]).pack(
            anchor="w", padx=pad, pady=(pad, METRICS.px(SPACE_S))
        )
        self.body = tk.Frame(self, bg=COLORS["card"])
        self.body.pack(fill=tk.BOTH, expand=True, padx=pad)
        if message:
            tk.Label(
                self.body,
                text=message,
                font=font("body"),
                bg=COLORS["card"],
                fg=COLORS["ink_muted"],
                justify=tk.LEFT,
                wraplength=METRICS.px(MESSAGE_WIDTH),
            ).pack(anchor="w")
        self.footer = tk.Frame(self, bg=COLORS["card"])
        self.footer.pack(fill=tk.X, padx=pad, pady=(METRICS.px(GUTTER), pad))
        self.protocol("WM_DELETE_WINDOW", lambda: self._cancel_action())
        self.bind("<Escape>", lambda _e: self._cancel_action())
        self.bind("<Return>", lambda _e: self._on_return())

    @classmethod
    def dismiss_active(cls) -> None:
        """Close the open dialog, if any."""
        dialog = cls.active() if cls.active else None
        if dialog is not None and dialog.winfo_exists():
            dialog.dismiss()
        cls.active = None

    def add_action(
        self,
        text: str,
        command: Callable[[], None] | None = None,
        variant: Variant = "secondary",
        default: bool = False,
        cancel: bool = False,
    ) -> PillButton:
        """Add a footer button; actions are listed left to right, primary last."""

        def run() -> None:
            self.dismiss()
            if command:
                command()

        button = PillButton(self.footer, text, command=run, variant=variant)
        gap = METRICS.px(SPACE_S) if self.footer.winfo_children()[:-1] else 0
        button.pack(side=tk.LEFT, padx=(gap, 0), expand=True, fill=tk.X)
        if default:
            self._default_action = run
        if cancel:
            self._cancel_action = run
        return button

    def present(self) -> None:
        """Center over the application window, then take keyboard and mouse focus."""
        self.update_idletasks()
        owner = self.master.winfo_toplevel()
        width = max(self.winfo_reqwidth(), METRICS.px(DIALOG_WIDTH))
        height = self.winfo_reqheight()
        x = owner.winfo_rootx() + (owner.winfo_width() - width) // 2
        y = owner.winfo_rooty() + (owner.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")
        self.grab_set()
        self.focus_force()

    def _on_return(self) -> None:
        if self._default_action:
            self._default_action()

    def dismiss(self) -> None:
        """Release focus and close."""
        self.grab_release()
        self.destroy()


def confirm(
    parent: tk.Misc,
    title: str,
    message: str,
    action_text: str,
    on_confirm: Callable[[], None],
    cancel_text: str = "Cancel",
    destructive: bool = True,
) -> Dialog:
    """Show a two-button confirmation dialog before taking an action."""
    dialog = Dialog(parent, title, message)
    dialog.add_action(cancel_text, cancel=True)
    dialog.add_action(
        action_text,
        on_confirm,
        variant="destructive" if destructive else "primary",
        default=True,
    )
    dialog.present()
    return dialog


def notify(parent: tk.Misc, title: str, message: str) -> Dialog:
    """Show a one-button informational alert."""
    dialog = Dialog(parent, title, message)
    dialog.add_action("OK", variant="primary", default=True, cancel=True)
    dialog.present()
    return dialog

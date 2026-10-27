import tkinter as tk
from typing import Optional
from ui_theme import THEME, FONT_NAME, ButtonPrimary, ButtonSecondary, ButtonDanger


class MainMenuView(tk.Frame):
    """
    Apple-styled Main Navigation Hub.
    Reorganized into clean functional categories to reduce visual clutter,
    with uniform button sizing across all navigation flows.
    """
    def __init__(self, parent, app):
        super().__init__(parent, bg=THEME['bg'])
        self.app = app
        self.active_category: Optional[str] = None
        self._build_ui()

    def _build_ui(self):
        for widget in self.winfo_children():
            widget.destroy()

        container = tk.Frame(self, bg=THEME['bg'])
        container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Title Block
        title_box = tk.Frame(container, bg=THEME['bg'])
        title_box.pack(pady=(0, 22))

        tk.Label(
            title_box,
            text="CHESS-SUT",
            font=(FONT_NAME, 26, "bold"),
            bg=THEME['bg'],
            fg=THEME['text']
        ).pack()

        tk.Label(
            title_box,
            text="Human Elephant Ant Tactical Board Game",
            font=(FONT_NAME, 11),
            bg=THEME['bg'],
            fg=THEME['text_muted']
        ).pack(pady=(4, 0))

        # Menu Container Card
        card = tk.Frame(
            container,
            bg=THEME['surface'],
            bd=1,
            relief=tk.SOLID,
            highlightbackground=THEME['border'],
            highlightthickness=1,
            padx=32,
            pady=24
        )
        card.pack()

        w = 32

        if self.active_category is None:
            # Root Category Selection
            tk.Label(
                card,
                text="SELECT CATEGORY",
                font=(FONT_NAME, 9, "bold"),
                bg=THEME['surface'],
                fg=THEME['text_muted']
            ).pack(pady=(0, 10))

            ButtonPrimary(
                card,
                text="Tactical Puzzle Mode",
                command=lambda: self.app.show_view('puzzle_select'),
                width=w
            ).pack(pady=4)

            ButtonSecondary(
                card,
                text="Match Modes (PvE / PvP)",
                command=lambda: self._show_category("matches"),
                width=w
            ).pack(pady=4)

            ButtonSecondary(
                card,
                text="Stage Studio & Tools",
                command=lambda: self._show_category("studio"),
                width=w
            ).pack(pady=4)

            ButtonSecondary(
                card,
                text="Records & Guide",
                command=lambda: self._show_category("records"),
                width=w
            ).pack(pady=4)

            ButtonDanger(
                card,
                text="Quit Application",
                command=self.app.destroy,
                width=w
            ).pack(pady=(14, 2))

        elif self.active_category == "matches":
            # Match Modes Submenu
            tk.Label(
                card,
                text="MATCH MODES",
                font=(FONT_NAME, 9, "bold"),
                bg=THEME['surface'],
                fg=THEME['text_muted']
            ).pack(pady=(0, 10))

            ButtonPrimary(
                card,
                text="Play vs AI (PvE)",
                command=lambda: self.app.open_config('PvE'),
                width=w
            ).pack(pady=4)

            ButtonSecondary(
                card,
                text="Play vs Player (PvP)",
                command=lambda: self.app.open_config('PvP'),
                width=w
            ).pack(pady=4)

            ButtonSecondary(
                card,
                text="Back to Main Menu",
                command=lambda: self._show_category(None),
                width=w
            ).pack(pady=(12, 2))

        elif self.active_category == "studio":
            # Stage Studio & Benchmark Submenu
            tk.Label(
                card,
                text="STAGE STUDIO & TOOLS",
                font=(FONT_NAME, 9, "bold"),
                bg=THEME['surface'],
                fg=THEME['text_muted']
            ).pack(pady=(0, 10))

            ButtonPrimary(
                card,
                text="Custom Stage Editor",
                command=lambda: self.app.show_view('stage_editor'),
                width=w
            ).pack(pady=4)

            ButtonSecondary(
                card,
                text="Simulation & Benchmark Lab",
                command=lambda: self.app.show_view('benchmark'),
                width=w
            ).pack(pady=4)

            ButtonSecondary(
                card,
                text="Back to Main Menu",
                command=lambda: self._show_category(None),
                width=w
            ).pack(pady=(12, 2))

        elif self.active_category == "records":
            # Records & Tutorial Submenu
            tk.Label(
                card,
                text="RECORDS & GUIDE",
                font=(FONT_NAME, 9, "bold"),
                bg=THEME['surface'],
                fg=THEME['text_muted']
            ).pack(pady=(0, 10))

            ButtonSecondary(
                card,
                text="Leaderboard & Records",
                command=lambda: self.app.show_view('leaderboard'),
                width=w
            ).pack(pady=4)

            ButtonSecondary(
                card,
                text="Load Saved Game",
                command=lambda: self.app.show_view('saves'),
                width=w
            ).pack(pady=4)

            ButtonSecondary(
                card,
                text="How to Play Guide",
                command=lambda: self.app.show_view('tutorial'),
                width=w
            ).pack(pady=4)

            ButtonSecondary(
                card,
                text="Back to Main Menu",
                command=lambda: self._show_category(None),
                width=w
            ).pack(pady=(12, 2))

    def _show_category(self, cat: Optional[str]):
        self.active_category = cat
        self._build_ui()

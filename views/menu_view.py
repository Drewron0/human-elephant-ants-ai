import tkinter as tk
from ui_theme import THEME, FONT_NAME, ButtonPrimary, ButtonSecondary, ButtonDanger


class MainMenuView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=THEME['bg'])
        self.app = app
        self._build_ui()

    def _build_ui(self):
        container = tk.Frame(self, bg=THEME['bg'])
        container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Title Card
        title_box = tk.Frame(container, bg=THEME['bg'])
        title_box.pack(pady=(0, 20))
        tk.Label(
            title_box,
            text="HUMAN ELEPHANT ANT",
            font=(FONT_NAME, 24, "bold"),
            bg=THEME['bg'],
            fg=THEME['text']
        ).pack()
        tk.Label(
            title_box,
            text="9x9 Turn-Based Tactical Board Game",
            font=(FONT_NAME, 11),
            bg=THEME['bg'],
            fg=THEME['text_muted']
        ).pack(pady=(4, 0))

        # Menu Card
        card = tk.Frame(
            container,
            bg=THEME['surface'],
            bd=1,
            relief=tk.SOLID,
            highlightbackground=THEME['border'],
            highlightthickness=1,
            padx=28,
            pady=22
        )
        card.pack()

        w = 28
        ButtonPrimary(card, text="Puzzle Mode (Chess-Sut Defender)", command=lambda: self.app.show_view('puzzle_select'), width=w).pack(pady=4)
        ButtonSecondary(card, text="Custom Stage Editor", command=lambda: self.app.show_view('stage_editor'), width=w).pack(pady=4)
        ButtonSecondary(card, text="Play vs AI (PvE)", command=lambda: self.app.open_config('PvE'), width=w).pack(pady=4)
        ButtonSecondary(card, text="Play vs Player (PvP)", command=lambda: self.app.open_config('PvP'), width=w).pack(pady=4)
        ButtonSecondary(card, text="Simulation & Benchmark Lab", command=lambda: self.app.show_view('benchmark'), width=w).pack(pady=4)
        ButtonSecondary(card, text="Load Saved Game", command=lambda: self.app.show_view('saves'), width=w).pack(pady=4)
        ButtonSecondary(card, text="Leaderboard and Records", command=lambda: self.app.show_view('leaderboard'), width=w).pack(pady=4)
        ButtonSecondary(card, text="How to Play", command=lambda: self.app.show_view('tutorial'), width=w).pack(pady=4)
        ButtonDanger(card, text="Quit Application", command=self.app.destroy, width=w).pack(pady=(10, 4))

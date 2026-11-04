import tkinter as tk
from typing import Optional
from ui_theme import THEME, FONT_NAME, ButtonPrimary, ButtonSecondary, CaptureLegend


class MainMenuView(tk.Frame):
    """Play destinations and capture rules, together on the first screen."""
    def __init__(self, parent, app):
        super().__init__(parent, bg=THEME['bg'])
        self.app = app
        self.active_category: Optional[str] = None
        self._build_ui()

    def _build_ui(self):
        for widget in self.winfo_children():
            widget.destroy()

        container = tk.Frame(self, bg=THEME['bg'])
        container.place(relx=0.5, rely=0.5, anchor=tk.CENTER, relwidth=0.88)
        container.columnconfigure(0, weight=1, uniform='menu')
        container.columnconfigure(1, weight=1, uniform='menu')

        title_box = tk.Frame(container, bg=THEME['bg'])
        title_box.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 24))
        tk.Label(title_box, text='Chess-Sut', font=(FONT_NAME, 28, 'bold'),
                 bg=THEME['bg'], fg=THEME['text']).pack(anchor='w')
        tk.Label(title_box, text='Human. Elephant. Ant. A game of tactical choices.',
                 font=(FONT_NAME, 12), bg=THEME['bg'], fg=THEME['text_muted']).pack(
                     anchor='w', pady=(8, 0))

        actions = tk.Frame(container, bg=THEME['surface'], padx=24, pady=24)
        actions.grid(row=1, column=0, sticky='nsew', padx=(0, 8))
        heading = 'Choose your game' if self.active_category is None else 'Records & guide'
        tk.Label(actions, text=heading, font=(FONT_NAME, 14, 'bold'),
                 bg=THEME['surface'], fg=THEME['text']).pack(anchor='w', pady=(0, 16))

        if self.active_category is None:
            ButtonPrimary(actions, text='Custom puzzles',
                          command=lambda: self.app.show_view('puzzle_select')).pack(
                              fill=tk.X, pady=(0, 8))
            destinations = [
                ('Play vs AI', lambda: self.app.open_config('PvE')),
                ('Create a custom stage', lambda: self.app.show_view('stage_editor')),
                ('Simulation & benchmark lab', lambda: self.app.show_view('benchmark')),
                ('Records & guide', lambda: self._show_category('records')),
            ]
        else:
            destinations = [
                ('Leaderboard & records', lambda: self.app.show_view('leaderboard')),
                ('How to play', lambda: self.app.show_view('tutorial')),
                ('Back to main menu', lambda: self._show_category(None)),
            ]
        for label, command in destinations:
            ButtonSecondary(actions, text=label, command=command).pack(fill=tk.X, pady=(0, 8))

        rules = tk.Frame(container, bg=THEME['surface'], padx=24, pady=24)
        rules.grid(row=1, column=1, sticky='nsew', padx=(8, 0))
        CaptureLegend(rules).pack(fill=tk.X)
        tk.Label(rules, text='Race to the star', font=(FONT_NAME, 14, 'bold'),
                 bg=THEME['surface'], fg=THEME['text']).pack(anchor='w', pady=(24, 8))
        goal = tk.Label(rules, text="Move any piece to your opponent's star corner to win.\n"
                                   'Each piece moves one square in any direction.',
                        font=(FONT_NAME, 11), bg=THEME['surface'], fg=THEME['text_muted'],
                        justify=tk.LEFT, anchor='w')
        goal.pack(fill=tk.X)
        rules.bind('<Configure>', lambda event: goal.config(wraplength=max(1, event.width - 48)))

        ButtonSecondary(container, text='Quit application', command=self.app.destroy).grid(
            row=2, column=0, sticky='w', pady=(16, 0))

    def _show_category(self, cat: Optional[str]):
        self.active_category = cat
        self._build_ui()

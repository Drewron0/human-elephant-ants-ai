import tkinter as tk
from tkinter import ttk

import storage
from competition import AI_MODEL, SEARCH_DEPTH, challenge_key
from puzzle_logic import generate_benchmark_corpus
from ui_theme import THEME, FONT_NAME, ButtonPrimary, ButtonSecondary, ButtonDanger, ThemedModal


class CompetitionView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=THEME['bg'])
        self.app = app
        self.challenges = generate_benchmark_corpus(3, seed=2026)
        self.var_challenge = tk.StringVar(value='Challenge 1')
        self.var_name = tk.StringVar(value=storage.get_last_username())
        self._build_ui()
        self._refresh_table()

    def _build_ui(self):
        content = tk.Frame(self, bg=THEME['bg'], padx=32, pady=24)
        content.pack(fill=tk.BOTH, expand=True)
        header = tk.Frame(content, bg=THEME['bg'])
        header.pack(fill=tk.X, pady=(0, 16))
        tk.Label(header, text='AI Competition', font=(FONT_NAME, 22, 'bold'),
                 bg=THEME['bg'], fg=THEME['text']).pack(side=tk.LEFT)
        ButtonSecondary(header, text='Main Menu', command=lambda: self.app.show_view('menu')).pack(side=tk.RIGHT)
        tk.Label(content, text='4 minutes total, including AI turns. One attempt per player per challenge.\n'
                 'Win: 1,000 - 10 × moves. Loss or timeout: 0. Equal scores use faster completion. No undo or reset.',
                 font=(FONT_NAME, 10), justify=tk.LEFT, bg=THEME['bg'], fg=THEME['text_muted']).pack(anchor='w', pady=(0, 16))
        controls = tk.Frame(content, bg=THEME['surface'], padx=16, pady=14)
        controls.pack(fill=tk.X, pady=(0, 16))
        tk.Label(controls, text='Challenge:', bg=THEME['surface'], fg=THEME['text']).pack(side=tk.LEFT)
        challenge = ttk.Combobox(controls, textvariable=self.var_challenge, state='readonly',
                                 values=['Challenge 1', 'Challenge 2', 'Challenge 3'], width=16)
        challenge.pack(side=tk.LEFT, padx=(8, 20))
        challenge.bind('<<ComboboxSelected>>', lambda event: self._refresh_table())
        tk.Label(controls, text='Player:', bg=THEME['surface'], fg=THEME['text']).pack(side=tk.LEFT)
        ttk.Combobox(controls, textvariable=self.var_name, values=storage.get_recent_profiles(), width=20).pack(side=tk.LEFT, padx=8)
        ButtonPrimary(controls, text='Start 4-minute Game', command=self._start_game).pack(side=tk.RIGHT)
        self.lbl_status = tk.Label(content, text='', bg=THEME['bg'], fg=THEME['text_muted'])
        self.lbl_status.pack(anchor='w', pady=(0, 10))
        columns = ('rank', 'player', 'score', 'moves', 'time', 'result')
        self.tree = ttk.Treeview(content, columns=columns, show='headings')
        for key, label in zip(columns, ('Rank', 'Player', 'Score', 'Moves', 'Time', 'Result')):
            self.tree.heading(key, text=label)
            self.tree.column(key, width=130, anchor=tk.CENTER)
        self.tree.pack(fill=tk.BOTH, expand=True)
        ButtonDanger(content, text='Clear This Round', command=self._clear_round).pack(anchor='e', pady=(14, 0))

    def _selected_scenario(self):
        return self.challenges[int(self.var_challenge.get().split()[-1]) - 1]

    def _refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        records = storage.get_competition_leaderboard(challenge_key(self._selected_scenario()))
        previous, rank = None, 0
        for index, record in enumerate(records, 1):
            order = (record['score'], record['elapsed_seconds'])
            if order != previous:
                rank = index
            previous = order
            self.tree.insert('', tk.END, values=(rank if record['solved'] else '-', record['username'],
                             record['score'], record['steps'], f"{record['elapsed_seconds']:.2f} s",
                             'Solved' if record['solved'] else record.get('reason') or 'Failed'))
        self.lbl_status.config(text='Same challenge and optimized depth-6 AI for every player. '
                               + ('No solved attempts yet.' if not any(r['solved'] for r in records) else 'Highest score wins.'))

    def _start_game(self):
        name = self.var_name.get().strip()
        if not name:
            self.lbl_status.config(text='Enter a player name before starting.')
            return
        scenario = self._selected_scenario()
        if any(record['username'].casefold() == name.casefold()
               for record in storage.get_competition_leaderboard(challenge_key(scenario))):
            self.lbl_status.config(text='This player has already played this challenge. Enter the next player or start a new round.')
            return
        storage.save_last_username(name)
        self.app.start_puzzle(dict(competition=True, p1_name=name, custom_scenario_obj=scenario,
                                  agent_model=AI_MODEL, search_depth=SEARCH_DEPTH))

    def _clear_round(self):
        key = challenge_key(self._selected_scenario())
        modal = ThemedModal(self, 'Start a New Round', min_width=380)
        tk.Label(modal.body, text='Delete scores for this challenge and let everyone play again?\nThis cannot be undone.',
                 bg=THEME['surface'], fg=THEME['text']).pack(pady=12)

        def confirm():
            storage.clear_competition_round(key)
            modal.dismiss()
            self._refresh_table()

        ButtonSecondary(modal.footer, text='Cancel', command=modal.dismiss).pack(side=tk.LEFT)
        ButtonDanger(modal.footer, text='Clear Round', command=confirm).pack(side=tk.RIGHT)

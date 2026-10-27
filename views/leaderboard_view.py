import tkinter as tk
from tkinter import ttk
from ui_theme import THEME, FONT_NAME, ButtonPrimary, ButtonSecondary, ButtonDanger, ThemedModal, SegmentedControl
import storage


class LeaderboardView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=THEME['bg'])
        self.app = app
        self.sort_by = "turns"
        self.difficulty_category = "all"
        self.current_tab = "pve"
        self._build_ui()

    def _build_ui(self):
        container = tk.Frame(self, bg=THEME['bg'])
        container.pack(fill=tk.BOTH, expand=True, padx=32, pady=18)

        # Header
        header = tk.Frame(container, bg=THEME['bg'])
        header.pack(fill=tk.X, pady=(0, 12))

        tk.Label(
            header,
            text="Game Leaderboard and Statistics",
            font=(FONT_NAME, 18, "bold"),
            bg=THEME['bg'],
            fg=THEME['text']
        ).pack(side=tk.LEFT)

        ButtonSecondary(header, text="Back to Hub", command=lambda: self.app.show_view('menu')).pack(side=tk.RIGHT)

        # Tabs: PvE vs PvP
        tabs_box = tk.Frame(container, bg=THEME['bg'])
        tabs_box.pack(fill=tk.X, pady=(0, 8))

        self.seg_tab = SegmentedControl(
            tabs_box,
            options=[("PvE Leaderboard", "pve"), ("PvP Player Records", "pvp")],
            default_val="pve",
            on_change=self._set_tab
        )
        self.seg_tab.pack(side=tk.LEFT)

        # PvE Filters Bar
        self.pve_toolbar = tk.Frame(
            container,
            bg=THEME['surface'],
            padx=10,
            pady=6,
            bd=1,
            relief=tk.SOLID,
            highlightbackground=THEME['border'],
            highlightthickness=1
        )
        self.pve_toolbar.pack(fill=tk.X, pady=(0, 8))

        tk.Label(self.pve_toolbar, text="Difficulty:", font=(FONT_NAME, 9, "bold"),
                 bg=THEME['surface'], fg=THEME['text_muted']).pack(side=tk.LEFT, padx=(0, 6))

        self.seg_diff = SegmentedControl(
            self.pve_toolbar,
            options=[("All", "all"), ("Easy", "easy"), ("Normal", "normal"), ("Hard", "hard")],
            default_val="all",
            on_change=self._set_difficulty_filter
        )
        self.seg_diff.pack(side=tk.LEFT, padx=(0, 16))

        tk.Label(self.pve_toolbar, text="Sort By:", font=(FONT_NAME, 9, "bold"),
                 bg=THEME['surface'], fg=THEME['text_muted']).pack(side=tk.LEFT, padx=(0, 6))

        self.seg_sort = SegmentedControl(
            self.pve_toolbar,
            options=[("Lowest Turns", "turns"), ("Fastest Time Left", "time"), ("Fewest Undos", "undos")],
            default_val="turns",
            on_change=self._set_sort
        )
        self.seg_sort.pack(side=tk.LEFT)

        # Table Container
        self.table_card = tk.Frame(
            container,
            bg=THEME['surface'],
            bd=1,
            relief=tk.SOLID,
            highlightbackground=THEME['border'],
            highlightthickness=1
        )
        self.table_card.pack(fill=tk.BOTH, expand=True)

        # Treeview with wide columns to NEVER cut off text
        self.tree = ttk.Treeview(self.table_card, show="headings", selectmode="browse")

        scroll_y = ttk.Scrollbar(self.table_card, orient=tk.VERTICAL, command=self.tree.yview)
        scroll_x = ttk.Scrollbar(self.table_card, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        # Actions Bar
        actions_bar = tk.Frame(container, bg=THEME['bg'])
        actions_bar.pack(fill=tk.X, pady=(10, 0))

        ButtonSecondary(actions_bar, text="Delete Selected Entry", command=self._delete_selected).pack(side=tk.LEFT, padx=(0, 6))
        self.btn_clear_cat = ButtonSecondary(actions_bar, text="Clear Current Category", command=self._clear_category)
        self.btn_clear_cat.pack(side=tk.LEFT, padx=(0, 6))
        ButtonDanger(actions_bar, text="Clear All Records", command=self._clear_all).pack(side=tk.LEFT)

        self._refresh_table()

    def _set_tab(self, tab: str):
        self.current_tab = tab
        if tab == "pve":
            self.pve_toolbar.pack(fill=tk.X, pady=(0, 8), before=self.table_card)
            self.btn_clear_cat.pack(side=tk.LEFT, padx=(0, 6))
        else:
            self.pve_toolbar.pack_forget()
            self.btn_clear_cat.pack_forget()
        self._refresh_table()

    def _set_difficulty_filter(self, diff: str):
        self.difficulty_category = diff
        self._refresh_table()

    def _set_sort(self, sort_by: str):
        self.sort_by = sort_by
        self._refresh_table()

    def _refresh_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        if self.current_tab == "pve":
            columns = ("rank", "player", "difficulty", "turns", "time_left", "undos", "date")
            self.tree["columns"] = columns

            self.tree.heading("rank", text="Rank")
            self.tree.heading("player", text="Player Name")
            self.tree.heading("difficulty", text="Difficulty")
            self.tree.heading("turns", text="Turns")
            self.tree.heading("time_left", text="Time Remaining")
            self.tree.heading("undos", text="Undos")
            self.tree.heading("date", text="Date Achieved")

            # Generous column widths so text is never truncated
            self.tree.column("rank", width=60, minwidth=50, anchor=tk.CENTER)
            self.tree.column("player", width=200, minwidth=140, anchor=tk.W)
            self.tree.column("difficulty", width=110, minwidth=90, anchor=tk.CENTER)
            self.tree.column("turns", width=80, minwidth=70, anchor=tk.CENTER)
            self.tree.column("time_left", width=130, minwidth=100, anchor=tk.CENTER)
            self.tree.column("undos", width=80, minwidth=70, anchor=tk.CENTER)
            self.tree.column("date", width=150, minwidth=120, anchor=tk.CENTER)

            records = storage.get_pve_leaderboard(sort_by=self.sort_by, difficulty=self.difficulty_category)
            for i, r in enumerate(records):
                t_val = r.get('time_left', 0)
                t_str = f"{t_val // 60}:{t_val % 60:02d}" if t_val >= 0 else "Unlimited"
                uname = r['username']
                self.tree.insert("", tk.END, iid=r['id'], values=(
                    i + 1, uname, r.get('difficulty', 'Normal'),
                    r['turns'], t_str, r['undos'], r['timestamp']
                ))

        else:
            columns = ("player", "wins", "losses", "undos", "rate", "last_played")
            self.tree["columns"] = columns

            self.tree.heading("player", text="Player Profile")
            self.tree.heading("wins", text="Wins")
            self.tree.heading("losses", text="Losses")
            self.tree.heading("undos", text="Total Undos")
            self.tree.heading("rate", text="Win Rate")
            self.tree.heading("last_played", text="Last Match")

            self.tree.column("player", width=220, minwidth=160, anchor=tk.W)
            self.tree.column("wins", width=90, minwidth=70, anchor=tk.CENTER)
            self.tree.column("losses", width=90, minwidth=70, anchor=tk.CENTER)
            self.tree.column("undos", width=100, minwidth=80, anchor=tk.CENTER)
            self.tree.column("rate", width=100, minwidth=80, anchor=tk.CENTER)
            self.tree.column("last_played", width=160, minwidth=120, anchor=tk.CENTER)

            pvp_data = storage.get_pvp_stats()
            for uname, stats in pvp_data.items():
                w = stats.get('wins', 0)
                l = stats.get('losses', 0)
                u = stats.get('undos', 0)
                total = w + l
                rate_str = f"{(w / total * 100):.1f}%" if total > 0 else "N/A"
                self.tree.insert("", tk.END, iid=uname, values=(
                    uname, w, l, u, rate_str, stats.get('last_played', '')
                ))

    def _delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            return

        sel_id = selected[0]
        if self.current_tab == "pve":
            storage.delete_pve_score(sel_id)
        else:
            storage.delete_pvp_player(sel_id)
        self._refresh_table()

    def _clear_category(self):
        if self.current_tab != "pve":
            return
        cat_name = self.difficulty_category.capitalize() if self.difficulty_category != "all" else "All Difficulties"
        modal = ThemedModal(self, "Clear Category Confirmation", min_width=380)
        tk.Label(
            modal.body,
            text=f"Clear leaderboard records for category '{cat_name}'? This cannot be undone.",
            font=(FONT_NAME, 10),
            bg=THEME['surface'],
            fg=THEME['text'],
            wraplength=340
        ).pack(pady=10)

        def confirm():
            modal.dismiss()
            storage.clear_pve_leaderboard(self.difficulty_category)
            self._refresh_table()

        ButtonSecondary(modal.footer, text="Cancel", command=modal.dismiss).pack(side=tk.LEFT)
        ButtonDanger(modal.footer, text="Clear Category", command=confirm).pack(side=tk.RIGHT)

    def _clear_all(self):
        modal = ThemedModal(self, "Clear All Records Confirmation", min_width=380)
        tk.Label(
            modal.body,
            text=f"Clear all {'PvE Leaderboard' if self.current_tab == 'pve' else 'PvP'} records? This cannot be undone.",
            font=(FONT_NAME, 10),
            bg=THEME['surface'],
            fg=THEME['text'],
            wraplength=340
        ).pack(pady=10)

        def confirm():
            modal.dismiss()
            if self.current_tab == "pve":
                storage.clear_pve_leaderboard("all")
            else:
                storage.clear_pvp_stats()
            self._refresh_table()

        ButtonSecondary(modal.footer, text="Cancel", command=modal.dismiss).pack(side=tk.LEFT)
        ButtonDanger(modal.footer, text="Clear All", command=confirm).pack(side=tk.RIGHT)

import tkinter as tk
from tkinter import ttk
import threading
import csv
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

from ui_theme import THEME, FONT_NAME, ButtonPrimary, ButtonSecondary, ButtonDanger, ThemedModal
from puzzle_logic import run_simulation_benchmark


class BenchmarkView(tk.Frame):
    """
    Simulation & Benchmark Lab View.
    Implements the comparative evaluation framework described in Chapter 2.2 and Table 3.
    """
    def __init__(self, parent, app):
        super().__init__(parent, bg=THEME['bg'])
        self.app = app
        self.results_data: List[Dict[str, Any]] = []
        self.is_running = False

        self._build_ui()

    def _build_ui(self):
        container = tk.Frame(self, bg=THEME['bg'])
        container.pack(fill=tk.BOTH, expand=True, padx=24, pady=16)

        # Header Card
        header = tk.Frame(container, bg=THEME['bg'])
        header.pack(fill=tk.X, pady=(0, 12))

        tk.Label(
            header,
            text="AI EVALUATION & BENCHMARK LAB",
            font=(FONT_NAME, 18, "bold"),
            bg=THEME['bg'],
            fg=THEME['text']
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Simulated Match Benchmark Framework (Russell & Norvig, Table 3 Comparative Analysis)",
            font=(FONT_NAME, 10),
            bg=THEME['bg'],
            fg=THEME['text_muted']
        ).pack(anchor="w", pady=(2, 0))

        # Controls Card
        ctrl_card = tk.Frame(
            container,
            bg=THEME['surface'],
            bd=1,
            relief=tk.SOLID,
            highlightbackground=THEME['border'],
            highlightthickness=1,
            padx=16,
            pady=12
        )
        ctrl_card.pack(fill=tk.X, pady=(0, 12))

        lbl_fnt = (FONT_NAME, 9, "bold")
        ent_fnt = (FONT_NAME, 9)

        # Row 1: Agent & Scripted Player
        row1 = tk.Frame(ctrl_card, bg=THEME['surface'])
        row1.pack(fill=tk.X, pady=4)

        tk.Label(row1, text="Defender Model:", font=lbl_fnt, bg=THEME['surface'], fg=THEME['text']).pack(side=tk.LEFT, padx=(0, 6))
        self.var_agent = tk.StringVar(value="Proposed: Optimized Agent (Alpha-Beta d=6)")
        cb_agent = ttk.Combobox(
            row1,
            textvariable=self.var_agent,
            values=[
                "Proposed: Optimized Agent (Alpha-Beta d=6)",
                "Proposed: Optimized Agent (Alpha-Beta d=3)",
                "Baseline 2: Vanilla Minimax (d=3, Static, No Pruning)",
                "Baseline 1: Random Move Agent"
            ],
            state="readonly",
            width=38,
            font=ent_fnt
        )
        cb_agent.pack(side=tk.LEFT, padx=(0, 18))

        tk.Label(row1, text="Scripted Opponent:", font=lbl_fnt, bg=THEME['surface'], fg=THEME['text']).pack(side=tk.LEFT, padx=(0, 6))
        self.var_scripted = tk.StringVar(value="Shortest-Path Player")
        cb_scripted = ttk.Combobox(
            row1,
            textvariable=self.var_scripted,
            values=[
                "Shortest-Path Player",
                "Sub-Optimal Player (25% Random Deviations)",
                "Random Move Player"
            ],
            state="readonly",
            width=32,
            font=ent_fnt
        )
        cb_scripted.pack(side=tk.LEFT)

        # Row 2: Games Count & Board Size & Actions
        row2 = tk.Frame(ctrl_card, bg=THEME['surface'])
        row2.pack(fill=tk.X, pady=(8, 4))

        tk.Label(row2, text="Simulated Games (G):", font=lbl_fnt, bg=THEME['surface'], fg=THEME['text']).pack(side=tk.LEFT, padx=(0, 6))
        self.var_games = tk.StringVar(value="25 Games")
        cb_games = ttk.Combobox(
            row2,
            textvariable=self.var_games,
            values=["10 Games", "25 Games", "50 Games", "100 Games"],
            state="readonly",
            width=12,
            font=ent_fnt
        )
        cb_games.pack(side=tk.LEFT, padx=(0, 18))

        tk.Label(row2, text="Board Size:", font=lbl_fnt, bg=THEME['surface'], fg=THEME['text']).pack(side=tk.LEFT, padx=(0, 6))
        self.var_size = tk.StringVar(value="9x9 Board")
        cb_size = ttk.Combobox(
            row2,
            textvariable=self.var_size,
            values=["9x9 Board", "6x6 Board"],
            state="readonly",
            width=12,
            font=ent_fnt
        )
        cb_size.pack(side=tk.LEFT, padx=(0, 20))

        self.btn_run = ButtonPrimary(row2, text="Run Single Simulation", command=self._start_single_benchmark)
        self.btn_run.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_run_all = ButtonSecondary(row2, text="Run Full Table 3 Benchmark", command=self._start_full_benchmark)
        self.btn_run_all.pack(side=tk.LEFT)

        # Progress bar & status
        prog_frame = tk.Frame(ctrl_card, bg=THEME['surface'])
        prog_frame.pack(fill=tk.X, pady=(10, 2))

        self.progress_bar = ttk.Progressbar(prog_frame, mode='determinate')
        self.progress_bar.pack(fill=tk.X)

        self.lbl_status = tk.Label(
            prog_frame,
            text="Ready to run simulated evaluation matches.",
            font=(FONT_NAME, 8, "italic"),
            bg=THEME['surface'],
            fg=THEME['text_muted']
        )
        self.lbl_status.pack(anchor="w", pady=(2, 0))

        # Results Table Card
        table_card = tk.Frame(
            container,
            bg=THEME['surface'],
            bd=1,
            relief=tk.SOLID,
            highlightbackground=THEME['border'],
            highlightthickness=1,
            padx=12,
            pady=10
        )
        table_card.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            table_card,
            text="TABLE 3: COMPARATIVE SEARCH & STRATEGIC METRICS",
            font=(FONT_NAME, 9, "bold"),
            bg=THEME['surface'],
            fg=THEME['text']
        ).pack(anchor="w", pady=(0, 6))

        columns = ("model", "opponent", "games", "latency", "pruning", "delay", "r_neut")
        self.tree = ttk.Treeview(table_card, columns=columns, show='headings', height=10)

        self.tree.heading("model", text="Defender Model")
        self.tree.heading("opponent", text="Scripted Opponent")
        self.tree.heading("games", text="Games (G)")
        self.tree.heading("latency", text="Turn Latency (Tturn)")
        self.tree.heading("pruning", text="Pruning Efficiency (prune)")
        self.tree.heading("delay", text="Delay Margin (moves)")
        self.tree.heading("r_neut", text="Neutralization Rate (Rneut)")

        self.tree.column("model", width=220, anchor="w")
        self.tree.column("opponent", width=160, anchor="w")
        self.tree.column("games", width=80, anchor="center")
        self.tree.column("latency", width=130, anchor="center")
        self.tree.column("pruning", width=140, anchor="center")
        self.tree.column("delay", width=110, anchor="center")
        self.tree.column("r_neut", width=140, anchor="center")

        tree_scroll = ttk.Scrollbar(table_card, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Footer Actions
        footer = tk.Frame(container, bg=THEME['bg'])
        footer.pack(fill=tk.X, pady=(10, 0))

        ButtonSecondary(footer, text="Back to Main Menu", command=lambda: self.app.show_view('menu')).pack(side=tk.LEFT)
        ButtonSecondary(footer, text="Export Table to CSV", command=self._export_csv).pack(side=tk.LEFT, padx=8)
        ButtonSecondary(footer, text="Clear Results", command=self._clear_table).pack(side=tk.LEFT)

    def _map_agent_key(self, val: str) -> Tuple[str, int]:
        if "Alpha-Beta d=6" in val:
            return 'proposed_d6', 6
        elif "Alpha-Beta d=3" in val:
            return 'proposed_d3', 3
        elif "Baseline 2" in val or "Vanilla" in val:
            return 'baseline_2_vanilla', 3
        else:
            return 'baseline_1_random', 1

    def _map_scripted_key(self, val: str) -> str:
        if "Sub-Optimal" in val:
            return 'sub_optimal'
        elif "Random" in val:
            return 'random'
        else:
            return 'shortest_path'

    def _parse_games_count(self) -> int:
        val = self.var_games.get()
        try:
            return int(val.split()[0])
        except Exception:
            return 25

    def _parse_board_size(self) -> int:
        return 6 if "6x6" in self.var_size.get() else 9

    def _start_single_benchmark(self):
        if self.is_running:
            return

        agent_model, depth = self._map_agent_key(self.var_agent.get())
        scripted_key = self._map_scripted_key(self.var_scripted.get())
        num_games = self._parse_games_count()
        board_size = self._parse_board_size()

        self.is_running = True
        self.btn_run.config(state=tk.DISABLED)
        self.btn_run_all.config(state=tk.DISABLED)
        self.progress_bar['value'] = 0
        self.progress_bar['maximum'] = num_games

        def worker():
            def prog_cb(cur, tot):
                self.after(0, lambda: self._update_progress(cur, tot))

            res = run_simulation_benchmark(
                agent_model=agent_model,
                scripted_player_type=scripted_key,
                num_games=num_games,
                depth=depth,
                board_size=board_size,
                progress_callback=prog_cb
            )

            self.after(0, lambda: self._on_benchmark_complete([res]))

        threading.Thread(target=worker, daemon=True).start()

    def _start_full_benchmark(self):
        if self.is_running:
            return

        combos = [
            ('proposed_d6', 6, "Proposed: Optimized Agent (d=6)", 'shortest_path'),
            ('proposed_d6', 6, "Proposed: Optimized Agent (d=6)", 'sub_optimal'),
            ('proposed_d6', 6, "Proposed: Optimized Agent (d=6)", 'random'),
            ('baseline_2_vanilla', 3, "Baseline 2: Vanilla Minimax (d=3)", 'shortest_path'),
            ('baseline_2_vanilla', 3, "Baseline 2: Vanilla Minimax (d=3)", 'sub_optimal'),
            ('baseline_2_vanilla', 3, "Baseline 2: Vanilla Minimax (d=3)", 'random'),
            ('baseline_1_random', 1, "Baseline 1: Random Move Agent", 'shortest_path'),
            ('baseline_1_random', 1, "Baseline 1: Random Move Agent", 'sub_optimal'),
            ('baseline_1_random', 1, "Baseline 1: Random Move Agent", 'random')
        ]

        board_size = self._parse_board_size()
        games_per_combo = 10  # Fast batch run

        self.is_running = True
        self.btn_run.config(state=tk.DISABLED)
        self.btn_run_all.config(state=tk.DISABLED)
        total_steps = len(combos) * games_per_combo
        self.progress_bar['value'] = 0
        self.progress_bar['maximum'] = total_steps

        def worker():
            completed_overall = 0
            batch_results = []

            for agent_k, d, display_agent, script_k in combos:
                def prog_cb(cur, tot):
                    nonlocal completed_overall
                    step = completed_overall + cur
                    self.after(0, lambda s=step, t=total_steps, da=display_agent, sk=script_k: (
                        self.progress_bar.config(value=s),
                        self.lbl_status.config(text=f"Benchmarking {da} vs {sk}... ({s}/{t} matches)")
                    ))

                res = run_simulation_benchmark(
                    agent_model=agent_k,
                    scripted_player_type=script_k,
                    num_games=games_per_combo,
                    depth=d,
                    board_size=board_size,
                    progress_callback=prog_cb
                )
                completed_overall += games_per_combo
                batch_results.append(res)

            self.after(0, lambda: self._on_benchmark_complete(batch_results))

        threading.Thread(target=worker, daemon=True).start()

    def _update_progress(self, current: int, total: int):
        self.progress_bar['value'] = current
        self.lbl_status.config(text=f"Simulating match {current} of {total}...")

    def _on_benchmark_complete(self, results: List[Dict[str, Any]]):
        self.is_running = False
        self.btn_run.config(state=tk.NORMAL)
        self.btn_run_all.config(state=tk.NORMAL)
        self.progress_bar['value'] = self.progress_bar['maximum']
        self.lbl_status.config(text="Benchmark simulation run complete.")

        for res in results:
            self.results_data.append(res)
            model_lbl = res['agent_model']
            if 'proposed_d6' in model_lbl:
                name = "Proposed (Alpha-Beta d=6)"
            elif 'proposed_d3' in model_lbl:
                name = "Proposed (Alpha-Beta d=3)"
            elif 'baseline_2' in model_lbl:
                name = "Baseline 2 (Vanilla d=3)"
            else:
                name = "Baseline 1 (Random)"

            opp_lbl = res['scripted_player'].replace('_', ' ').title()

            self.tree.insert(
                "",
                tk.END,
                values=(
                    name,
                    opp_lbl,
                    str(res['total_games']),
                    f"{res['avg_latency']:.3f} s",
                    f"{res['avg_pruning_efficiency']:.1f} %",
                    f"+{res['delay_margin']:.1f} moves",
                    f"{res['neutralization_rate']:.1f} %"
                )
            )

    def _clear_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.results_data.clear()
        self.lbl_status.config(text="Results cleared.")

    def _export_csv(self):
        if not self.results_data:
            modal = ThemedModal(self, "Export Table", min_width=320)
            tk.Label(modal.body, text="No benchmark results to export.", bg=THEME['surface'], fg=THEME['text']).pack(pady=10)
            ButtonPrimary(modal.footer, text="Close", command=modal.dismiss).pack(side=tk.RIGHT)
            return

        filename = f"benchmark_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Defender Model", "Scripted Opponent", "Games (G)",
                    "Turn Latency (s)", "Pruning Efficiency (%)",
                    "Delay Margin (moves)", "Neutralization Rate (%)"
                ])
                for r in self.results_data:
                    writer.writerow([
                        r['agent_model'],
                        r['scripted_player'],
                        r['total_games'],
                        f"{r['avg_latency']:.4f}",
                        f"{r['avg_pruning_efficiency']:.2f}",
                        f"{r['delay_margin']:.2f}",
                        f"{r['neutralization_rate']:.2f}"
                    ])

            modal = ThemedModal(self, "Export Successful", min_width=360)
            tk.Label(
                modal.body,
                text=f"Benchmark results successfully exported to:\n{filename}",
                font=(FONT_NAME, 9),
                bg=THEME['surface'],
                fg=THEME['text'],
                justify="center"
            ).pack(pady=10)
            ButtonPrimary(modal.footer, text="OK", command=modal.dismiss).pack(side=tk.RIGHT)
        except Exception as e:
            modal = ThemedModal(self, "Export Error", min_width=360)
            tk.Label(modal.body, text=f"Failed to export: {e}", bg=THEME['surface'], fg='#E53935').pack(pady=10)
            ButtonPrimary(modal.footer, text="Close", command=modal.dismiss).pack(side=tk.RIGHT)

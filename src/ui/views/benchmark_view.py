"""Simulation lab: compares defenders and exports the results."""

import csv
import threading
import tkinter as tk
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any

from config import settings
from src.ai.agents import BENCHMARK_AGENTS, AgentSpec
from src.benchmark.players import BENCHMARK_PLAYERS, PLAYER_LABELS
from src.benchmark.runner import generate_benchmark_corpus, run_simulation_benchmark
from src.ui.background import BackgroundTask
from src.ui.dialogs import notify
from src.ui.fields import Field
from src.ui.scene import HeaderBar, Panel, SceneView
from src.ui.table import DataTable, TableColumn
from src.ui.theme import COLORS, GUTTER, METRICS, SPACE_M, SPACE_S, font
from src.ui.widgets import PillButton, ProgressBar, WrapLabel, field_label

if TYPE_CHECKING:
    from src.ui.app import GameApp

COLUMNS: tuple[TableColumn, ...] = (
    TableColumn("model", "Defender", 210, "w"),
    TableColumn("opponent", "Opponent", 160, "w"),
    TableColumn("games", "Games", 70, "center"),
    TableColumn("latency", "Avg latency", 100, "center"),
    TableColumn("max_latency", "Max latency", 100, "center"),
    TableColumn("pruning", "Pruning", 80, "center"),
    TableColumn("delay", "Delay margin", 120, "center"),
    TableColumn("r_neut", "Neutralized", 100, "center"),
    TableColumn("depth", "Depth", 130, "center"),
    TableColumn("timeouts", "Timeouts", 80, "center"),
)
EMPTY_TEXT = "Run a simulation to see results here."
READY_TEXT = "Ready. 1000 games with the Alpha-Beta agent can take hours, so start small."
Combination = tuple[AgentSpec, str]


class BenchmarkView(SceneView):
    """Runs simulations on a worker; leaving the screen cancels them."""

    def __init__(self, parent: tk.Misc, app: "GameApp") -> None:
        super().__init__(parent, app)
        self.results_data: list[dict[str, Any]] = []
        self._task: BackgroundTask | None = None
        self.header = HeaderBar(
            self, "Simulation Lab", "Compare defenders", "Menu", lambda: self.app.show_view("menu")
        )
        self.btn_export = PillButton(
            self.header.actions, "Export CSV", self._export_csv, icon="export"
        )
        self.btn_export.pack(side=tk.LEFT, padx=(0, METRICS.px(SPACE_S)))
        self.btn_clear = PillButton(self.header.actions, "Clear", self._clear_table, icon="trash")
        self.btn_clear.pack(side=tk.LEFT)
        self.controls = Panel(self)
        self._build_controls(self.controls.body)
        self.table_panel = Panel(self)
        self.table = DataTable(self.table_panel.body, COLUMNS, EMPTY_TEXT)
        self.table.pack(fill=tk.BOTH, expand=True)
        self._sync_actions()

    def _select(self, parent: tk.Misc, column: int, label: str, values: list[str]) -> tk.StringVar:
        box = tk.Frame(parent, bg=COLORS["card"])
        gap = METRICS.px(SPACE_S)
        box.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else gap, 0))
        field_label(box, label).pack(fill=tk.X, pady=(0, gap))
        variable = tk.StringVar(value=values[0])
        Field(box, variable, values, editable=False).pack(fill=tk.X)
        return variable

    def _build_controls(self, body: tk.Frame) -> None:
        row = tk.Frame(body, bg=COLORS["card"])
        row.pack(fill=tk.X)
        row.columnconfigure(0, weight=4, uniform="fields")
        row.columnconfigure(1, weight=4, uniform="fields")
        row.columnconfigure((2, 3), weight=2, uniform="fields")
        self.var_agent = self._select(row, 0, "Defender", [a.label for a in BENCHMARK_AGENTS])
        self.var_scripted = self._select(
            row, 1, "Scripted player", [PLAYER_LABELS[p] for p in BENCHMARK_PLAYERS]
        )
        games = [str(g) for g in reversed(settings.BENCHMARK_GAME_CHOICES)]
        self.var_games = self._select(row, 2, "Games", games)
        self.var_size = self._select(
            row, 3, "Board", [f"{s}x{s}" for s in settings.BENCHMARK_BOARD_CHOICES]
        )

        buttons = tk.Frame(body, bg=COLORS["card"])
        buttons.pack(fill=tk.X, pady=(METRICS.px(SPACE_M), 0))
        gap = (0, METRICS.px(SPACE_S))
        self.btn_run = PillButton(
            buttons, "Run Simulation", self._start_single_benchmark, variant="primary", icon="play"
        )
        self.btn_run.pack(side=tk.LEFT, padx=gap)
        self.btn_run_all = PillButton(
            buttons, "Run Full Table", self._start_full_benchmark, icon="chart"
        )
        self.btn_run_all.pack(side=tk.LEFT, padx=gap)
        self.btn_cancel = PillButton(buttons, "Cancel", self._cancel_benchmark, icon="stop")
        self.btn_cancel.pack(side=tk.LEFT)

        self.progress_bar = ProgressBar(body)
        self.progress_bar.pack(fill=tk.X, pady=(METRICS.px(SPACE_M), METRICS.px(SPACE_S)))
        self.lbl_status = WrapLabel(body, READY_TEXT, font=font("caption"), fg=COLORS["ink_muted"])
        self.lbl_status.pack(fill=tk.X)

    def layout(self, width: int, height: int) -> None:
        """Fit the controls to their content and give the table the rest."""
        top = self.header.place_top(width)
        margin = top - self.header.height()
        gutter = METRICS.px(GUTTER)
        controls_h = self.controls.fit_height()
        self.controls.place(margin, top, width - margin * 2, controls_h)
        table_top = top + controls_h + gutter
        self.table_panel.place(margin, table_top, width - margin * 2, height - table_top - margin)

    def _selected_agent(self) -> AgentSpec:
        return next(a for a in BENCHMARK_AGENTS if a.label == self.var_agent.get())

    def _selected_player(self) -> str:
        return next(p for p in BENCHMARK_PLAYERS if PLAYER_LABELS[p] == self.var_scripted.get())

    def _start_single_benchmark(self) -> None:
        self._start([(self._selected_agent(), self._selected_player())])

    def _start_full_benchmark(self) -> None:
        self._start([(agent, player) for agent in BENCHMARK_AGENTS for player in BENCHMARK_PLAYERS])

    def _start(self, combinations: list[Combination]) -> None:
        if self._task is not None:
            return
        games = int(self.var_games.get())
        board_size = int(self.var_size.get().split("x")[0])
        self.progress_bar.set(0, games * len(combinations))
        self.lbl_status.configure(text="Generating test positions...", fg=COLORS["ink_muted"])

        def work(cancel: threading.Event, report: Callable[[Any], None]) -> list[dict[str, Any]]:
            corpus = generate_benchmark_corpus(games, board_size)
            results = []
            for index, (agent, player) in enumerate(combinations):
                offset = index * games

                def progress(
                    current: int,
                    _total: int,
                    base: int = offset,
                    label: str = agent.label,
                    opponent: str = PLAYER_LABELS[player],
                ) -> None:
                    report((base + current, label, opponent))

                results.append(
                    run_simulation_benchmark(
                        agent.model,
                        player,
                        games,
                        agent.depth,
                        board_size,
                        progress,
                        corpus,
                        cancel_event=cancel,
                    )
                )
            return results

        self._task = BackgroundTask(
            self, work, self._on_complete, self._on_failed, self._on_progress
        )
        self._sync_actions()
        self._task.start()

    def _on_progress(self, update: tuple[int, str, str]) -> None:
        done, agent, player = update
        self.progress_bar.set(done)
        total = int(self.progress_bar.maximum)
        self.lbl_status.configure(text=f"{agent} vs {player}: game {done} of {total}")

    def _on_failed(self, message: str) -> None:
        self._task = None
        self.lbl_status.configure(text=f"Benchmark failed: {message}", fg=COLORS["danger"])
        self._sync_actions()

    def _cancel_benchmark(self) -> None:
        if self._task is not None:
            self._task.cancel()
            self._task = None
        self.progress_bar.set(0)
        self.lbl_status.configure(text="Benchmark cancelled.", fg=COLORS["ink_muted"])
        self._sync_actions()

    def _on_complete(self, results: list[dict[str, Any]]) -> None:
        self._task = None
        self.progress_bar.set(self.progress_bar.maximum)
        self.lbl_status.configure(text="Benchmark complete.", fg=COLORS["ink_muted"])
        self.results_data.extend(results)
        labels = {agent.model: agent.label for agent in BENCHMARK_AGENTS}
        rows: list[tuple[str, tuple[object, ...]]] = []
        for index, result in enumerate(self.results_data):
            delay = result["delay_margin"]
            depth = result["requested_depth"]
            rows.append(
                (
                    str(index),
                    (
                        labels[result["agent_model"]],
                        PLAYER_LABELS[result["scripted_player"]],
                        result["total_games"],
                        f"{result['avg_latency']:.3f} s",
                        f"{result['max_latency']:.3f} s",
                        f"{result['avg_pruning_efficiency']:.1f}%",
                        "No wins" if delay is None else f"{delay:+.1f} moves",
                        f"{result['neutralization_rate']:.1f}%",
                        (
                            (
                                f"{result['avg_completed_depth']:.1f} / {depth} "
                                f"({result['full_depth_rate']:.0f}%)"
                            )
                            if depth > 1
                            else "No search"
                        ),
                        result["timeout_count"],
                    ),
                )
            )
        self.table.set_rows(rows)
        self._sync_actions()

    def _sync_actions(self) -> None:
        running = self._task is not None
        self.btn_run.set_enabled(not running)
        self.btn_run_all.set_enabled(not running)
        self.btn_cancel.set_enabled(running)
        self.btn_export.set_enabled(bool(self.results_data))
        self.btn_clear.set_enabled(bool(self.results_data))

    def _clear_table(self) -> None:
        self.table.set_rows([])
        self.results_data.clear()
        self.lbl_status.configure(text="Results cleared.", fg=COLORS["ink_muted"])
        self._sync_actions()

    def _export_csv(self) -> None:
        if not self.results_data:
            return
        settings.BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
        path = settings.BENCHMARK_DIR / f"lab_{datetime.now():%Y%m%d_%H%M%S}.csv"
        try:
            with path.open("w", newline="", encoding="utf-8") as output:
                writer = csv.DictWriter(output, fieldnames=list(self.results_data[0]))
                writer.writeheader()
                writer.writerows(self.results_data)
        except OSError as error:
            notify(self, "Export Failed", str(error))
            return
        notify(self, "Export Complete", f"Results saved to:\n{path}")

    def cleanup(self) -> None:
        """Cancel any running simulation."""
        super().cleanup()
        if self._task is not None:
            self._task.cancel()
            self._task = None

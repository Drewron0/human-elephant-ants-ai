"""Puzzle play against the defender, with counted undo and optional search metrics."""

import logging
import time
import tkinter as tk
from typing import TYPE_CHECKING, Any

from config import settings
from src import storage
from src.ai.agents import EXACT_DEFENDER, OPTIMIZED_D6
from src.ai.exact_defender import get_exact_defender_reply
from src.ai.search import SearchTelemetry, get_defender_move
from src.core.game_logic import Coord, MoveTuple, coord_label
from src.puzzle.scenario import (
    STATUS_DELAYED,
    STATUS_NEUTRALIZED,
    STATUS_SOLVED,
    PuzzleScenario,
    PuzzleSession,
)
from src.puzzle.solver import make_puzzle_move
from src.ui.background import BackgroundTask
from src.ui.dialogs import Dialog
from src.ui.play_view import PlayerCard, PlayView, stat_line
from src.ui.scene import HeaderBar
from src.ui.theme import COLORS, GUTTER, METRICS, SPACE_L, SPACE_S, font
from src.ui.widgets import PillButton, WrapLabel, section_title

if TYPE_CHECKING:
    from src.ui.app import GameApp

logger = logging.getLogger(__name__)


class PuzzleGameView(PlayView):
    """Runs one stage; the defender always thinks on a worker thread."""

    def __init__(self, parent: tk.Misc, app: "GameApp", config: dict[str, Any]) -> None:
        scenario: PuzzleScenario | None = config.get("scenario")
        if scenario is None:
            raise ValueError("Select an existing custom stage before playing")
        super().__init__(parent, app, scenario.board_size)
        self.config_options = config
        self.scenario = scenario
        self.show_metrics: bool = config.get("show_metrics", False)
        self.session = PuzzleSession(scenario, show_metrics=self.show_metrics)
        self.state = scenario.create_initial_state()
        self.is_game_active = True
        self.defender_model: str = config.get("agent_model", OPTIMIZED_D6)
        self._ai_task: BackgroundTask | None = None
        self.start_time = time.time()
        self._build_ui()
        self.bind_hotkey("undo", self._on_undo)
        self.bind_hotkey("restart", self._on_reset_attempt)
        self._update_ui_state()

    def _build_ui(self) -> None:
        self.header = HeaderBar(
            self,
            self.scenario.title,
            f"{self.scenario.step_summary}  |  Move limit: {self.session.s_max}",
            "Stages",
            self._on_back_to_select,
        )
        PillButton(self.header.actions, "Rules", self._show_stage_rules, icon="help").pack()

        options = self.config_options
        self.card_player = PlayerCard(
            self.side,
            options.get("p1_name", settings.DEFAULT_PLAYER_NAME),
            "H",
            0,
            self._player_colors()[0],
        )
        self.card_player.pack(fill=tk.X, pady=(0, METRICS.px(SPACE_S)))
        self.card_ai = PlayerCard(
            self.side,
            options.get("agent_label", "Defender"),
            "E",
            1,
            self._player_colors()[1],
        )
        self.card_ai.pack(fill=tk.X, pady=(0, METRICS.px(GUTTER)))

        self.lbl_status = self.add_status()
        self.lbl_steps = stat_line(self.side, "Steps")
        self.lbl_delay = stat_line(self.side, "Extra moves")
        self.lbl_sub_stats = stat_line(self.side, "Resets / undos")
        if self.show_metrics:
            section_title(self.side, "AI metrics").pack(
                fill=tk.X, pady=(METRICS.px(SPACE_L), METRICS.px(SPACE_S))
            )
            self.lbl_ai_metrics = WrapLabel(
                self.side,
                text="No reply yet.",
                font=font("caption"),
                fg=COLORS["ink_muted"],
            )
            self.lbl_ai_metrics.pack(fill=tk.X)
        self.add_history()
        self.add_cycle_card()

        actions = self.action_bar
        gap = METRICS.px(SPACE_S) // 2
        self.btn_ai_retry = PillButton(actions, "Retry Proof", self._trigger_ai_move)
        self.btn_ai_fallback = PillButton(actions, "Use Alpha-Beta", self._use_alpha_beta_reply)
        if self.defender_model == EXACT_DEFENDER:
            self.btn_ai_retry.grid(row=0, column=0, sticky="ew", padx=(0, gap), pady=gap)
            self.btn_ai_fallback.grid(row=0, column=1, sticky="ew", padx=(gap, 0), pady=gap)
        self._set_recovery(retry=False, fallback=False)
        self.btn_undo = PillButton(actions, "Undo", self._on_undo, icon="undo")
        self.btn_undo.grid(row=1, column=0, sticky="ew", padx=(0, gap), pady=gap)
        PillButton(actions, "Reset", self._on_reset_attempt, icon="restart").grid(
            row=1, column=1, sticky="ew", padx=(gap, 0), pady=gap
        )
        PillButton(actions, "Give Up", self._on_concede, variant="destructive", icon="flag").grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=gap
        )

    def _player_colors(self) -> dict[int, str]:
        return self.config_options.get("colors", {0: COLORS["accent"], 1: COLORS["danger"]})

    def _can_interact(self) -> bool:
        return (
            self.is_game_active
            and not self.session.is_neutralized
            and self.state.winner is None
            and self.state.current_turn == 0
        )

    def _commit_move(self, start: Coord, end: Coord) -> None:
        make_puzzle_move(self.state, start, end)
        self.last_move = (start, end)
        self.clear_selection()
        self.session.record_player_step()
        status = self.session.evaluate_status(self.state)
        self._update_ui_state()
        if status == STATUS_SOLVED:
            self._handle_puzzle_finish(solved=True)
        elif status != STATUS_NEUTRALIZED and self.state.current_turn == 1:
            self._trigger_ai_move()

    def _trigger_ai_move(self) -> None:
        if not self.is_game_active or self.session.is_neutralized or self.state.current_turn != 1:
            return
        self._cancel_defender()
        self._set_recovery(retry=False, fallback=False)
        position = self.state.clone()
        model = self.defender_model
        if model == EXACT_DEFENDER:
            remaining = self.session.s_max - self.session.current_attempt_steps
            policy = dict(self.scenario.defender_policy)
            self._set_status("Proving the best reply...", COLORS["ink_muted"])
            self._set_recovery(retry=False, fallback=True)
            self._ai_task = BackgroundTask(
                self,
                lambda cancel, _report: get_exact_defender_reply(
                    position, remaining, policy, cancel_event=cancel
                ),
                self._on_exact_reply,
                self._on_ai_failed,
            )
        else:
            depth = self.config_options.get("search_depth", settings.OPTIMIZED_DEFAULT_DEPTH)
            self._set_status("The defender is thinking...", COLORS["ink_muted"])
            self._ai_task = BackgroundTask(
                self,
                lambda _cancel, _report: get_defender_move(position, model, depth),
                self._on_search_reply,
                self._on_ai_failed,
            )
        self._ai_task.start()

    def _use_alpha_beta_reply(self) -> None:
        """Answer with the heuristic agent, only because the player asked for it."""
        self._cancel_defender()
        self._set_recovery(retry=False, fallback=False)
        position = self.state.clone()
        self._set_status("Using an unproven Alpha-Beta reply...", COLORS["ink_muted"])
        self._ai_task = BackgroundTask(
            self,
            lambda _cancel, _report: get_defender_move(
                position, OPTIMIZED_D6, settings.OPTIMIZED_DEFAULT_DEPTH
            ),
            self._on_search_reply,
            self._on_ai_failed,
        )
        self._ai_task.start()

    def _on_search_reply(self, result: tuple[MoveTuple | None, float, SearchTelemetry]) -> None:
        self._ai_task = None
        move, score, telemetry = result
        self._apply_defender_move(move, score, telemetry)

    def _on_exact_reply(self, result: dict[str, Any]) -> None:
        self._ai_task = None
        status = result["status"]
        if status == "PROVEN":
            self._merge_policy(result["defender_policy"])
            self._set_recovery(retry=False, fallback=False)
            self._apply_defender_move(
                result["move"],
                result["eval_score"],
                result["telemetry"],
                result["proof_horizon"],
            )
        elif status == "NO_MOVES":
            self._set_recovery(retry=False, fallback=False)
            self._apply_defender_move(None, result["eval_score"], result["telemetry"])
        elif status == "TERMINAL":
            self._update_ui_state()
        else:
            self._show_unverified_defense()

    def _on_ai_failed(self, message: str) -> None:
        self._ai_task = None
        logger.error("Defender failed: %s", message)
        if self.defender_model == EXACT_DEFENDER:
            self._show_unverified_defense()
        else:
            self._set_status("The defender could not reply. Undo or reset.", COLORS["danger"])

    def _merge_policy(self, updates: dict[str, Any]) -> None:
        policy = self.scenario.defender_policy
        for key, entry in updates.items():
            old = policy.get(key)
            if (
                old is None
                or (old["steps"] is None and entry["steps"] is not None)
                or (
                    old["steps"] is None
                    and entry["steps"] is None
                    and entry["remaining"] > old["remaining"]
                )
            ):
                policy[key] = entry

    def _set_recovery(self, retry: bool, fallback: bool) -> None:
        """Enable the recovery buttons; they keep their place so nothing below them moves."""
        self.btn_ai_retry.set_enabled(retry)
        self.btn_ai_fallback.set_enabled(fallback)

    def _show_unverified_defense(self) -> None:
        self._set_status(
            "The proof ran out of budget, so no reply was guessed.", COLORS["ink_muted"]
        )
        self._set_recovery(retry=True, fallback=True)

    def _cancel_defender(self) -> None:
        if self._ai_task is not None:
            self._ai_task.cancel()
            self._ai_task = None

    def _apply_defender_move(
        self,
        best_move: MoveTuple | None,
        eval_score: float,
        telemetry: SearchTelemetry,
        proof_horizon: int | None = None,
    ) -> None:
        if not best_move:
            self.state.current_turn = 0
            self.state.winner = None
            self._update_ui_state()
            return
        start, end = best_move
        self.session.record_ai_telemetry(
            action=(start, end),
            eval_score=eval_score,
            t_turn=telemetry.t_turn,
            nodes_gen=telemetry.nodes_generated,
            nodes_eval=telemetry.nodes_evaluated,
            prune_efficiency=telemetry.pruning_efficiency,
            completed_depth=telemetry.completed_depth,
            timed_out=telemetry.timed_out,
            proof_horizon=proof_horizon,
        )

        make_puzzle_move(self.state, start, end)
        self.last_move = (start, end)
        self._update_ui_state()

    def _set_status(self, text: str, color: str) -> None:
        self.lbl_status.configure(text=text, fg=color)

    def _update_ui_state(self) -> None:
        self.render_board()
        session = self.session
        minimum = session.s_optimal
        self.lbl_steps.configure(text=f"{session.current_attempt_steps} / {session.s_max}")
        delta = session.delay_margin
        self.lbl_delay.configure(
            text="N/A" if minimum is None else f"+{delta}",
        )
        self.lbl_sub_stats.configure(text=f"{session.resets_count} / {session.undo_count}")

        status = session.evaluate_status(self.state)
        your_turn = self.state.current_turn == 0
        self.card_player.set_active(your_turn)
        self.card_ai.set_active(not your_turn)
        if status == STATUS_SOLVED:
            self._set_status("Solved", COLORS["ink"])
        elif status == STATUS_NEUTRALIZED:
            self._set_status(
                f"{session.neutralization_reason}. Undo or reset to try again.",
                COLORS["danger"],
            )
        elif your_turn and status == STATUS_DELAYED:
            self._set_status(f"Your turn (+{delta} over minimum)", COLORS["ink_muted"])
        elif your_turn:
            self._set_status("Your turn", COLORS["ink"])
        self._refresh_metrics()
        self.refresh_history()
        self.btn_undo.set_enabled(bool(self.state.history))

    def _refresh_metrics(self) -> None:
        if not self.show_metrics or not self.session.ai_telemetry_history:
            return
        last = self.session.ai_telemetry_history[-1]
        size = self.state.board_size
        start, end = last["action"]
        score = last["eval_score"]
        if score <= -settings.DECISIVE_SCORE:
            score_text = "Neutralized"
        elif score >= settings.DECISIVE_SCORE:
            score_text = "Breakthrough"
        else:
            score_text = f"{score:+.1f}"
        horizon = last["proof_horizon"]
        detail = (
            f"Proven reply, horizon {horizon} moves"
            if horizon is not None
            else (
                f"Pruned {last['prune_efficiency']:.1f}%, depth {last['completed_depth']}"
                + (" (time limit)" if last["timed_out"] else "")
            )
        )
        self.lbl_ai_metrics.configure(
            text=(
                f"{coord_label(start, size)} to {coord_label(end, size)}, eval {score_text}\n"
                f"{last['t_turn']:.3f} s, {detail}"
            )
        )

    def _on_undo(self) -> None:
        if not self.is_game_active:
            return
        self._cancel_defender()
        self._set_recovery(retry=False, fallback=False)
        if self.state.undo():
            self.session.record_undo()
            if self.state.current_turn == 1:
                self.state.undo(count_action=False)
        self.clear_selection()
        self.last_move = None
        self._update_ui_state()

    def _on_reset_attempt(self) -> None:
        self._cancel_defender()
        self._set_recovery(retry=False, fallback=False)
        self.session.reset_attempt()
        self.state = self.scenario.create_initial_state()
        self.clear_selection()
        self.last_move = None
        self.is_game_active = True
        self.start_time = time.time()
        self._update_ui_state()

    def _on_concede(self) -> None:
        if self.is_game_active:
            self._cancel_defender()
            self._handle_puzzle_finish(solved=False, reason="You gave up")

    def _handle_puzzle_finish(self, solved: bool, reason: str = "") -> None:
        if not self.is_game_active:
            return
        self.is_game_active = False
        session = self.session
        time_spent = int(time.time() - self.start_time)
        if solved:
            storage.save_stage_score(
                self.scenario.id,
                self.config_options.get("p1_name", settings.DEFAULT_PLAYER_NAME),
                session.current_attempt_steps,
                time_spent,
                session.undo_count,
                session.delay_margin,
            )
            title = "Puzzle Solved"
            summary = (
                f"You reached the corner in {session.current_attempt_steps} steps.\n"
                f"{self.scenario.step_summary}\n"
                f"Extra moves: +{session.delay_margin}   Time: {time_spent} s"
            )
        else:
            title = "Defender Wins"
            summary = f"{reason or 'The defender stopped your advance'}."
        summary += (
            f"\n\nSteps across resets: {session.cumulative_steps + session.current_attempt_steps}"
            f"\nResets: {session.resets_count}   Undos: {session.undo_count}"
        )
        dialog = Dialog(self, title, summary)
        dialog.add_action("Stages", self._on_back_to_select, cancel=True)
        dialog.add_action("Retry Stage", self._on_reset_attempt, variant="primary", default=True)
        dialog.present()

    def _show_stage_rules(self) -> None:
        self.show_rules(
            f"Reach the corner within {self.session.s_max} moves. "
            f"{self.scenario.step_summary}.\nUndo and Reset stay available after a loss."
        )

    def _on_back_to_select(self) -> None:
        self.app.show_view("puzzle_select")

    def cleanup(self) -> None:
        """Stop the defender and release the shortcuts."""
        self.is_game_active = False
        super().cleanup()
        self._cancel_defender()
        self.unbind_hotkeys()

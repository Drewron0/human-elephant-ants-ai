"""Versus-AI match on the standard board with per-side clocks."""

import logging
import tkinter as tk
from typing import TYPE_CHECKING, Any

from config import settings
from src import storage
from src.ai.practice import DIFFICULTY_LABELS, get_ai_move_with_delay
from src.core.game_logic import Coord, GameState, MoveTuple
from src.ui.background import BackgroundTask
from src.ui.dialogs import Dialog, confirm
from src.ui.play_view import PlayerCard, PlayView, stat_line
from src.ui.scene import HeaderBar
from src.ui.theme import COLORS, GUTTER, HOTKEYS, METRICS, SPACE_S
from src.ui.widgets import PillButton

if TYPE_CHECKING:
    from src.ui.app import GameApp

logger = logging.getLogger(__name__)

LOW_TIME_SECONDS = 15
TICK_MS = 1000


def format_time(seconds: int) -> str:
    """Format a clock value; negative means the match has no timer."""
    if seconds < 0:
        return "--:--"
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


class GameView(PlayView):
    """Plays the human against a practice opponent running off the UI thread."""

    def __init__(self, parent: tk.Misc, app: "GameApp", config: dict[str, Any]) -> None:
        super().__init__(parent, app, settings.DEFAULT_BOARD_SIZE)
        self.config_options = config
        self.state = GameState()
        self.time_limit: int = config.get("time_limit", settings.TIME_LIMIT_CHOICES["2 Minutes"])
        self.time_p1 = self.time_limit
        self.time_p2 = self.time_limit
        self.timer_id: str | None = None
        self.ai_timer_id: str | None = None
        self._ai_task: BackgroundTask | None = None
        self.is_game_active = True
        self._build_ui()
        self.bind_hotkey("undo", self._on_undo)
        self.bind_hotkey("restart", self._on_restart)
        self.bind_hotkey("surrender", self._on_surrender)
        self._update_ui_state()
        self._start_timer()

    def _build_ui(self) -> None:
        options = self.config_options
        self.header = HeaderBar(
            self,
            "Versus AI",
            "Reach the star corner of your opponent",
            "Menu",
            self._on_back_to_hub,
        )
        PillButton(self.header.actions, "Rules", self.show_rules, icon="help").pack()

        level = DIFFICULTY_LABELS.get(options.get("difficulty", "normal"), "Normal")
        self.card_p2 = PlayerCard(
            self.side,
            f"{options.get('p2_name', 'AI')} ({level})",
            "E",
            1,
            self._color(1),
        )
        self.card_p2.pack(fill=tk.X, pady=(0, METRICS.px(SPACE_S)))
        self.card_p1 = PlayerCard(
            self.side,
            options.get("p1_name", settings.DEFAULT_PLAYER_NAME),
            "H",
            0,
            self._color(0),
        )
        self.card_p1.pack(fill=tk.X, pady=(0, METRICS.px(GUTTER)))

        self.lbl_status = self.add_status()
        self.lbl_turns = stat_line(self.side, "Turns")
        self.lbl_undos = stat_line(self.side, "Undos")
        self.add_history()
        self.add_cycle_card()

        actions = self.action_bar
        gap = METRICS.px(SPACE_S) // 2
        self.btn_undo = PillButton(actions, "Undo", self._on_undo, icon="undo")
        self.btn_undo.grid(row=0, column=0, sticky="ew", padx=(0, gap), pady=gap)
        self.btn_restart = PillButton(actions, "Restart", self._on_restart, icon="restart")
        self.btn_restart.grid(row=0, column=1, sticky="ew", padx=(gap, 0), pady=gap)
        self.btn_surrender = PillButton(
            actions,
            HOTKEYS["surrender"]["label"],
            self._on_surrender,
            variant="destructive",
            icon="flag",
        )
        self.btn_surrender.grid(row=1, column=0, columnspan=2, sticky="ew", pady=gap)

    def _color(self, owner: int) -> str:
        return self.config_options.get(f"p{owner + 1}_color", COLORS["accent"])

    def _player_name(self, owner: int) -> str:
        return self.config_options.get(f"p{owner + 1}_name", f"Player {owner + 1}")

    def _player_colors(self) -> dict[int, str]:
        return {0: self._color(0), 1: self._color(1)}

    def _can_interact(self) -> bool:
        return self.is_game_active and self.state.winner is None and self.state.current_turn == 0

    def _commit_move(self, start: Coord, end: Coord) -> None:
        self._execute_move(start, end)

    def _win_reason(self, winner: int) -> str:
        corner = self.state.get_piece(*self.state.target_corners[winner])
        if corner and corner.owner == winner:
            return "Star corner reached"
        return "Opponent has no legal moves"

    def _execute_move(self, start: Coord, end: Coord) -> None:
        if not self.state.make_move(start, end):
            return
        self.last_move = (start, end)
        self.clear_selection()
        self._update_ui_state()
        if self.state.winner is not None:
            self._handle_game_over(self.state.winner, self._win_reason(self.state.winner))
        elif self.state.current_turn == 1:
            self._start_ai_turn()

    def _start_ai_turn(self) -> None:
        position = self.state.clone()
        difficulty = self.config_options.get("difficulty", "normal")
        self._ai_task = BackgroundTask(
            self,
            lambda _cancel, _report: get_ai_move_with_delay(position, difficulty),
            self._on_ai_ready,
            self._on_ai_failed,
        )
        self._ai_task.start()

    def _on_ai_ready(self, result: tuple[MoveTuple | None, float]) -> None:
        self._ai_task = None
        move, delay = result
        if move is None or not self.is_game_active:
            return

        def play() -> None:
            self.ai_timer_id = None
            self._execute_move(move[0], move[1])

        self.ai_timer_id = self.after(int(delay * 1000), play)

    def _on_ai_failed(self, message: str) -> None:
        self._ai_task = None
        logger.error("AI opponent failed: %s", message)
        self.lbl_status.configure(
            text="The AI could not move. Undo or restart.", fg=COLORS["danger"]
        )

    def _cancel_ai(self) -> None:
        if self._ai_task is not None:
            self._ai_task.cancel()
            self._ai_task = None
        if self.ai_timer_id is not None:
            self.after_cancel(self.ai_timer_id)
            self.ai_timer_id = None

    def _update_ui_state(self) -> None:
        self.render_board()
        turn = self.state.current_turn
        self.lbl_status.configure(
            text="Your turn" if turn == 0 else f"{self._player_name(1)} is thinking...",
            fg=COLORS["ink"] if turn == 0 else COLORS["ink_muted"],
        )
        self.lbl_turns.configure(text=str(self.state.total_turns))
        self.lbl_undos.configure(text=str(self.state.undos_p1))
        self.card_p1.set_active(turn == 0)
        self.card_p2.set_active(turn == 1)
        self._refresh_clocks()
        self.refresh_history()
        self.btn_undo.set_enabled(
            bool(self.config_options.get("undo_enabled", True) and self.state.history)
        )

    def _refresh_clocks(self) -> None:
        limited = self.time_limit > 0
        self.card_p1.set_value(
            format_time(self.time_p1), limited and self.time_p1 <= LOW_TIME_SECONDS
        )
        self.card_p2.set_value(
            format_time(self.time_p2), limited and self.time_p2 <= LOW_TIME_SECONDS
        )

    def _start_timer(self) -> None:
        if self.time_limit <= 0:
            return
        self.timer_id = self.after(TICK_MS, self._tick)

    def _tick(self) -> None:
        self.timer_id = None
        if not self.is_game_active or self.state.winner is not None:
            return
        if self.state.current_turn == 0:
            self.time_p1 -= 1
        else:
            self.time_p2 -= 1
        self._refresh_clocks()
        if self.time_p1 <= 0:
            self._handle_game_over(1, f"{self._player_name(0)} ran out of time")
        elif self.time_p2 <= 0:
            self._handle_game_over(0, f"{self._player_name(1)} ran out of time")
        else:
            self.timer_id = self.after(TICK_MS, self._tick)

    def _stop_timer(self) -> None:
        if self.timer_id is not None:
            self.after_cancel(self.timer_id)
            self.timer_id = None
        self._cancel_ai()

    def _handle_game_over(self, winner: int, reason: str) -> None:
        if not self.is_game_active:
            return
        self.is_game_active = False
        self.state.winner = winner
        self._stop_timer()
        self.clear_selection()
        self.render_board()
        self.lbl_status.configure(text=f"{self._player_name(winner)} wins", fg=COLORS["ink"])
        if winner == 0:
            difficulty = self.config_options.get("difficulty", "normal")
            storage.save_pve_score(
                self._player_name(0),
                self.state.total_turns,
                max(0, self.time_p1) if self.time_limit > 0 else settings.NO_TIMER,
                self.state.undos_p1,
                DIFFICULTY_LABELS.get(difficulty, difficulty),
            )
        summary = f"{reason}.\nTurns: {self.state.total_turns}   Undos: {self.state.undos_p1}"
        if self.time_limit > 0:
            remaining = self.time_p1 if winner == 0 else self.time_p2
            summary += f"\nTime remaining: {format_time(max(0, remaining))}"
        dialog = Dialog(self, f"{self._player_name(winner)} Wins", summary)
        dialog.add_action("Menu", lambda: self.app.show_view("menu"), cancel=True)
        dialog.add_action("Leaderboard", lambda: self.app.show_view("leaderboard"))
        dialog.add_action("Play Again", self._restart_match, variant="primary", default=True)
        dialog.present()

    def _on_undo(self) -> None:
        if not self.config_options.get("undo_enabled", True) or not self.is_game_active:
            return
        self._cancel_ai()
        if self.state.undo() and self.state.current_turn == 1:
            self.state.undo(count_action=False)
        self.clear_selection()
        self.last_move = None
        self._update_ui_state()

    def _on_restart(self) -> None:
        if not self.is_game_active:
            self._restart_match()
            return
        confirm(
            self,
            "Restart Match?",
            "Your current progress will be lost.",
            "Restart",
            self._restart_match,
        )

    def _restart_match(self) -> None:
        self._stop_timer()
        self.state = GameState()
        self.clear_selection()
        self.last_move = None
        self.is_game_active = True
        self.time_p1 = self.time_limit
        self.time_p2 = self.time_limit
        self._update_ui_state()
        self._start_timer()

    def _on_surrender(self) -> None:
        if not self.is_game_active:
            return
        confirm(
            self,
            "Give Up?",
            "The win will be awarded to your opponent.",
            "Give Up",
            lambda: self._handle_game_over(1, f"{self._player_name(0)} gave up"),
        )

    def _on_back_to_hub(self) -> None:
        if self.is_game_active and self.state.total_turns > 0:
            confirm(
                self,
                "Leave Match?",
                "The match in progress will be lost.",
                "Leave",
                lambda: self.app.show_view("menu"),
                cancel_text="Stay",
            )
        else:
            self.app.show_view("menu")

    def cleanup(self) -> None:
        """Stop the clock and the opponent, and release the shortcuts."""
        self.is_game_active = False
        super().cleanup()
        self._stop_timer()
        self.unbind_hotkeys()

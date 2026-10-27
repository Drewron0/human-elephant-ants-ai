import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional, Tuple, List
import time

from ui_theme import (
    THEME, FONT_NAME, HOTKEYS, ButtonPrimary, ButtonSecondary, ButtonDanger,
    ThemedModal, draw_star, bind_mousewheel
)
from game_logic import GameState, Piece
from puzzle_logic import PuzzleScenario, PuzzleSession, PRECONFIGURED_PUZZLES, generate_winnable_puzzle
from ai_engine import get_defender_move, DEFAULT_PROPOSAL_WEIGHTS
import storage


class PuzzleGameView(tk.Frame):
    """
    Puzzle Game Screen for the 'Optimal Defender' scenario.
    Adheres strictly to Apple Design principles: resizable PanedWindow layout,
    adaptive board scaling, restrained typography, and spoiler-free metrics toggling.
    """
    def __init__(self, parent, app, config: Dict[str, Any]):
        super().__init__(parent, bg=THEME['bg'])
        self.app = app
        self.config = config

        # Initialize Scenario & Session
        scenario_key = config.get('puzzle_scenario', 'stage_6x6_01')
        custom_obj = config.get('custom_scenario_obj')

        if custom_obj:
            self.scenario = custom_obj
        elif scenario_key in PRECONFIGURED_PUZZLES:
            self.scenario = PRECONFIGURED_PUZZLES[scenario_key]
        else:
            self.scenario = generate_winnable_puzzle(board_size=config.get('board_size', 6))

        self.show_metrics = config.get('show_metrics', False)
        self.session = PuzzleSession(self.scenario, show_metrics=self.show_metrics)
        self.state = self.scenario.create_initial_state()

        self.selected_sq: Optional[Tuple[int, int]] = None
        self.valid_targets: List[Tuple[int, int]] = []
        self.last_move: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None
        self.is_game_active = True
        self.ai_timer_id: Optional[str] = None
        self.start_time = time.time()
        self._resize_job = None

        # Canvas dynamic sizing
        self.current_sq_size: int = 80

        self._build_ui()
        self._bind_hotkeys()

    def _build_ui(self):
        # Top Bar
        top_bar = tk.Frame(self, bg=THEME['surface'], height=42, bd=0, highlightbackground=THEME['border'], highlightthickness=1)
        top_bar.pack(fill=tk.X, padx=0, pady=0)

        title_box = tk.Frame(top_bar, bg=THEME['surface'])
        title_box.pack(side=tk.LEFT, padx=16, pady=8)

        tk.Label(
            title_box,
            text=self.scenario.title,
            font=(FONT_NAME, 11, "bold"),
            bg=THEME['surface'],
            fg=THEME['text']
        ).pack(side=tk.LEFT)

        tk.Label(
            title_box,
            text=f"- Optimal Steps: {self.session.s_optimal} | Move Limit: {self.session.s_max}",
            font=(FONT_NAME, 9),
            bg=THEME['surface'],
            fg=THEME['text_muted']
        ).pack(side=tk.LEFT, padx=(8, 0))

        ButtonSecondary(top_bar, text="Back to Stages", command=self._on_back_to_select).pack(side=tk.RIGHT, padx=12, pady=6)
        ButtonSecondary(top_bar, text="Rules", command=self._show_rules_modal).pack(side=tk.RIGHT, padx=(0, 6), pady=6)

        # Resizable PanedWindow: Board (Left) & Controls (Right)
        self.paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg=THEME['border'], sashrelief=tk.FLAT, sashwidth=4, bd=0)
        self.paned.pack(fill=tk.BOTH, expand=True)

        # Left Board Container (Adaptive & Resizable)
        self.board_container = tk.Frame(self.paned, bg=THEME['bg'])
        self.paned.add(self.board_container, minsize=420, stretch="always")
        self.board_container.bind("<Configure>", self._on_board_container_resize)

        self.canvas_card = tk.Frame(
            self.board_container,
            bg=THEME['surface'],
            bd=1,
            relief=tk.SOLID,
            highlightbackground=THEME['border'],
            highlightthickness=1,
            padx=6,
            pady=6
        )
        self.canvas_card.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self.canvas = tk.Canvas(self.canvas_card, width=540, height=540, bg=THEME['bg'], highlightthickness=0)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_board_click)

        # Right Controls & Telemetry Sidebar (Resizable)
        self.sidebar_pane = tk.Frame(self.paned, bg=THEME['surface'], bd=0, highlightbackground=THEME['border'], highlightthickness=1)
        self.paned.add(self.sidebar_pane, minsize=300, stretch="never")

        sidebar_scroll_canvas = tk.Canvas(self.sidebar_pane, bg=THEME['surface'], highlightthickness=0)
        scroll_y = ttk.Scrollbar(self.sidebar_pane, orient=tk.VERTICAL, command=sidebar_scroll_canvas.yview)
        content = tk.Frame(sidebar_scroll_canvas, bg=THEME['surface'], padx=14, pady=12)

        content.bind(
            "<Configure>",
            lambda e: sidebar_scroll_canvas.configure(scrollregion=sidebar_scroll_canvas.bbox("all"))
        )
        self.sidebar_canvas_window = sidebar_scroll_canvas.create_window((0, 0), window=content, anchor="nw")
        sidebar_scroll_canvas.configure(yscrollcommand=scroll_y.set)

        sidebar_scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        sidebar_scroll_canvas.bind("<Configure>", lambda e: sidebar_scroll_canvas.itemconfig(self.sidebar_canvas_window, width=e.width))

        bind_mousewheel(content, sidebar_scroll_canvas)
        bind_mousewheel(sidebar_scroll_canvas, sidebar_scroll_canvas)

        # Player & AI Info Card
        players_card = tk.Frame(content, bg=THEME['surface_card'], padx=10, pady=8, bd=1, relief=tk.SOLID, highlightbackground=THEME['border'], highlightthickness=1)
        players_card.pack(fill=tk.X, pady=(0, 8))

        p_name = self.config.get('p1_name', 'Player 1')
        ai_name = self.config.get('agent_model_name', 'Proposed: Optimized Agent (d=6)')

        row_p = tk.Frame(players_card, bg=THEME['surface_card'])
        row_p.pack(fill=tk.X)
        tk.Label(row_p, text="Player:", font=(FONT_NAME, 9, "bold"), bg=THEME['surface_card'], fg=THEME['text_muted']).pack(side=tk.LEFT)
        tk.Label(row_p, text=p_name, font=(FONT_NAME, 9, "bold"), bg=THEME['surface_card'], fg=self.config.get('p1_color', '#30D158')).pack(side=tk.RIGHT)

        row_ai = tk.Frame(players_card, bg=THEME['surface_card'])
        row_ai.pack(fill=tk.X, pady=(3, 0))
        tk.Label(row_ai, text="Defender:", font=(FONT_NAME, 9, "bold"), bg=THEME['surface_card'], fg=THEME['text_muted']).pack(side=tk.LEFT)
        tk.Label(row_ai, text=ai_name, font=(FONT_NAME, 8), bg=THEME['surface_card'], fg=self.config.get('p2_color', '#FF453A')).pack(side=tk.RIGHT)

        # Strategic Attempt Telemetry Box
        strat_card = tk.Frame(content, bg=THEME['surface_light'], padx=10, pady=8, bd=1, relief=tk.SOLID, highlightbackground=THEME['border'], highlightthickness=1)
        strat_card.pack(fill=tk.X, pady=(0, 8))

        tk.Label(strat_card, text="ATTEMPT PROGRESS", font=(FONT_NAME, 8, "bold"), bg=THEME['surface_light'], fg=THEME['text_muted']).pack(anchor="w", pady=(0, 3))

        s_row = tk.Frame(strat_card, bg=THEME['surface_light'])
        s_row.pack(fill=tk.X)
        self.lbl_steps = tk.Label(s_row, text=f"Steps: 0 / {self.session.s_optimal}", font=(FONT_NAME, 10, "bold"), bg=THEME['surface_light'], fg=THEME['text'])
        self.lbl_steps.pack(side=tk.LEFT)

        self.lbl_delay = tk.Label(s_row, text="Delay: 0 moves", font=(FONT_NAME, 9, "bold"), bg=THEME['surface_light'], fg=THEME['success'])
        self.lbl_delay.pack(side=tk.RIGHT)

        st_row = tk.Frame(strat_card, bg=THEME['surface_light'])
        st_row.pack(fill=tk.X, pady=(3, 0))
        self.lbl_sub_stats = tk.Label(st_row, text="Resets: 0 | Undos: 0", font=(FONT_NAME, 8), bg=THEME['surface_light'], fg=THEME['text_muted'])
        self.lbl_sub_stats.pack(side=tk.LEFT)

        self.lbl_status = tk.Label(st_row, text="ON TRACK", font=(FONT_NAME, 8, "bold"), bg=THEME['surface_light'], fg=THEME['accent'])
        self.lbl_status.pack(side=tk.RIGHT)

        # AI Search Metrics Box (Only shown if show_metrics is enabled)
        if self.show_metrics:
            self.ai_metrics_card = tk.Frame(content, bg=THEME['surface_card'], padx=10, pady=8, bd=1, relief=tk.SOLID, highlightbackground=THEME['border'], highlightthickness=1)
            self.ai_metrics_card.pack(fill=tk.X, pady=(0, 8))

            tk.Label(self.ai_metrics_card, text="AI SEARCH TELEMETRY", font=(FONT_NAME, 8, "bold"), bg=THEME['surface_card'], fg=THEME['text_muted']).pack(anchor="w", pady=(0, 3))

            self.lbl_ai_action = tk.Label(self.ai_metrics_card, text="Last Action A = None", font=(FONT_NAME, 8), bg=THEME['surface_card'], fg=THEME['text'])
            self.lbl_ai_action.pack(anchor="w")

            self.lbl_ai_metrics = tk.Label(self.ai_metrics_card, text="Latency: -- | Prune: 0.0%", font=(FONT_NAME, 8), bg=THEME['surface_card'], fg=THEME['text_muted'])
            self.lbl_ai_metrics.pack(anchor="w", pady=(2, 0))
        else:
            self.ai_metrics_card = None

        # Move History
        tk.Label(content, text="Move History:", font=(FONT_NAME, 9, "bold"), bg=THEME['surface'], fg=THEME['text_muted']).pack(anchor="w")
        notation_box = tk.Frame(content, bg=THEME['surface_light'], height=130)
        notation_box.pack(fill=tk.X, pady=(3, 8))
        notation_box.pack_propagate(False)

        hist_scroll = ttk.Scrollbar(notation_box)
        hist_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.list_notation = tk.Listbox(
            notation_box,
            bg=THEME['surface_card'],
            fg=THEME['text'],
            font=(FONT_NAME, 8),
            bd=0,
            yscrollcommand=hist_scroll.set,
            selectbackground=THEME['accent']
        )
        self.list_notation.pack(fill=tk.BOTH, expand=True)
        hist_scroll.config(command=self.list_notation.yview)
        bind_mousewheel(self.list_notation, self.list_notation)

        # Action Buttons
        btn_frame = tk.Frame(content, bg=THEME['surface'])
        btn_frame.pack(fill=tk.X, pady=(2, 0))

        self.btn_undo = ButtonSecondary(btn_frame, text=f"Undo ({HOTKEYS['undo']['key_str']})", command=self._on_undo)
        self.btn_undo.grid(row=0, column=0, sticky="ew", padx=2, pady=2)

        ButtonSecondary(btn_frame, text=f"Reset ({HOTKEYS['restart']['key_str']})", command=self._on_reset_attempt).grid(row=0, column=1, sticky="ew", padx=2, pady=2)
        ButtonDanger(btn_frame, text="Concede", command=self._on_concede).grid(row=1, column=0, sticky="ew", padx=2, pady=2)
        ButtonSecondary(btn_frame, text="Stages List", command=self._on_back_to_select).grid(row=1, column=1, sticky="ew", padx=2, pady=2)

        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        self._draw_board()
        self._update_ui_state()

    def _bind_hotkeys(self):
        self.app.bind(HOTKEYS['undo']['seq'], lambda e: self._on_undo())
        self.app.bind(HOTKEYS['restart']['seq'], lambda e: self._on_reset_attempt())

    def _unbind_hotkeys(self):
        for h in [HOTKEYS['undo'], HOTKEYS['restart']]:
            self.app.unbind(h['seq'])

    def _on_board_container_resize(self, event):
        """Dynamically adjusts square size and canvas dimensions to fit the container with debouncing."""
        if self._resize_job is not None:
            try:
                self.after_cancel(self._resize_job)
            except Exception:
                pass
        self._resize_job = self.after(35, lambda w=event.width, h=event.height: self._apply_board_resize(w, h))

    def _apply_board_resize(self, width: int, height: int):
        self._resize_job = None
        avail_w = width - 24
        avail_h = height - 24
        dim = max(300, min(avail_w, avail_h, 700))
        size = self.state.board_size
        new_sq_size = dim // size
        total_canvas_dim = new_sq_size * size + 30

        if new_sq_size == self.current_sq_size and self.canvas.winfo_width() == total_canvas_dim:
            return

        self.current_sq_size = new_sq_size
        self.canvas.config(width=total_canvas_dim, height=total_canvas_dim)
        self._draw_board()

    def _draw_board(self):
        self.canvas.delete("all")
        size = self.state.board_size
        sq_size = self.current_sq_size
        board_dim = size * sq_size
        total_dim = board_dim + 30

        self.canvas.create_rectangle(0, 0, total_dim, total_dim, fill=THEME['surface'], outline='')

        # Coordinates on bottom and right
        for c in range(size):
            x = c * sq_size + sq_size // 2
            y = board_dim + 15
            self.canvas.create_text(x, y, text=chr(65 + c), font=(FONT_NAME, 8, "bold"), fill=THEME['text_muted'])

        for r in range(size):
            x = board_dim + 15
            y = r * sq_size + sq_size // 2
            self.canvas.create_text(x, y, text=str(size - r), font=(FONT_NAME, 8, "bold"), fill=THEME['text_muted'])

        # Draw Cells
        for r in range(size):
            for c in range(size):
                x0 = c * sq_size
                y0 = r * sq_size
                x1 = x0 + sq_size
                y1 = y0 + sq_size

                base_color = THEME['board_light'] if (r + c) % 2 == 0 else THEME['board_dark']
                is_p1_target = ((r, c) == self.state.target_corners[0])
                is_p2_target = ((r, c) == self.state.target_corners[1])

                cell_fill = base_color
                outline_color = THEME['board_grid']
                outline_width = 1

                if is_p1_target:
                    cell_fill = THEME['corner_p1']
                    outline_color = '#F57F17'
                    outline_width = 2
                elif is_p2_target:
                    cell_fill = THEME['corner_p2']
                    outline_color = '#C62828'
                    outline_width = 2

                if self.last_move and ((r, c) == self.last_move[0] or (r, c) == self.last_move[1]):
                    cell_fill = THEME['last_move']

                if self.selected_sq == (r, c):
                    cell_fill = THEME['select_square']

                if (r, c) in self.valid_targets:
                    dest_piece = self.state.board[r][c]
                    if dest_piece is not None:
                        cell_fill = THEME['capture_square']
                        outline_color = '#B71C1C'

                self.canvas.create_rectangle(x0, y0, x1, y1, fill=cell_fill, outline=outline_color, width=outline_width)

                if is_p1_target and self.state.board[r][c] is None:
                    draw_star(self.canvas, (x0 + x1) / 2, (y0 + y1) / 2, max(6, sq_size * 0.28), fill='#F57F17', outline='')
                elif is_p2_target and self.state.board[r][c] is None:
                    draw_star(self.canvas, (x0 + x1) / 2, (y0 + y1) / 2, max(6, sq_size * 0.28), fill='#C62828', outline='')

                if (r, c) in self.valid_targets and self.state.board[r][c] is None:
                    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
                    rad = max(4, sq_size // 10)
                    self.canvas.create_oval(cx - rad, cy - rad, cx + rad, cy + rad, fill=THEME['move_dot'], outline='')

                piece = self.state.board[r][c]
                if piece:
                    self._draw_piece(x0, y0, x1, y1, piece, sq_size)

    def _draw_piece(self, x0: int, y0: int, x1: int, y1: int, piece: Piece, sq_size: int):
        color = self.config.get('p1_color', '#30D158') if piece.owner == 0 else self.config.get('p2_color', '#FF453A')
        pad = max(4, sq_size // 8)

        self.canvas.create_oval(x0 + pad, y0 + pad, x1 - pad, y1 - pad, fill=color, outline='#FFFFFF', width=2)
        cx = (x0 + x1) // 2
        cy = (y0 + y1) // 2
        font_sz = max(8, sq_size // 4)
        self.canvas.create_text(cx, cy, text=piece.p_type, font=(FONT_NAME, font_sz, "bold"), fill='#FFFFFF')

    def _on_board_click(self, event):
        if not self.is_game_active or self.state.winner is not None or self.state.current_turn != 0:
            return

        size = self.state.board_size
        sq_size = self.current_sq_size
        c = event.x // sq_size
        r = event.y // sq_size

        if not (0 <= r < size and 0 <= c < size):
            return

        if self.selected_sq:
            if (r, c) in self.valid_targets:
                self._execute_player_move(self.selected_sq, (r, c))
            else:
                target_p = self.state.board[r][c]
                if target_p and target_p.owner == self.state.current_turn:
                    self.selected_sq = (r, c)
                    self.valid_targets = [m[1] for m in self.state.get_valid_moves_for_piece(r, c)]
                else:
                    self.selected_sq = None
                    self.valid_targets = []
                self._draw_board()
        else:
            p = self.state.board[r][c]
            if p and p.owner == self.state.current_turn:
                self.selected_sq = (r, c)
                self.valid_targets = [m[1] for m in self.state.get_valid_moves_for_piece(r, c)]
                self._draw_board()

    def _execute_player_move(self, start: Tuple[int, int], end: Tuple[int, int]):
        move = self.state.make_move(start, end)
        if not move:
            return

        self.last_move = (start, end)
        self.selected_sq = None
        self.valid_targets = []
        self.session.record_player_step()

        self._update_ui_state()
        self.update_idletasks()

        status = self.session.evaluate_status(self.state)
        if status == 'SOLVED':
            self._handle_puzzle_finish(solved=True)
            return
        elif status == 'NEUTRALIZED':
            self._handle_puzzle_finish(solved=False, reason=self.session.neutralization_reason)
            return

        if self.state.current_turn == 1 and self.is_game_active:
            self.after(40, self._trigger_ai_move)

    def _trigger_ai_move(self):
        agent_model = self.config.get('agent_model', 'proposed_d6')
        depth = self.config.get('search_depth', 6)
        weights = self.config.get('weights', DEFAULT_PROPOSAL_WEIGHTS)

        best_move, eval_score, telemetry = get_defender_move(
            state=self.state,
            agent_model=agent_model,
            depth=depth,
            weights=weights
        )

        if not best_move:
            self._handle_puzzle_finish(solved=True)
            return

        s, e = best_move
        self.session.record_ai_telemetry(
            source_coord=s,
            target_coord=e,
            eval_score=eval_score,
            t_turn=telemetry.t_turn,
            nodes_gen=telemetry.nodes_generated,
            nodes_eval=telemetry.nodes_evaluated,
            prune_efficiency=telemetry.pruning_efficiency
        )

        def do_move():
            if not self.is_game_active:
                return
            self.state.make_move(s, e)
            self.last_move = (s, e)
            self._update_ui_state()

            status = self.session.evaluate_status(self.state)
            if status == 'SOLVED':
                self._handle_puzzle_finish(solved=True)
            elif status == 'NEUTRALIZED':
                self._handle_puzzle_finish(solved=False, reason=self.session.neutralization_reason)

        self.ai_timer_id = self.after(300, do_move)

    def _update_ui_state(self):
        self._draw_board()

        cur = self.session.current_attempt_steps
        s_opt = self.session.s_optimal
        s_max = self.session.s_max
        self.lbl_steps.config(text=f"Steps: {cur} / {s_opt} (Max: {s_max})")

        delta = self.session.delay_margin
        if delta == 0:
            self.lbl_delay.config(text="Delay: 0 moves (Optimal)", fg=THEME['success'])
        else:
            self.lbl_delay.config(text=f"Delay: +{delta} moves", fg=THEME['warning'])

        self.lbl_sub_stats.config(
            text=f"Resets: {self.session.resets_count} | Undos: {self.session.undo_count}"
        )

        status = self.session.evaluate_status(self.state)
        if status == 'SOLVED':
            self.lbl_status.config(text="SOLVED", fg=THEME['success'])
        elif status == 'NEUTRALIZED':
            self.lbl_status.config(text="NEUTRALIZED", fg=THEME['danger'])
        elif status == 'DELAYED':
            self.lbl_status.config(text=f"DELAYED (+{delta})", fg=THEME['warning'])
        else:
            self.lbl_status.config(text="ON TRACK", fg=THEME['accent'])

        if self.show_metrics and self.ai_metrics_card and self.session.ai_telemetry_history:
            last = self.session.ai_telemetry_history[-1]
            act = last['action']
            score = last['eval_score']
            size = self.state.board_size
            act_str = f"{chr(65 + act[0][1])}{size - act[0][0]} -> {chr(65 + act[1][1])}{size - act[1][0]}"
            if score <= -90000:
                score_str = "Neutralized"
            elif score >= 90000:
                score_str = "Breakthrough"
            else:
                score_str = f"{score:+.1f}"
            self.lbl_ai_action.config(text=f"Action: {act_str} | Eval: {score_str}")

            t = last['t_turn']
            prune = last['prune_efficiency']
            self.lbl_ai_metrics.config(
                text=f"Latency: {t:.3f}s (<=2.0s) | Prune: {prune:.1f}%"
            )

        # Move History
        self.list_notation.delete(0, tk.END)
        for i, n in enumerate(self.state.notation):
            prefix = f"{i + 1}. " if i % 2 == 0 else "   "
            self.list_notation.insert(tk.END, f"{prefix}{n}")
        self.list_notation.yview(tk.END)

        if not self.config.get('undo_enabled', True) or not self.state.history:
            self.btn_undo.config(state=tk.DISABLED, fg=THEME['text_muted'])
        else:
            self.btn_undo.config(state=tk.NORMAL, fg=THEME['text'])

    def _on_undo(self):
        if not self.config.get('undo_enabled', True) or not self.is_game_active:
            return

        if self.state.undo(player_idx=0):
            self.session.record_undo()
            self.state.undo(player_idx=0)

        self.selected_sq = None
        self.valid_targets = []
        self._update_ui_state()

    def _on_reset_attempt(self):
        self.session.reset_attempt()
        self.state = self.scenario.create_initial_state()
        self.selected_sq = None
        self.valid_targets = []
        self.last_move = None
        self.is_game_active = True
        self.start_time = time.time()
        self._update_ui_state()

    def _on_concede(self):
        if not self.is_game_active:
            return
        self._handle_puzzle_finish(solved=False, reason="Conceded by Player")

    def _handle_puzzle_finish(self, solved: bool, reason: str = ""):
        self.is_game_active = False
        time_spent = int(time.time() - self.start_time)

        # Record Score in Stage-Specific Leaderboard (Requirement)
        if solved:
            p_name = self.config.get('p1_name', 'Player 1')
            is_guest = self.config.get('is_guest_1', False)
            storage.save_stage_score(
                stage_id=self.scenario.id,
                username=p_name,
                steps=self.session.current_attempt_steps,
                time_spent=time_spent,
                undos=self.session.undo_count,
                delay_margin=self.session.delay_margin,
                is_guest=is_guest
            )

        modal = ThemedModal(self, "Stage Outcome", min_width=440)

        if solved:
            tk.Label(
                modal.body,
                text="Puzzle Solved!",
                font=(FONT_NAME, 14, "bold"),
                bg=THEME['surface'],
                fg=THEME['success']
            ).pack(pady=(6, 2))

            summary = (
                f"You reached the corner in {self.session.current_attempt_steps} steps "
                f"(Optimal: {self.session.s_optimal}).\n"
                f"Forced Delay Margin: +{self.session.delay_margin} moves | Time: {time_spent}s."
            )
        else:
            tk.Label(
                modal.body,
                text="Puzzle Neutralized (Defender Wins)",
                font=(FONT_NAME, 14, "bold"),
                bg=THEME['surface'],
                fg=THEME['danger']
            ).pack(pady=(6, 2))

            cause = reason or "Target rendered unreachable"
            summary = (
                f"The AI optimal defender neutralized your advance.\n"
                f"Cause: {cause}."
            )

        tk.Label(
            modal.body,
            text=summary,
            font=(FONT_NAME, 9),
            bg=THEME['surface'],
            fg=THEME['text_muted'],
            justify="center"
        ).pack(pady=(0, 10))

        box = tk.Frame(modal.body, bg=THEME['surface_light'], padx=12, pady=8)
        box.pack(fill=tk.X, pady=4)

        tk.Label(
            box,
            text=f"Total Steps (Current Attempt): {self.session.current_attempt_steps} / Max: {self.session.s_max}",
            font=(FONT_NAME, 9, "bold"),
            bg=THEME['surface_light'],
            fg=THEME['text']
        ).pack(anchor="w")

        tk.Label(
            box,
            text=f"Cumulative Steps Across Resets: {self.session.cumulative_steps + self.session.current_attempt_steps}",
            font=(FONT_NAME, 8),
            bg=THEME['surface_light'],
            fg=THEME['text_muted']
        ).pack(anchor="w")

        tk.Label(
            box,
            text=f"Resets: {self.session.resets_count} | Undos Used: {self.session.undo_count}",
            font=(FONT_NAME, 8),
            bg=THEME['surface_light'],
            fg=THEME['text_muted']
        ).pack(anchor="w")

        def retry():
            modal.dismiss()
            self._on_reset_attempt()

        def to_select():
            modal.dismiss()
            self._cleanup()
            self.app.show_view('puzzle_select')

        ButtonPrimary(modal.footer, text="Retry Stage", command=retry).pack(side=tk.LEFT, padx=3)
        ButtonSecondary(modal.footer, text="Stages Catalog", command=to_select).pack(side=tk.RIGHT, padx=3)

    def _show_rules_modal(self):
        modal = ThemedModal(self, "Rules and Movement", min_width=480)
        content = (
            "1. Objective:\n"
            f"   Navigate your piece to the opponent's star corner within Move Limit={self.session.s_max} moves.\n"
            f"   The optimal path takes {self.session.s_optimal} steps.\n\n"
            "2. Combat Hierarchy:\n"
            "   Elephant (E) defeats Human (H)\n"
            "   Human (H) defeats Ant (A)\n"
            "   Ant (A) defeats Elephant (E)\n"
            "   Matching pieces cannot capture each other.\n\n"
            "3. Movement:\n"
            "   Each piece moves 1 square in any of the 8 directions.\n"
            "   Squares highlighted red represent valid captures."
        )
        tk.Label(
            modal.body,
            text=content,
            font=(FONT_NAME, 9),
            bg=THEME['surface'],
            fg=THEME['text'],
            justify="left"
        ).pack(anchor="w", pady=4)

        ButtonPrimary(modal.footer, text="Close", command=modal.dismiss).pack(side=tk.RIGHT)

    def _on_back_to_select(self):
        self._cleanup()
        self.app.show_view('puzzle_select')

    def _cleanup(self):
        if self._resize_job is not None:
            try:
                self.after_cancel(self._resize_job)
            except Exception:
                pass
            self._resize_job = None
        self._unbind_hotkeys()
        if self.ai_timer_id:
            self.after_cancel(self.ai_timer_id)
            self.ai_timer_id = None

import tkinter as tk
from typing import Dict, Any, Optional, Tuple, List
import time

from ui_theme import (
    THEME, FONT_NAME, HOTKEYS, ButtonPrimary, ButtonSecondary, ButtonDanger,
    ThemedModal, draw_star
)
from game_logic import GameState, Piece
from puzzle_logic import PuzzleScenario, PuzzleSession, PRECONFIGURED_PUZZLES, generate_procedural_puzzle
from ai_engine import get_defender_move, DEFAULT_PROPOSAL_WEIGHTS
import storage


class PuzzleGameView(tk.Frame):
    """
    Puzzle Game Screen for the 'Optimal Defender' scenario.
    Adheres strictly to the existing UI theme, color palette, and layout geometry.
    """
    def __init__(self, parent, app, config: Dict[str, Any]):
        super().__init__(parent, bg=THEME['bg'])
        self.app = app
        self.config = config

        # Initialize Scenario & Session
        scenario_key = config.get('puzzle_scenario', 'p10_proposal')
        board_size = config.get('board_size', 9)

        if scenario_key == 'procedural':
            self.scenario = generate_procedural_puzzle(target_steps=10, board_size=board_size)
        elif scenario_key in PRECONFIGURED_PUZZLES:
            self.scenario = PRECONFIGURED_PUZZLES[scenario_key]
        else:
            self.scenario = PRECONFIGURED_PUZZLES['p10_proposal']

        self.session = PuzzleSession(self.scenario)
        self.state = self.scenario.create_initial_state()

        self.selected_sq: Optional[Tuple[int, int]] = None
        self.valid_targets: List[Tuple[int, int]] = []
        self.last_move: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None
        self.is_game_active = True
        self.ai_timer_id: Optional[str] = None

        self._build_ui()
        self._bind_hotkeys()

    def _build_ui(self):
        # Top objective bar
        top_bar = tk.Frame(
            self,
            bg=THEME['surface'],
            height=36,
            bd=1,
            relief=tk.SOLID,
            highlightbackground=THEME['border'],
            highlightthickness=1
        )
        top_bar.pack(fill=tk.X, padx=16, pady=(10, 6))

        goal_text = (
            f"Puzzle Objective: Reach corner within S_max={self.session.s_max} moves "
            f"(Optimal: S_optimal={self.session.s_optimal}). AI acts as Optimal Defender."
        )
        tk.Label(
            top_bar,
            text=goal_text,
            font=(FONT_NAME, 9, "bold"),
            bg=THEME['surface'],
            fg=THEME['text']
        ).pack(side=tk.LEFT, padx=16, pady=6)

        ButtonSecondary(top_bar, text="Puzzle Brief & Rules", command=self._show_rules_modal).pack(side=tk.RIGHT, padx=10, pady=4)

        # Main Layout
        main_layout = tk.Frame(self, bg=THEME['bg'])
        main_layout.pack(fill=tk.BOTH, expand=True, padx=16, pady=(6, 12))

        # Board Canvas (Left) - exactly 678x678
        canvas_card = tk.Frame(
            main_layout,
            bg=THEME['surface'],
            bd=1,
            relief=tk.SOLID,
            highlightbackground=THEME['border'],
            highlightthickness=1,
            padx=8,
            pady=8
        )
        canvas_card.pack(side=tk.LEFT, fill=tk.BOTH)

        self.canvas = tk.Canvas(canvas_card, width=678, height=678, bg=THEME['bg'], highlightthickness=0)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_board_click)

        # Controls Panel (Right)
        right_panel = tk.Frame(
            main_layout,
            bg=THEME['surface'],
            bd=1,
            relief=tk.SOLID,
            highlightbackground=THEME['border'],
            highlightthickness=1,
            padx=16,
            pady=12
        )
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(14, 0))

        # Defender AI Card
        agent_model_name = self.config.get('agent_model_name', 'Proposed: Optimized Agent (Alpha-Beta d=6)')
        self.card_p2 = tk.Frame(right_panel, bg=THEME['surface_light'], padx=12, pady=6)
        self.card_p2.pack(fill=tk.X, pady=(0, 4))
        self.lbl_p2_name = tk.Label(
            self.card_p2,
            text=f"AI Defender: {agent_model_name}",
            font=(FONT_NAME, 9, "bold"),
            bg=THEME['surface_light'],
            fg=self.config.get('p2_color', '#E74C3C')
        )
        self.lbl_p2_name.pack(side=tk.LEFT)

        # Player Card
        p1_title = self.config.get('p1_name', 'Player 1')
        self.card_p1 = tk.Frame(right_panel, bg=THEME['surface_light'], padx=12, pady=6)
        self.card_p1.pack(fill=tk.X, pady=(0, 8))
        self.lbl_p1_name = tk.Label(
            self.card_p1,
            text=f"Player: {p1_title}",
            font=(FONT_NAME, 9, "bold"),
            bg=THEME['surface_light'],
            fg=self.config.get('p1_color', '#2ECC71')
        )
        self.lbl_p1_name.pack(side=tk.LEFT)

        # Strategic Performance Telemetry Panel (Table 1 & PEAS)
        telemetry_frame = tk.Frame(
            right_panel,
            bg=THEME['surface_light'],
            bd=1,
            relief=tk.SOLID,
            highlightbackground=THEME['border'],
            highlightthickness=1,
            padx=10,
            pady=8
        )
        telemetry_frame.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            telemetry_frame,
            text="STRATEGIC PERFORMANCE TELEMETRY",
            font=(FONT_NAME, 8, "bold"),
            bg=THEME['surface_light'],
            fg=THEME['text_muted']
        ).pack(anchor="w", pady=(0, 4))

        row1 = tk.Frame(telemetry_frame, bg=THEME['surface_light'])
        row1.pack(fill=tk.X)
        self.lbl_steps = tk.Label(
            row1,
            text=f"Steps: 0 / {self.session.s_optimal} (Max: {self.session.s_max})",
            font=(FONT_NAME, 9, "bold"),
            bg=THEME['surface_light'],
            fg=THEME['text']
        )
        self.lbl_steps.pack(side=tk.LEFT)

        self.lbl_delay = tk.Label(
            row1,
            text="Delay: ΔS = 0",
            font=(FONT_NAME, 9, "bold"),
            bg=THEME['surface_light'],
            fg='#2ECC71'
        )
        self.lbl_delay.pack(side=tk.RIGHT)

        row2 = tk.Frame(telemetry_frame, bg=THEME['surface_light'])
        row2.pack(fill=tk.X, pady=(3, 0))
        self.lbl_resets = tk.Label(
            row2,
            text="Resets: 0 | Cum. Steps: 0 | Undos: 0",
            font=(FONT_NAME, 8),
            bg=THEME['surface_light'],
            fg=THEME['text_muted']
        )
        self.lbl_resets.pack(side=tk.LEFT)

        self.lbl_status = tk.Label(
            row2,
            text="Status: ON TRACK",
            font=(FONT_NAME, 8, "bold"),
            bg=THEME['surface_light'],
            fg=THEME['accent']
        )
        self.lbl_status.pack(side=tk.RIGHT)

        # AI Search Efficiency Telemetry Panel (Table 1, 2.1.3 & 2.2.2)
        ai_telemetry_frame = tk.Frame(
            right_panel,
            bg=THEME['surface_light'],
            bd=1,
            relief=tk.SOLID,
            highlightbackground=THEME['border'],
            highlightthickness=1,
            padx=10,
            pady=8
        )
        ai_telemetry_frame.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            ai_telemetry_frame,
            text="AI PER-TURN SEARCH METRICS",
            font=(FONT_NAME, 8, "bold"),
            bg=THEME['surface_light'],
            fg=THEME['text_muted']
        ).pack(anchor="w", pady=(0, 4))

        self.lbl_ai_action = tk.Label(
            ai_telemetry_frame,
            text="Last Action A = None | Eval: 0.00",
            font=("Consolas", 8),
            bg=THEME['surface_light'],
            fg=THEME['text']
        )
        self.lbl_ai_action.pack(anchor="w")

        self.lbl_ai_metrics = tk.Label(
            ai_telemetry_frame,
            text="Turn Latency: -- | Nodes: 0/0 | Prune: 0.0%",
            font=("Consolas", 8),
            bg=THEME['surface_light'],
            fg=THEME['text_muted']
        )
        self.lbl_ai_metrics.pack(anchor="w", pady=(2, 0))

        # Move History (Fixed Height)
        tk.Label(
            right_panel,
            text="Move History:",
            font=(FONT_NAME, 9, "bold"),
            bg=THEME['surface'],
            fg=THEME['text_muted']
        ).pack(anchor="w")

        notation_container = tk.Frame(right_panel, bg=THEME['surface_light'], height=130)
        notation_container.pack(fill=tk.X, pady=(3, 8))
        notation_container.pack_propagate(False)

        scroll = tk.Scrollbar(notation_container)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.list_notation = tk.Listbox(
            notation_container,
            bg='#1D1E26',
            fg=THEME['text'],
            font=("Consolas", 9),
            bd=0,
            yscrollcommand=scroll.set,
            selectbackground=THEME['accent']
        )
        self.list_notation.pack(fill=tk.BOTH, expand=True)
        scroll.config(command=self.list_notation.yview)

        # Action Buttons Grid
        btn_frame = tk.Frame(right_panel, bg=THEME['surface'])
        btn_frame.pack(fill=tk.X, pady=(2, 0))

        self.btn_undo = ButtonSecondary(
            btn_frame,
            text=f"Undo ({HOTKEYS['undo']['key_str']})",
            command=self._on_undo
        )
        self.btn_undo.grid(row=0, column=0, sticky="ew", padx=2, pady=2)

        btn_restart = ButtonSecondary(
            btn_frame,
            text=f"Reset Attempt ({HOTKEYS['restart']['key_str']})",
            command=self._on_reset_attempt
        )
        btn_restart.grid(row=0, column=1, sticky="ew", padx=2, pady=2)

        btn_surrender = ButtonDanger(
            btn_frame,
            text="Concede Puzzle",
            command=self._on_concede
        )
        btn_surrender.grid(row=1, column=0, sticky="ew", padx=2, pady=2)

        btn_hub = ButtonSecondary(
            btn_frame,
            text="Back to Main Menu",
            command=self._on_back_to_hub
        )
        btn_hub.grid(row=1, column=1, sticky="ew", padx=2, pady=2)

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

    def _draw_board(self):
        self.canvas.delete("all")
        size = self.state.board_size
        sq_size = 648 // size
        board_dim = size * sq_size

        self.canvas.create_rectangle(0, 0, 678, 678, fill=THEME['surface'], outline='')

        # Coordinates ONLY on BOTTOM (Letters) and RIGHT (Numbers)
        for c in range(size):
            x = c * sq_size + sq_size // 2
            y = board_dim + 15
            letter = chr(65 + c)
            self.canvas.create_text(x, y, text=letter, font=(FONT_NAME, 9, "bold"), fill=THEME['text_muted'])

        for r in range(size):
            x = board_dim + 15
            y = r * sq_size + sq_size // 2
            num_str = str(size - r)
            self.canvas.create_text(x, y, text=num_str, font=(FONT_NAME, 9, "bold"), fill=THEME['text_muted'])

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

                # CAPTURE MOVE: SQUARE HIGHLIGHT RED
                if (r, c) in self.valid_targets:
                    dest_piece = self.state.board[r][c]
                    if dest_piece is not None:
                        cell_fill = THEME['capture_square']
                        outline_color = '#B71C1C'

                self.canvas.create_rectangle(x0, y0, x1, y1, fill=cell_fill, outline=outline_color, width=outline_width)

                # CORNER OBJECTIVES: CLEAN VECTOR STAR
                if is_p1_target and self.state.board[r][c] is None:
                    draw_star(self.canvas, (x0 + x1) / 2, (y0 + y1) / 2, 14, fill='#F57F17', outline='#E65100')
                elif is_p2_target and self.state.board[r][c] is None:
                    draw_star(self.canvas, (x0 + x1) / 2, (y0 + y1) / 2, 14, fill='#C62828', outline='#8E0000')

                # EMPTY VALID MOVE: BLACK DOT
                if (r, c) in self.valid_targets and self.state.board[r][c] is None:
                    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
                    self.canvas.create_oval(cx - 7, cy - 7, cx + 7, cy + 7, fill=THEME['move_dot'], outline='')

                # DRAW PIECE
                piece = self.state.board[r][c]
                if piece:
                    self._draw_piece(x0, y0, x1, y1, piece, sq_size)

    def _draw_piece(self, x0: int, y0: int, x1: int, y1: int, piece: Piece, sq_size: int):
        color = self.config.get('p1_color', '#2ECC71') if piece.owner == 0 else self.config.get('p2_color', '#E74C3C')
        pad = max(6, sq_size // 9)

        # Subtle rim
        self.canvas.create_oval(x0 + pad + 1, y0 + pad + 2, x1 - pad + 1, y1 - pad + 2, fill='#151515', outline='')
        # Main piece circle
        self.canvas.create_oval(x0 + pad, y0 + pad, x1 - pad, y1 - pad, fill=color, outline='#FFFFFF', width=2)

        # Monogram letter ONLY
        cx = (x0 + x1) // 2
        cy = (y0 + y1) // 2
        font_size = 18 if sq_size > 90 else 14
        self.canvas.create_text(cx, cy, text=piece.p_type, font=(FONT_NAME, font_size, "bold"), fill='#FFFFFF')

    def _on_board_click(self, event):
        if not self.is_game_active or self.state.winner is not None or self.state.current_turn != 0:
            return

        size = self.state.board_size
        sq_size = 648 // size
        c = event.x // sq_size
        r = event.y // sq_size

        if not (0 <= r < size and 0 <= c < size):
            return

        if self.selected_sq:
            if (r, c) in self.valid_targets:
                start = self.selected_sq
                end = (r, c)
                self._execute_player_move(start, end)
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

        status = self.session.evaluate_status(self.state)
        if status == 'SOLVED':
            self._handle_puzzle_finish(solved=True)
            return
        elif status == 'NEUTRALIZED':
            self._handle_puzzle_finish(solved=False, reason=self.session.neutralization_reason)
            return

        # AI Defender responds
        if self.state.current_turn == 1 and self.is_game_active:
            self._trigger_ai_move()

    def _trigger_ai_move(self):
        agent_model = self.config.get('agent_model', 'proposed_d6')
        depth = self.config.get('search_depth', 6)
        weights = self.config.get('weights', DEFAULT_PROPOSAL_WEIGHTS)

        # AI move computation
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

        # Slight UI response delay (0.35s) so the human sees their move before AI strikes
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

        self.ai_timer_id = self.after(350, do_move)

    def _update_ui_state(self):
        self._draw_board()

        # Update telemetry labels
        cur = self.session.current_attempt_steps
        s_opt = self.session.s_optimal
        s_max = self.session.s_max
        self.lbl_steps.config(text=f"Steps: {cur} / {s_opt} (Max: {s_max})")

        delta = self.session.delay_margin
        if delta == 0:
            self.lbl_delay.config(text="Delay: ΔS = 0 (Optimal)", fg='#2ECC71')
        else:
            self.lbl_delay.config(text=f"Delay: ΔS = +{delta}", fg='#FFB300')

        self.lbl_resets.config(
            text=f"Resets: {self.session.resets_count} | Cum. Steps: {self.session.cumulative_steps} | Undos: {self.session.undo_count}"
        )

        status = self.session.evaluate_status(self.state)
        if status == 'SOLVED':
            self.lbl_status.config(text="Status: SOLVED", fg='#2ECC71')
        elif status == 'NEUTRALIZED':
            self.lbl_status.config(text="Status: NEUTRALIZED", fg='#E53935')
        elif status == 'DELAYED':
            self.lbl_status.config(text=f"Status: DELAYED (+{delta})", fg='#FFB300')
        else:
            self.lbl_status.config(text="Status: ON TRACK", fg=THEME['accent'])

        # AI Telemetry
        if self.session.ai_telemetry_history:
            last = self.session.ai_telemetry_history[-1]
            act = last['action']
            score = last['eval_score']
            size = self.state.board_size
            act_str = f"{chr(65 + act[0][1])}{size - act[0][0]} -> {chr(65 + act[1][1])}{size - act[1][0]}"
            self.lbl_ai_action.config(text=f"Last Action A: {act_str} | EvalScore: {score:.2f}")

            t = last['t_turn']
            prune = last['prune_efficiency']
            ngen = last['nodes_gen']
            neval = last['nodes_eval']
            self.lbl_ai_metrics.config(
                text=f"Latency Tturn: {t:.3f}s (≤2.0s) | Nodes: {neval}/{ngen} | Prune: {prune:.1f}%"
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

        # Undo both AI move and Player move
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
        self._update_ui_state()

    def _on_concede(self):
        if not self.is_game_active:
            return
        self._handle_puzzle_finish(solved=False, reason="Conceded by Player")

    def _handle_puzzle_finish(self, solved: bool, reason: str = ""):
        self.is_game_active = False

        modal = ThemedModal(self, "Puzzle Result", min_width=440)

        if solved:
            tk.Label(
                modal.body,
                text="Puzzle Successfully Solved!",
                font=(FONT_NAME, 16, "bold"),
                bg=THEME['surface'],
                fg='#2ECC71'
            ).pack(pady=(6, 2))

            summary = (
                f"You reached the target corner in {self.session.current_attempt_steps} steps "
                f"(Optimal: {self.session.s_optimal}).\n"
                f"Forced Delay Margin ΔS: {self.session.delay_margin} moves."
            )
        else:
            tk.Label(
                modal.body,
                text="Puzzle Neutralized (AI Defender Wins)",
                font=(FONT_NAME, 16, "bold"),
                bg=THEME['surface'],
                fg='#E53935'
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

        # Metrics Breakdown
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
            font=(FONT_NAME, 9),
            bg=THEME['surface_light'],
            fg=THEME['text_muted']
        ).pack(anchor="w")

        tk.Label(
            box,
            text=f"Total Resets: {self.session.resets_count} | Undos Used: {self.session.undo_count}",
            font=(FONT_NAME, 9),
            bg=THEME['surface_light'],
            fg=THEME['text_muted']
        ).pack(anchor="w")

        if self.session.ai_telemetry_history:
            avg_prune = sum(x['prune_efficiency'] for x in self.session.ai_telemetry_history) / len(self.session.ai_telemetry_history)
            avg_lat = sum(x['t_turn'] for x in self.session.ai_telemetry_history) / len(self.session.ai_telemetry_history)
            tk.Label(
                box,
                text=f"AI Search Metrics: Avg Latency: {avg_lat:.3f}s | Avg Pruning Efficiency: {avg_prune:.1f}%",
                font=(FONT_NAME, 8, "italic"),
                bg=THEME['surface_light'],
                fg=THEME['accent']
            ).pack(anchor="w", pady=(4, 0))

        def retry():
            modal.dismiss()
            self._on_reset_attempt()

        def to_hub():
            modal.dismiss()
            self._cleanup()
            self.app.show_view('menu')

        def to_config():
            modal.dismiss()
            self._cleanup()
            self.app.open_config('Puzzle')

        ButtonPrimary(modal.footer, text="Retry Puzzle", command=retry).pack(side=tk.LEFT, padx=3)
        ButtonSecondary(modal.footer, text="Select Puzzle", command=to_config).pack(side=tk.LEFT, padx=3)
        ButtonSecondary(modal.footer, text="Main Menu", command=to_hub).pack(side=tk.RIGHT, padx=3)

    def _show_rules_modal(self):
        modal = ThemedModal(self, "Puzzle Objectives & Non-Transitive Mechanics", min_width=500)
        content = (
            "1. Puzzle Objective:\n"
            f"   Navigate your piece to the opponent's star corner within S_max={self.session.s_max} moves.\n"
            f"   The optimal path takes exactly S_optimal={self.session.s_optimal} steps.\n\n"
            "2. AI Defender Role:\n"
            "   The AI agent acts as an optimal defender. If you play optimally, it aims to delay\n"
            "   you as long as possible (maximizing delay margin ΔS). If you play sub-optimally,\n"
            "   it exploits the mistake to neutralize your advance and make the goal unreachable.\n\n"
            "3. Non-Transitive Combat Hierarchy:\n"
            "   - Elephant (E) defeats Human (H)\n"
            "   - Human (H) defeats Ant (A)\n"
            "   - Ant (A) defeats Elephant (E)\n"
            "   Pieces of the same type cannot capture each other.\n\n"
            "4. Search Optimizations:\n"
            "   The agent utilizes Minimax with Alpha-Beta Pruning, suit-adapted MVV-LVA move ordering,\n"
            "   and dynamic non-transitive heuristic scoring E(s) evaluated under 2.0s per turn."
        )
        tk.Label(
            modal.body,
            text=content,
            font=(FONT_NAME, 9),
            bg=THEME['surface'],
            fg=THEME['text'],
            justify="left"
        ).pack(anchor="w", pady=4)

        ButtonPrimary(modal.footer, text="Understood", command=modal.dismiss).pack(side=tk.RIGHT)

    def _on_back_to_hub(self):
        self._cleanup()
        self.app.show_view('menu')

    def _cleanup(self):
        self._unbind_hotkeys()
        if self.ai_timer_id:
            self.after_cancel(self.ai_timer_id)
            self.ai_timer_id = None

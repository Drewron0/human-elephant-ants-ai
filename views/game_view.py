import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional, Tuple, List
from ui_theme import (
    THEME, FONT_NAME, HOTKEYS, ButtonPrimary, ButtonSecondary, ButtonDanger,
    ThemedModal, draw_star, bind_mousewheel
)
from game_logic import GameState, Piece, TARGET_CORNERS
from ai_engine import get_ai_move_with_delay
import storage
from network import NetworkManager


class GameView(tk.Frame):
    def __init__(self, parent, app, config: Dict[str, Any], saved_state: Optional[Dict[str, Any]] = None):
        super().__init__(parent, bg=THEME['bg'])
        self.app = app
        self.config = config

        self.state = GameState.from_dict(saved_state['state']) if saved_state else GameState()

        time_limit = self.config.get('time_limit', 120)
        self.time_p1 = saved_state.get('p1_time', time_limit) if saved_state else time_limit
        self.time_p2 = saved_state.get('p2_time', time_limit) if saved_state else time_limit

        self.selected_sq: Optional[Tuple[int, int]] = None
        self.valid_targets: List[Tuple[int, int]] = []
        self.last_move: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None
        self.network_mgr: Optional[NetworkManager] = None
        self.timer_id: Optional[str] = None
        self.ai_timer_id: Optional[str] = None
        self.is_game_active = True
        self._resize_job = None

        # Canvas dynamic sizing
        self.current_sq_size: int = 72

        self._build_ui()
        self._bind_hotkeys()
        self._start_timer()

        if self.config.get('mode') == 'PvP' and self.config.get('pvp_type') == 'Online':
            self._init_network()

    def _build_ui(self):
        # Top objective reminder bar
        top_bar = tk.Frame(self, bg=THEME['surface'], height=36, bd=1, relief=tk.SOLID,
                           highlightbackground=THEME['border'], highlightthickness=1)
        top_bar.pack(fill=tk.X, padx=16, pady=(10, 6))

        goal_text = "Objective: Move any piece into your opponent's star corner. P1 targets I9 (top-right), P2 targets A1 (bottom-left)."
        tk.Label(top_bar, text=goal_text, font=(FONT_NAME, 9, "bold"),
                 bg=THEME['surface'], fg=THEME['text']).pack(side=tk.LEFT, padx=16, pady=6)

        ButtonSecondary(top_bar, text="How to Play", command=self._show_rules_modal).pack(side=tk.RIGHT, padx=10, pady=4)

        # Resizable PanedWindow: Board (Left) & Controls (Right)
        self.paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg=THEME['border'], sashrelief=tk.FLAT, sashwidth=4, bd=0)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=16, pady=(6, 12))

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

        self.canvas = tk.Canvas(self.canvas_card, width=678, height=678, bg=THEME['surface'], highlightthickness=0)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_board_click)

        # Controls Panel (Right, Resizable)
        right_panel = tk.Frame(self.paned, bg=THEME['surface'], bd=0, padx=16, pady=14)
        self.paned.add(right_panel, minsize=320, stretch="never")

        # Player 2 Card
        p2_title = self.config.get('p2_name', 'Player 2')
        if self.config.get('mode') == 'PvE':
            p2_title += f" ({self.config.get('difficulty', 'Normal').capitalize()})"

        self.card_p2 = tk.Frame(right_panel, bg=THEME['surface_light'], padx=12, pady=8)
        self.card_p2.pack(fill=tk.X, pady=(0, 6))
        self.lbl_p2_name = tk.Label(self.card_p2, text=p2_title, font=(FONT_NAME, 10, "bold"),
                                    bg=THEME['surface_light'], fg=self.config.get('p2_color'))
        self.lbl_p2_name.pack(side=tk.LEFT)
        self.lbl_p2_timer = tk.Label(self.card_p2, text=self._format_time(self.time_p2),
                                     font=(FONT_NAME, 12, "bold"), bg=THEME['surface_light'], fg=THEME['text'])
        self.lbl_p2_timer.pack(side=tk.RIGHT)

        # Player 1 Card
        p1_title = self.config.get('p1_name', 'Player 1')

        self.card_p1 = tk.Frame(right_panel, bg=THEME['surface_light'], padx=12, pady=8)
        self.card_p1.pack(fill=tk.X, pady=(0, 10))
        self.lbl_p1_name = tk.Label(self.card_p1, text=p1_title, font=(FONT_NAME, 10, "bold"),
                                    bg=THEME['surface_light'], fg=self.config.get('p1_color'))
        self.lbl_p1_name.pack(side=tk.LEFT)
        self.lbl_p1_timer = tk.Label(self.card_p1, text=self._format_time(self.time_p1),
                                     font=(FONT_NAME, 12, "bold"), bg=THEME['surface_light'], fg=THEME['text'])
        self.lbl_p1_timer.pack(side=tk.RIGHT)

        # Status & Metrics
        metrics_frame = tk.Frame(right_panel, bg=THEME['surface'])
        metrics_frame.pack(fill=tk.X, pady=(0, 8))
        self.lbl_turn = tk.Label(metrics_frame, text="Turn: Player 1", font=(FONT_NAME, 11, "bold"),
                                 bg=THEME['surface'], fg=THEME['text'])
        self.lbl_turn.pack(side=tk.LEFT)
        self.lbl_stats = tk.Label(metrics_frame, text="Turns: 0 | Undos: 0", font=(FONT_NAME, 9),
                                  bg=THEME['surface'], fg=THEME['text_muted'])
        self.lbl_stats.pack(side=tk.RIGHT)

        # Move History (FIXED HEIGHT, NOT OVERSIZED)
        tk.Label(right_panel, text="Move History:", font=(FONT_NAME, 9, "bold"),
                 bg=THEME['surface'], fg=THEME['text_muted']).pack(anchor="w")

        notation_container = tk.Frame(right_panel, bg=THEME['surface_light'], height=160)
        notation_container.pack(fill=tk.X, pady=(4, 10))
        notation_container.pack_propagate(False)

        scroll = ttk.Scrollbar(notation_container)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.list_notation = tk.Listbox(
            notation_container,
            bg='#18181A',
            fg=THEME['text'],
            font=(FONT_NAME, 9),
            bd=0,
            yscrollcommand=scroll.set,
            selectbackground=THEME['accent']
        )
        self.list_notation.pack(fill=tk.BOTH, expand=True)
        scroll.config(command=self.list_notation.yview)
        bind_mousewheel(self.list_notation, self.list_notation)

        # Action Buttons Grid
        btn_frame = tk.Frame(right_panel, bg=THEME['surface'])
        btn_frame.pack(fill=tk.X, pady=(4, 0))

        self.btn_undo = ButtonSecondary(
            btn_frame,
            text=f"Undo ({HOTKEYS['undo']['key_str']})",
            command=self._on_undo
        )
        self.btn_undo.grid(row=0, column=0, sticky="ew", padx=2, pady=3)

        btn_save = ButtonSecondary(
            btn_frame,
            text=f"Save ({HOTKEYS['save']['key_str']})",
            command=self._on_save
        )
        btn_save.grid(row=0, column=1, sticky="ew", padx=2, pady=3)

        btn_restart = ButtonSecondary(
            btn_frame,
            text=f"Restart ({HOTKEYS['restart']['key_str']})",
            command=self._on_restart
        )
        btn_restart.grid(row=1, column=0, sticky="ew", padx=2, pady=3)

        btn_surrender = ButtonDanger(
            btn_frame,
            text=f"Give Up ({HOTKEYS['surrender']['key_str']})",
            command=self._on_surrender
        )
        btn_surrender.grid(row=1, column=1, sticky="ew", padx=2, pady=3)

        btn_hub = ButtonSecondary(
            btn_frame,
            text="Back to Main Menu",
            command=self._on_back_to_hub
        )
        btn_hub.grid(row=2, column=0, columnspan=2, sticky="ew", padx=2, pady=(8, 2))

        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        # Hotkeys footer
        hotkeys_bar = tk.Frame(right_panel, bg=THEME['surface'])
        hotkeys_bar.pack(fill=tk.X, pady=(10, 0))
        hk_text = " | ".join([f"{v['key_str']}: {v['label']}" for v in HOTKEYS.values()])
        tk.Label(hotkeys_bar, text=hk_text, font=(FONT_NAME, 8),
                 bg=THEME['surface'], fg=THEME['text_muted']).pack()

        self._draw_board()
        self._update_ui_state()

    def _bind_hotkeys(self):
        self.app.bind(HOTKEYS['undo']['seq'], lambda e: self._on_undo())
        self.app.bind(HOTKEYS['restart']['seq'], lambda e: self._on_restart())
        self.app.bind(HOTKEYS['surrender']['seq'], lambda e: self._on_surrender())
        self.app.bind(HOTKEYS['save']['seq'], lambda e: self._on_save())

    def _unbind_hotkeys(self):
        for h in HOTKEYS.values():
            self.app.unbind(h['seq'])

    def _format_time(self, seconds: int) -> str:
        if seconds < 0:
            return "--:--"
        m = seconds // 60
        s = seconds % 60
        return f"{m:02d}:{s:02d}"

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
        dim = max(360, min(avail_w, avail_h, 750))
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
        sq_size = self.current_sq_size
        size = self.state.board_size
        board_dim = size * sq_size
        total_dim = board_dim + 30

        self.canvas.create_rectangle(0, 0, total_dim, total_dim, fill=THEME['surface'], outline='')

        # Coordinates ONLY on BOTTOM (Letters A-I) and RIGHT (Numbers 9-1)
        for c in range(size):
            x = c * sq_size + sq_size // 2
            y = board_dim + 15
            self.canvas.create_text(x, y, text=chr(65 + c), font=(FONT_NAME, 9, "bold"), fill=THEME['text_muted'])

        for r in range(size):
            x = board_dim + 15
            y = r * sq_size + sq_size // 2
            self.canvas.create_text(x, y, text=str(size - r), font=(FONT_NAME, 9, "bold"), fill=THEME['text_muted'])

        # Draw Cells
        for r in range(size):
            for c in range(size):
                x0 = c * sq_size
                y0 = r * sq_size
                x1 = x0 + sq_size
                y1 = y0 + sq_size

                base_color = THEME['board_light'] if (r + c) % 2 == 0 else THEME['board_dark']

                is_p1_target = ((r, c) == TARGET_CORNERS[0])
                is_p2_target = ((r, c) == TARGET_CORNERS[1])

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

                # CAPTURE MOVE: ENTIRE SQUARE RED
                if (r, c) in self.valid_targets:
                    dest_piece = self.state.board[r][c]
                    if dest_piece is not None:
                        cell_fill = THEME['capture_square']
                        outline_color = '#B71C1C'

                self.canvas.create_rectangle(x0, y0, x1, y1, fill=cell_fill, outline=outline_color, width=outline_width)

                # CORNER OBJECTIVES: JUST A CLEAN VECTOR STAR, NO TEXT
                if is_p1_target and self.state.board[r][c] is None:
                    draw_star(self.canvas, (x0 + x1) / 2, (y0 + y1) / 2, 14, fill='#F57F17', outline='#E65100')
                elif is_p2_target and self.state.board[r][c] is None:
                    draw_star(self.canvas, (x0 + x1) / 2, (y0 + y1) / 2, 14, fill='#C62828', outline='#8E0000')

                # EMPTY VALID MOVE: BLACK DOT
                if (r, c) in self.valid_targets and self.state.board[r][c] is None:
                    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
                    self.canvas.create_oval(cx - 7, cy - 7, cx + 7, cy + 7, fill=THEME['move_dot'], outline='')

                # DRAW PIECE (LETTER ONLY, NO WORDS)
                piece = self.state.board[r][c]
                if piece:
                    self._draw_piece(x0, y0, x1, y1, piece)

    def _draw_piece(self, x0: int, y0: int, x1: int, y1: int, piece: Piece):
        color = self.config.get('p1_color', '#2ECC71') if piece.owner == 0 else self.config.get('p2_color', '#E74C3C')
        sq_size = x1 - x0
        pad = max(4, int(sq_size * 0.11))
        # Subtle rim
        self.canvas.create_oval(x0 + pad + 1, y0 + pad + 2, x1 - pad + 1, y1 - pad + 2, fill='#151515', outline='')
        # Main piece circle
        self.canvas.create_oval(x0 + pad, y0 + pad, x1 - pad, y1 - pad, fill=color, outline='#FFFFFF', width=2)

        # Monogram letter ONLY (NO FULL WORDS)
        cx = (x0 + x1) // 2
        cy = (y0 + y1) // 2
        font_sz = max(10, int(sq_size * 0.22))
        self.canvas.create_text(cx, cy, text=piece.p_type, font=(FONT_NAME, font_sz, "bold"), fill='#FFFFFF')

    def _on_board_click(self, event):
        if not self.is_game_active or self.state.winner is not None:
            return

        if self.config.get('mode') == 'PvE' and self.state.current_turn == 1:
            return

        if self.config.get('mode') == 'PvP' and self.config.get('pvp_type') == 'Online':
            my_role = 0 if self.config.get('is_host') else 1
            if self.state.current_turn != my_role:
                return

        sq_size = self.current_sq_size
        c = event.x // sq_size
        r = event.y // sq_size

        if not (0 <= r < 9 and 0 <= c < 9):
            return

        if self.selected_sq:
            if (r, c) in self.valid_targets:
                start = self.selected_sq
                end = (r, c)
                self._execute_move(start, end)
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

    def _execute_move(self, start: Tuple[int, int], end: Tuple[int, int], from_network: bool = False):
        move = self.state.make_move(start, end)
        if not move:
            return

        self.last_move = (start, end)
        self.selected_sq = None
        self.valid_targets = []

        if self.network_mgr and not from_network:
            self.network_mgr.send_move(start, end)

        self._update_ui_state()
        self.update_idletasks()

        if self.state.winner is not None:
            self._handle_game_over(self.state.winner, "Target Corner Reached")
            return

        # PVE: AI delay calculation so AI clock ticks and human can win via time
        if self.config.get('mode') == 'PvE' and self.state.current_turn == 1 and self.is_game_active:
            def _schedule_pve_ai():
                if not self.is_game_active or self.state.current_turn != 1:
                    return
                diff = self.config.get('difficulty', 'normal')
                ai_move, delay_sec = get_ai_move_with_delay(self.state, diff)
                if ai_move and self.is_game_active:
                    delay_ms = int(delay_sec * 1000)
                    self.ai_timer_id = self.after(delay_ms, lambda: self._execute_move(ai_move[0], ai_move[1]))

            self.after(40, _schedule_pve_ai)

    def _update_ui_state(self):
        self._draw_board()

        p_name = self.config.get('p1_name') if self.state.current_turn == 0 else self.config.get('p2_name')
        color = self.config.get('p1_color') if self.state.current_turn == 0 else self.config.get('p2_color')

        self.lbl_turn.config(text=f"Turn: {p_name}", fg=color)

        if self.config.get('mode') == 'PvP':
            self.lbl_stats.config(
                text=f"Turns: {self.state.total_turns} | P1 Undos: {self.state.undos_p1} | P2 Undos: {self.state.undos_p2}"
            )
        else:
            self.lbl_stats.config(
                text=f"Turns: {self.state.total_turns} | Undos: {self.state.undos_p1}"
            )

        self.list_notation.delete(0, tk.END)
        for i, n in enumerate(self.state.notation):
            prefix = f"{i + 1}. " if i % 2 == 0 else "   "
            self.list_notation.insert(tk.END, f"{prefix}{n}")
        self.list_notation.yview(tk.END)

        if self.state.current_turn == 0:
            self.card_p1.config(highlightbackground=THEME['accent'], highlightthickness=2)
            self.card_p2.config(highlightthickness=0)
        else:
            self.card_p2.config(highlightbackground=THEME['accent'], highlightthickness=2)
            self.card_p1.config(highlightthickness=0)

        if not self.config.get('undo_enabled') or not self.state.history:
            self.btn_undo.config(state=tk.DISABLED, fg=THEME['text_muted'])
        else:
            self.btn_undo.config(state=tk.NORMAL, fg=THEME['text'])

    def _start_timer(self):
        if self.config.get('time_limit', 120) <= 0:
            return

        def tick():
            if not self.is_game_active or self.state.winner is not None:
                return

            if self.state.current_turn == 0:
                self.time_p1 -= 1
                self.lbl_p1_timer.config(text=self._format_time(self.time_p1))
                if self.time_p1 <= 0:
                    self._handle_game_over(1, "Player 1 Clock Expired")
                    return
            else:
                self.time_p2 -= 1
                self.lbl_p2_timer.config(text=self._format_time(self.time_p2))
                if self.time_p2 <= 0:
                    self._handle_game_over(0, "Player 2 Clock Expired")
                    return

            self.timer_id = self.after(1000, tick)

        self.timer_id = self.after(1000, tick)

    def _stop_timer(self):
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None
        if self.ai_timer_id:
            self.after_cancel(self.ai_timer_id)
            self.ai_timer_id = None

    def _handle_game_over(self, winner: int, reason: str):
        self.is_game_active = False
        self.state.winner = winner
        self._stop_timer()

        winner_name = self.config.get('p1_name') if winner == 0 else self.config.get('p2_name')
        win_color = self.config.get('p1_color') if winner == 0 else self.config.get('p2_color')

        # Record Score into Storage
        if self.config.get('mode') == 'PvE':
            if winner == 0:
                storage.save_pve_score(
                    username=self.config.get('p1_name', 'Player'),
                    turns=self.state.total_turns,
                    time_left=max(0, self.time_p1),
                    undos=self.state.undos_p1,
                    difficulty=self.config.get('difficulty', 'normal')
                )
        else:
            storage.update_pvp_stats(self.config.get('p1_name'), won=(winner == 0), undos=self.state.undos_p1)
            storage.update_pvp_stats(self.config.get('p2_name'), won=(winner == 1), undos=self.state.undos_p2)

        # Game Over Modal (Self-sizing, never cutoff)
        modal = ThemedModal(self, "Match Finished", min_width=440)

        tk.Label(
            modal.body,
            text=f"{winner_name} Wins",
            font=(FONT_NAME, 16, "bold"),
            bg=THEME['surface'],
            fg=win_color
        ).pack(pady=(6, 4))

        tk.Label(
            modal.body,
            text=f"Victory Method: {reason}",
            font=(FONT_NAME, 10),
            bg=THEME['surface'],
            fg=THEME['text_muted']
        ).pack(pady=(0, 10))

        info_box = tk.Frame(modal.body, bg=THEME['surface_light'], padx=14, pady=8)
        info_box.pack(fill=tk.X, pady=4)

        if self.config.get('mode') == 'PvP':
            stats_str = f"Turns: {self.state.total_turns} | P1 Undos: {self.state.undos_p1} | P2 Undos: {self.state.undos_p2}"
        else:
            stats_str = f"Turns: {self.state.total_turns} | Undos: {self.state.undos_p1}"

        tk.Label(info_box, text=stats_str, font=(FONT_NAME, 9), bg=THEME['surface_light'], fg=THEME['text']).pack()

        if self.config.get('time_limit', 120) > 0:
            rem = self.time_p1 if winner == 0 else self.time_p2
            tk.Label(info_box, text=f"Time Remaining: {self._format_time(rem)}", font=(FONT_NAME, 9),
                     bg=THEME['surface_light'], fg=THEME['text_muted']).pack(pady=(2, 0))

        def on_rematch():
            modal.dismiss()
            self._restart_match()

        def on_hub():
            modal.dismiss()
            self._cleanup()
            self.app.show_view('menu')

        def on_lb():
            modal.dismiss()
            self._cleanup()
            self.app.show_view('leaderboard')

        ButtonPrimary(modal.footer, text="Play Again", command=on_rematch).pack(side=tk.LEFT, padx=3)
        ButtonSecondary(modal.footer, text="Leaderboard", command=on_lb).pack(side=tk.LEFT, padx=3)
        ButtonSecondary(modal.footer, text="Back to Hub", command=on_hub).pack(side=tk.RIGHT, padx=3)

    def _on_undo(self):
        if not self.config.get('undo_enabled') or not self.is_game_active:
            return

        if self.config.get('mode') == 'PvP' and self.config.get('pvp_type') == 'Online':
            return

        active_player = self.state.current_turn

        if self.config.get('mode') == 'PvE':
            # Revert both AI and player moves, attribute undo to player (0)
            if self.state.undo(player_idx=0):
                self.state.undo(player_idx=0)
        else:
            # Local PvP: attribute undo to active player
            self.state.undo(player_idx=active_player)

        self.selected_sq = None
        self.valid_targets = []
        self._update_ui_state()

    def _on_restart(self):
        if not self.is_game_active:
            self._restart_match()
            return

        modal = ThemedModal(self, "Restart Match Confirmation", min_width=380)
        tk.Label(
            modal.body,
            text="Are you sure you want to restart the match? Current progress will be reset.",
            font=(FONT_NAME, 10),
            bg=THEME['surface'],
            fg=THEME['text'],
            wraplength=340,
            justify="left"
        ).pack(pady=10)

        def confirm():
            modal.dismiss()
            if self.network_mgr:
                self.network_mgr.send_restart()
            self._restart_match()

        ButtonSecondary(modal.footer, text="Cancel", command=modal.dismiss).pack(side=tk.LEFT)
        ButtonDanger(modal.footer, text="Restart Match", command=confirm).pack(side=tk.RIGHT)

    def _restart_match(self):
        self._stop_timer()
        self.state = GameState()
        self.selected_sq = None
        self.valid_targets = []
        self.last_move = None
        self.is_game_active = True
        limit = self.config.get('time_limit', 120)
        self.time_p1 = limit
        self.time_p2 = limit
        self._update_ui_state()
        self._start_timer()

    def _on_surrender(self):
        if not self.is_game_active or self.state.winner is not None:
            return

        modal = ThemedModal(self, "Surrender Match Confirmation", min_width=380)
        tk.Label(
            modal.body,
            text="Are you sure you want to surrender? Victory will be awarded to your opponent.",
            font=(FONT_NAME, 10),
            bg=THEME['surface'],
            fg=THEME['text'],
            wraplength=340,
            justify="left"
        ).pack(pady=10)

        def confirm():
            modal.dismiss()
            if self.network_mgr:
                self.network_mgr.send_surrender()
            winner = 1 - self.state.current_turn
            self._handle_game_over(winner, "Surrender")

        ButtonSecondary(modal.footer, text="Cancel", command=modal.dismiss).pack(side=tk.LEFT)
        ButtonDanger(modal.footer, text="Surrender", command=confirm).pack(side=tk.RIGHT)

    def _on_save(self):
        if self.config.get('mode') != 'PvE':
            modal = ThemedModal(self, "Save Game", min_width=360)
            tk.Label(
                modal.body,
                text="Mid-game save slots are currently available for PvE matches.",
                font=(FONT_NAME, 10),
                bg=THEME['surface'],
                fg=THEME['text'],
                wraplength=320
            ).pack(pady=12)
            ButtonPrimary(modal.footer, text="Close", command=modal.dismiss).pack(side=tk.RIGHT)
            return

        modal = ThemedModal(self, "Save to Game Slot", min_width=460)
        tk.Label(
            modal.body,
            text="Select a slot to save your current PvE match:",
            font=(FONT_NAME, 9),
            bg=THEME['surface'],
            fg=THEME['text_muted']
        ).pack(anchor="w", pady=(0, 6))

        slots_box = tk.Frame(modal.body, bg=THEME['surface'])
        slots_box.pack(fill=tk.BOTH, expand=True)

        existing_saves = storage.get_saved_slots()

        for slot_num in range(1, 6):
            slot_id = f"slot_{slot_num}"
            save_info = existing_saves.get(slot_id)
            row = tk.Frame(slots_box, bg=THEME['surface_light'], padx=8, pady=4)
            row.pack(fill=tk.X, pady=2)

            if save_info:
                label_txt = f"Slot {slot_num}: Turns: {save_info.get('state', {}).get('total_turns', 0)} ({save_info.get('timestamp')})"
            else:
                label_txt = f"Slot {slot_num}: [Empty Slot]"

            tk.Label(row, text=label_txt, font=(FONT_NAME, 9), bg=THEME['surface_light'], fg=THEME['text']).pack(side=tk.LEFT)

            def make_save_cmd(s_id=slot_id, s_num=slot_num):
                payload = {
                    'mode': self.config.get('mode'),
                    'config': self.config,
                    'p1_time': self.time_p1,
                    'p2_time': self.time_p2,
                    'state': self.state.to_dict()
                }
                storage.save_game_slot(s_id, f"Slot {s_num}", payload)
                modal.dismiss()

            ButtonPrimary(row, text="Save Here", command=make_save_cmd, pady=2, padx=8).pack(side=tk.RIGHT)

        ButtonSecondary(modal.footer, text="Close", command=modal.dismiss).pack(side=tk.RIGHT)

    def _on_back_to_hub(self):
        if self.is_game_active and self.state.winner is None and self.state.total_turns > 0:
            modal = ThemedModal(self, "Return to Hub Confirmation", min_width=380)
            tk.Label(
                modal.body,
                text="Match is still in progress. Unsaved progress will be lost. Return to menu?",
                font=(FONT_NAME, 10),
                bg=THEME['surface'],
                fg=THEME['text'],
                wraplength=340
            ).pack(pady=10)

            def confirm():
                modal.dismiss()
                self._cleanup()
                self.app.show_view('menu')

            ButtonSecondary(modal.footer, text="Stay in Match", command=modal.dismiss).pack(side=tk.LEFT)
            ButtonDanger(modal.footer, text="Return to Hub", command=confirm).pack(side=tk.RIGHT)
        else:
            self._cleanup()
            self.app.show_view('menu')

    def _show_rules_modal(self):
        modal = ThemedModal(self, "Rules and Movement", min_width=480)
        content = (
            "1. Objective:\n"
            "   Move any piece into your opponent's star corner.\n"
            "   Player 1 reaches I9 (top-right corner).\n"
            "   Player 2 reaches A1 (bottom-left corner).\n\n"
            "2. Combat Hierarchy:\n"
            "   Human beats Ant.\n"
            "   Ant beats Elephant.\n"
            "   Elephant beats Human.\n"
            "   Matching pieces cannot capture each other.\n"
            "   Friendly pieces cannot be captured.\n\n"
            "3. Movement:\n"
            "   Every piece moves 1 square in any of the 8 directions.\n"
            "   Valid moves to empty squares appear as black dots.\n"
            "   Valid capture moves highlight the target square red."
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

    def _init_network(self):
        is_host = self.config.get('is_host', True)
        ip = self.config.get('ip', '127.0.0.1')
        port = self.config.get('port', 5555)
        local_name = self.config.get('p1_name', 'Player 1')

        self.network_mgr = NetworkManager(
            is_host=is_host,
            ip=ip,
            port=port,
            local_name=local_name,
            on_connect=None,
            on_opponent_name=lambda name: self.after(0, lambda: self._on_opponent_named(name)),
            on_move=lambda s, e: self.after(0, lambda: self._execute_move((s[0], s[1]), (e[0], e[1]), from_network=True)),
            on_restart=lambda: self.after(0, self._restart_match),
            on_surrender=lambda: self.after(0, lambda: self._handle_game_over(0 if not is_host else 1, "Opponent Surrendered")),
            on_disconnect=None
        )
        self.network_mgr.start()

    def _on_opponent_named(self, name: str):
        self.config['p2_name'] = name
        self.lbl_p2_name.config(text=name)

    def _cleanup(self):
        if self._resize_job is not None:
            try:
                self.after_cancel(self._resize_job)
            except Exception:
                pass
            self._resize_job = None
        self._stop_timer()
        self._unbind_hotkeys()
        if self.network_mgr:
            self.network_mgr.close()
            self.network_mgr = None

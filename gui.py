import tkinter as tk
from tkinter import messagebox
from game_logic import GameState, BEATS
from ai_engine import get_ai_move
import storage

COLORS = {
    'bg': '#1E1E1E',
    'board_light': '#E0E0E0',
    'board_dark': '#BDBDBD',
    'p1': '#4CAF50',
    'p2': '#F44336',
    'highlight': '#FFEB3B',
    'text': '#FFFFFF'
}

class GameApp(tk.Tk):
    def __init__(self, mode='PvE'):
        super().__init__()
        self.title("9x9 Tactical: Human-Elephant-Ant")
        self.geometry("900x700")
        self.configure(bg=COLORS['bg'])
        self.mode = mode
        
        self.state = GameState()
        self.selected_sq = None
        self.valid_targets = []
        
        self.time_p1 = 120
        self.time_p2 = 120
        
        self._build_ui()
        self._bind_hotkeys()
        self._update_timer()

    def _build_ui(self):
        self.canvas = tk.Canvas(self, width=540, height=540, bg=COLORS['bg'], highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, padx=20, pady=20)
        self.canvas.bind("<Button-1>", self._on_click)

        right_panel = tk.Frame(self, bg=COLORS['bg'])
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=20, pady=20)

        self.lbl_turn = tk.Label(right_panel, text="Turn: P1", font=("Arial", 16, "bold"), bg=COLORS['bg'], fg=COLORS['text'])
        self.lbl_turn.pack(pady=10)

        self.lbl_p2_time = tk.Label(right_panel, text="P2 Time: 2:00", font=("Arial", 14), bg=COLORS['bg'], fg=COLORS['p2'])
        self.lbl_p2_time.pack()

        self.lbl_p1_time = tk.Label(right_panel, text="P1 Time: 2:00", font=("Arial", 14), bg=COLORS['bg'], fg=COLORS['p1'])
        self.lbl_p1_time.pack(pady=10)
        
        self.lbl_stats = tk.Label(right_panel, text="Turns: 0 | Undos: 0", font=("Arial", 12), bg=COLORS['bg'], fg=COLORS['text'])
        self.lbl_stats.pack(pady=10)

        self.list_notation = tk.Listbox(right_panel, bg='#2C2C2C', fg=COLORS['text'], font=("Consolas", 10))
        self.list_notation.pack(fill=tk.BOTH, expand=True, pady=10)

        self._draw_board()

    def _bind_hotkeys(self):
        self.bind("<Control-z>", lambda e: self._undo())
        self.bind("<Control-r>", lambda e: self._restart())
        self.bind("<Control-e>", lambda e: self._surrender())

    def _draw_board(self):
        self.canvas.delete("all")
        sq_size = 60
        for r in range(9):
            for c in range(9):
                x0, y0 = c * sq_size, r * sq_size
                x1, y1 = x0 + sq_size, y0 + sq_size
                color = COLORS['board_light'] if (r + c) % 2 == 0 else COLORS['board_dark']
                
                if self.selected_sq == (r, c):
                    color = COLORS['highlight']
                elif (r, c) in self.valid_targets:
                    color = '#81D4FA'

                self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline='#757575')

                piece = self.state.board[r][c]
                if piece:
                    pc = COLORS['p1'] if piece.owner == 0 else COLORS['p2']
                    self.canvas.create_oval(x0+10, y0+10, x1-10, y1-10, fill=pc, outline='')
                    self.canvas.create_text(x0+30, y0+30, text=piece.p_type, font=("Arial", 16, "bold"), fill='#FFFFFF')

    def _on_click(self, event):
        if self.state.winner is not None: return
        if self.mode == 'PvE' and self.state.current_turn == 1: return

        sq_size = 60
        c, r = event.x // sq_size, event.y // sq_size
        if not (0 <= r < 9 and 0 <= c < 9): return

        if self.selected_sq:
            if (r, c) in self.valid_targets:
                self.state.make_move(self.selected_sq, (r, c))
                self.selected_sq = None
                self.valid_targets = []
                self._update_ui()
                self._check_win()
                if self.mode == 'PvE' and self.state.winner is None:
                    self.after(500, self._ai_turn)
            else:
                self.selected_sq = None
                self.valid_targets = []
                self._draw_board()
        else:
            p = self.state.board[r][c]
            if p and p.owner == self.state.current_turn:
                self.selected_sq = (r, c)
                self.valid_targets = [m[1] for m in self.state.get_valid_moves(self.state.current_turn) if m[0] == (r, c)]
                self._draw_board()

    def _ai_turn(self):
        move = get_ai_move(self.state)
        if move:
            self.state.make_move(move[0], move[1])
            self._update_ui()
            self._check_win()

    def _update_ui(self):
        self._draw_board()
        self.lbl_turn.config(text=f"Turn: P{self.state.current_turn + 1}")
        self.lbl_stats.config(text=f"Turns: {self.state.total_turns} | Undos: {self.state.undos}")
        self.list_notation.delete(0, tk.END)
        for n in self.state.notation: self.list_notation.insert(tk.END, n)
        self.list_notation.yview(tk.END)

    def _update_timer(self):
        if self.state.winner is None:
            if self.state.current_turn == 0:
                self.time_p1 -= 1
            else:
                self.time_p2 -= 1

            if self.time_p1 <= 0: self._end_game(1, "Timeout")
            if self.time_p2 <= 0: self._end_game(0, "Timeout")

            self.lbl_p1_time.config(text=f"P1 Time: {self.time_p1//60}:{self.time_p1%60:02d}")
            self.lbl_p2_time.config(text=f"P2 Time: {self.time_p2//60}:{self.time_p2%60:02d}")
            self.after(1000, self._update_timer)

    def _check_win(self):
        if self.state.winner is not None:
            self._end_game(self.state.winner, "Target Reached")

    def _end_game(self, winner, reason):
        self.state.winner = winner
        msg = f"Player {winner + 1} wins by {reason}!"
        messagebox.showinfo("Game Over", msg)
        if self.mode == 'PvE' and winner == 0:
            storage.save_pve_score("Player", self.state.total_turns, self.time_p1, self.state.undos)

    def _undo(self):
        if self.state.undo():
            if self.mode == 'PvE': self.state.undo()
            self._update_ui()

    def _restart(self):
        if messagebox.askyesno("Restart", "Restart game?"):
            self.state = GameState()
            self.time_p1 = 120
            self.time_p2 = 120
            self._update_ui()

    def _surrender(self):
        if messagebox.askyesno("Surrender", "Are you sure you want to surrender?"):
            self._end_game(1 - self.state.current_turn, "Surrender")
            self.destroy()
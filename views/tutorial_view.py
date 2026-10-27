import tkinter as tk
from tkinter import ttk
from ui_theme import THEME, FONT_NAME, ButtonSecondary


class TutorialView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=THEME['bg'])
        self.app = app
        self._build_ui()

    def _build_ui(self):
        container = tk.Frame(self, bg=THEME['bg'])
        container.pack(fill=tk.BOTH, expand=True, padx=40, pady=20)

        # Fixed Top Header with Back to Hub Button
        header = tk.Frame(container, bg=THEME['bg'])
        header.pack(fill=tk.X, pady=(0, 14))

        tk.Label(
            header,
            text="Game Rules and How to Play",
            font=(FONT_NAME, 18, "bold"),
            bg=THEME['bg'],
            fg=THEME['text']
        ).pack(side=tk.LEFT)

        ButtonSecondary(header, text="Back to Main Menu", command=lambda: self.app.show_view('menu')).pack(side=tk.RIGHT)

        # Scrollable content area so it never clips or overflows
        scroll_card = tk.Frame(
            container,
            bg=THEME['surface'],
            bd=1,
            relief=tk.SOLID,
            highlightbackground=THEME['border'],
            highlightthickness=1
        )
        scroll_card.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(scroll_card, bg=THEME['surface'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_card, orient=tk.VERTICAL, command=canvas.yview)
        content_frame = tk.Frame(canvas, bg=THEME['surface'], padx=24, pady=18)

        content_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=content_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        guide_text = (
            "1. Primary Victory Condition:\n"
            "   Move any of your pieces into your opponent's designated star corner.\n"
            "   Player 1 (starts at bottom): Target corner is I9 (top-right).\n"
            "   Player 2 (starts at top): Target corner is A1 (bottom-left).\n"
            "   Reaching the target corner results in immediate victory.\n\n"
            "2. Combat Hierarchy (Cyclic Dominance):\n"
            "   Human (H) captures Ant (A).\n"
            "   Ant (A) captures Elephant (E).\n"
            "   Elephant (E) captures Human (H).\n"
            "   Matching pieces (for example H vs H) cannot capture each other and movement is blocked.\n"
            "   Friendly fire is illegal: You can never capture or land on your own pieces.\n\n"
            "3. Movement Mechanics:\n"
            "   Every piece moves exactly 1 square per turn in any of the 8 adjacent directions (orthogonal or diagonal).\n"
            "   Valid moves to empty squares are displayed as black dots.\n"
            "   Valid capture moves highlight the target square completely red.\n\n"
            "4. Puzzle Mode: Optimal Defender (Proposal Specification):\n"
            "   The game begins in a pre-configured puzzle state with an optimal solution of N moves (e.g. 10 moves).\n"
            "   The AI acts as an Optimal Defender: if you play optimally, it maximizes delay (delay margin);\n"
            "   if you play sub-optimally, it exploits the mistake to neutralize the advance within S_max = 3 * S_optimal.\n"
            "   The AI utilizes Minimax with Alpha-Beta Pruning, suit-adapted MVV-LVA move ordering, and a\n"
            "   Dynamic Non-Transitive Evaluation Function E(s) = wm*M(s) + wc*C(s) + wp*P(s) + wt*T(s) evaluated under 2.0s.\n\n"
            "5. Simulation & Benchmark Lab:\n"
            "   Run simulated matches comparing Proposed Method (Alpha-Beta d=6), Baseline 2 (Vanilla Minimax d=3),\n"
            "   and Baseline 1 (Random Agent) against scripted players (Shortest-Path, Sub-Optimal, Random).\n"
            "   Records real-time turn latency, pruning efficiency, delay margin, and neutralization rate.\n\n"
            "6. Match Clock and Hotkeys:\n"
            "   Each side has an active countdown timer during their turn (PvE/PvP).\n"
            "   Ctrl + Z: Undo move\n"
            "   Ctrl + R: Restart / Reset puzzle attempt (requires confirmation)\n"
            "   Ctrl + E: Surrender / Concede match\n"
            "   Ctrl + S: Save mid-game state to a save slot"
        )

        tk.Label(
            content_frame,
            text=guide_text,
            font=(FONT_NAME, 10),
            bg=THEME['surface'],
            fg=THEME['text'],
            justify="left",
            wraplength=760
        ).pack(anchor="w")

        # Fixed Bottom Footer with second Back to Hub Button
        footer = tk.Frame(container, bg=THEME['bg'])
        footer.pack(fill=tk.X, pady=(12, 0))

        ButtonSecondary(footer, text="Back to Main Menu", command=lambda: self.app.show_view('menu')).pack(side=tk.RIGHT)

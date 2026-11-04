import tkinter as tk
from tkinter import ttk
from ui_theme import THEME, FONT_NAME, ButtonSecondary, CaptureLegend, bind_mousewheel


class TutorialView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=THEME["bg"])
        self.app = app
        self._build_ui()

    def _build_ui(self):
        container = tk.Frame(self, bg=THEME["bg"])
        container.pack(fill=tk.BOTH, expand=True, padx=40, pady=20)

        # Fixed Top Header with Back to Hub Button
        header = tk.Frame(container, bg=THEME["bg"])
        header.pack(fill=tk.X, pady=(0, 14))

        tk.Label(
            header,
            text="Game Rules and How to Play",
            font=(FONT_NAME, 18, "bold"),
            bg=THEME["bg"],
            fg=THEME["text"],
        ).pack(side=tk.LEFT)

        ButtonSecondary(
            header, text="Back to Main Menu", command=lambda: self.app.show_view("menu")
        ).pack(side=tk.RIGHT)

        # Scrollable content area so it never clips or overflows
        scroll_card = tk.Frame(
            container,
            bg=THEME["surface"],
            bd=0,
            relief=tk.FLAT,
            highlightbackground=THEME["border"],
            highlightthickness=1,
        )
        scroll_card.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(scroll_card, bg=THEME["surface"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_card, orient=tk.VERTICAL, command=canvas.yview)
        content_frame = tk.Frame(canvas, bg=THEME["surface"], padx=24, pady=18)

        content_window = canvas.create_window((0, 0), window=content_frame, anchor="nw")
        canvas.bind('<Configure>', lambda event: canvas.itemconfigure(content_window, width=event.width))
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        CaptureLegend(content_frame).pack(fill=tk.X, pady=(0, 24))

        guide_text = (
            "Victory condition\n"
            "   Move any of your pieces into your opponent's designated star corner.\n"
            "   Player 1 (starts at bottom): Target corner is I9 (top-right).\n"
            "   Player 2 (starts at top): Target corner is A1 (bottom-left).\n"
            "   Reaching the target corner results in immediate victory.\n\n"
            "   Friendly fire is illegal: You can never capture or land on your own pieces.\n\n"
            "Movement\n"
            "   Every piece moves exactly 1 square per turn in any of the 8 adjacent directions (orthogonal or diagonal).\n"
            "   Valid moves to empty squares are displayed as black dots.\n"
            "   Valid capture moves highlight the target square completely red.\n\n"
            "Tactical Puzzle Mode:\n"
            "   Stage authors enter the minimum steps themselves when creating or editing a stage.\n"
            "   Saving and loading keep that number; no algorithm calculates or verifies it.\n"
            "   The move limit is three times the entered minimum.\n"
            "   After a loss, Undo or Reset remains available; each successful undo action is counted.\n"
            "   The defender tries to delay your corner arrival and exploit mistakes before the move limit.\n"
            "   Exact Defender analyzes its replies separately and does not change the entered minimum.\n"
            "   If analysis is incomplete, it pauses: Retry, Undo or Reset. It never substitutes a guessed move.\n"
            "   Practice baseline models deliberately use weaker, approximate or random decisions.\n\n"
            "Simulation & benchmark lab\n"
            "   Compare optimized search at d=6 and d=3, Baseline 2 (Vanilla Minimax d=3),\n"
            "   and Baseline 1 (Random Agent) against scripted players (Shortest-Path, Sub-Optimal, Random).\n"
            "   Default: 1,000 games per combination on certified random 11x11 10-step race puzzles.\n"
            "   Records turn latency, actual depth, timeouts, pruning efficiency, delay margin, and neutralization rate.\n\n"
            "Keyboard shortcuts\n"
            "   Ctrl + Z undoes a move; Ctrl + R restarts a puzzle.\n"
            "   Ctrl + E: Surrender / Concede match\n"
            "   Ctrl + S: Save mid-game state to a save slot"
        )

        guide = tk.Label(
            content_frame,
            text=guide_text,
            font=(FONT_NAME, 11),
            bg=THEME["surface"],
            fg=THEME["text"],
            justify="left",
            wraplength=760,
        )
        guide.pack(anchor="w")
        content_frame.bind('<Configure>', lambda event: (
            canvas.configure(scrollregion=canvas.bbox('all')),
            guide.configure(wraplength=max(1, min(760, event.width - 48)))))
        bind_mousewheel(scroll_card, canvas)


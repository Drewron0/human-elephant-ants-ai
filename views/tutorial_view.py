import tkinter as tk
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
        scrollbar = tk.Scrollbar(scroll_card, orient=tk.VERTICAL, command=canvas.yview)
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
            "4. Match Clock and Hotkeys:\n"
            "   Each side has an active countdown timer during their turn.\n"
            "   Ctrl + Z: Undo move\n"
            "   Ctrl + R: Restart match (requires confirmation)\n"
            "   Ctrl + E: Surrender match (requires confirmation)\n"
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

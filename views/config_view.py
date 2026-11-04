import tkinter as tk
from tkinter import ttk
from typing import Dict, Any
from ui_theme import THEME, FONT_NAME, COLOR_PALETTES, ButtonPrimary, ButtonSecondary, SegmentedControl
import storage


class ConfigView(tk.Frame):
    def __init__(self, parent, app, mode: str):
        super().__init__(parent, bg=THEME['bg'])
        self.app = app
        self.mode = 'PvE'
        self._build_ui()

    def _build_ui(self):
        container = tk.Frame(self, bg=THEME['bg'])
        container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        mode_title = "Player vs AI (Practice)"

        tk.Label(
            container,
            text=f"Match Setup: {mode_title}",
            font=(FONT_NAME, 18, "bold"),
            bg=THEME['bg'],
            fg=THEME['text']
        ).pack(pady=(0, 16))

        card = tk.Frame(
            container,
            bg=THEME['surface'],
            bd=1,
            relief=tk.SOLID,
            highlightbackground=THEME['border'],
            highlightthickness=1,
            padx=28,
            pady=18
        )
        card.pack()

        row = 0
        lbl_font = (FONT_NAME, 9, "bold")
        entry_font = (FONT_NAME, 9)

        # Primary Player Profile
        tk.Label(card, text="Player 1 Name:", font=lbl_font, bg=THEME['surface'], fg=THEME['text']).grid(row=row, column=0, sticky="w", pady=6)
        p1_box = tk.Frame(card, bg=THEME['surface'])
        p1_box.grid(row=row, column=1, sticky="w", padx=(12, 0), pady=6)

        self.last_name = storage.get_last_username()
        self.var_p1_name = tk.StringVar(value=self.last_name)
        profiles = storage.get_recent_profiles()

        self.cb_p1_name = ttk.Combobox(p1_box, textvariable=self.var_p1_name, values=profiles, width=16, font=entry_font)
        self.cb_p1_name.pack(side=tk.LEFT)

        # ================= PVE MODE SETTINGS =================
        row += 1
        tk.Label(card, text="AI Engine Model:", font=lbl_font, bg=THEME['surface'], fg=THEME['text']).grid(row=row, column=0, sticky="w", pady=6)
        self.var_pve_engine = tk.StringVar(value="Standard Minimax")
        cb_pve_engine = ttk.Combobox(
            card,
            textvariable=self.var_pve_engine,
            values=["Standard Minimax", "Optimized: Non-Transitive Alpha-Beta (d=6)"],
            state="readonly",
            width=28,
            font=entry_font
        )
        cb_pve_engine.grid(row=row, column=1, sticky="w", padx=(12, 0), pady=6)

        row += 1
        tk.Label(card, text="AI Difficulty:", font=lbl_font, bg=THEME['surface'], fg=THEME['text']).grid(row=row, column=0, sticky="w", pady=6)
        self.seg_difficulty = SegmentedControl(
            card,
            options=[("Easy", "Easy"), ("Normal", "Normal"), ("Hard", "Hard")],
            default_val="Normal"
        )
        self.seg_difficulty.grid(row=row, column=1, sticky="w", padx=(12, 0), pady=6)

        # Time Limit
        row += 1
        tk.Label(card, text="Timer Per Side:", font=lbl_font, bg=THEME['surface'], fg=THEME['text']).grid(row=row, column=0, sticky="w", pady=6)
        self.var_time = tk.StringVar(value="2 Minutes")
        cb_time = ttk.Combobox(
            card,
            textvariable=self.var_time,
            values=["1 Minute", "2 Minutes", "3 Minutes", "5 Minutes", "10 Minutes", "No Timer"],
            state="readonly",
            width=16,
            font=entry_font
        )
        cb_time.grid(row=row, column=1, sticky="w", padx=(12, 0), pady=6)

        # Allow Undo
        row += 1
        tk.Label(card, text="Allow Undo:", font=lbl_font, bg=THEME['surface'], fg=THEME['text']).grid(row=row, column=0, sticky="w", pady=6)
        self.var_undo = tk.BooleanVar(value=True)
        chk_undo = tk.Checkbutton(
            card,
            text="Enable Undo (Ctrl+Z)",
            variable=self.var_undo,
            font=entry_font,
            bg=THEME['surface'],
            fg=THEME['text'],
            selectcolor=THEME['surface_light'],
            activebackground=THEME['surface'],
            activeforeground=THEME['text']
        )
        chk_undo.grid(row=row, column=1, sticky="w", padx=(12, 0), pady=6)

        # Primary Player Color
        row += 1
        tk.Label(card, text="Player 1 Color:", font=lbl_font, bg=THEME['surface'], fg=THEME['text']).grid(row=row, column=0, sticky="w", pady=6)
        self.var_p1_color = tk.StringVar(value="Emerald Green")
        cb_p1 = ttk.Combobox(card, textvariable=self.var_p1_color, values=list(COLOR_PALETTES.keys()), state="readonly", width=16, font=entry_font)
        cb_p1.grid(row=row, column=1, sticky="w", padx=(12, 0), pady=6)

        # Opponent Color
        row += 1
        p2_lbl = "AI Color:"
        tk.Label(card, text=p2_lbl, font=lbl_font, bg=THEME['surface'], fg=THEME['text']).grid(row=row, column=0, sticky="w", pady=6)
        self.var_p2_color = tk.StringVar(value="Ruby Red")
        cb_p2 = ttk.Combobox(card, textvariable=self.var_p2_color, values=list(COLOR_PALETTES.keys()), state="readonly", width=16, font=entry_font)
        cb_p2.grid(row=row, column=1, sticky="w", padx=(12, 0), pady=6)

        # Bottom Buttons
        row += 1
        btn_box = tk.Frame(card, bg=THEME['surface'])
        btn_box.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(16, 4))

        ButtonSecondary(btn_box, text="Back to Hub", command=lambda: self.app.show_view('menu')).pack(side=tk.LEFT)
        ButtonPrimary(btn_box, text="Start Game", command=self._start_game).pack(side=tk.RIGHT)

    def _start_game(self):
        name = self.var_p1_name.get().strip() or "Player 1"
        storage.save_last_username(name)
        difficulty = ('proposed' if "Non-Transitive" in self.var_pve_engine.get()
                      else self.seg_difficulty.get().lower())
        time_map = {"1 Minute": 60, "2 Minutes": 120, "3 Minutes": 180,
                    "5 Minutes": 300, "10 Minutes": 600, "No Timer": -1}
        self.app.start_game(dict(
            mode='PvE', p1_name=name, p2_name='AI Opponent', difficulty=difficulty,
            time_limit=time_map.get(self.var_time.get(), 120),
            undo_enabled=self.var_undo.get(),
            p1_color=COLOR_PALETTES.get(self.var_p1_color.get(), '#2ECC71'),
            p2_color=COLOR_PALETTES.get(self.var_p2_color.get(), '#E74C3C')))

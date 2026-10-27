import tkinter as tk
from tkinter import ttk
from typing import Dict, Any
from ui_theme import THEME, FONT_NAME, COLOR_PALETTES, ButtonPrimary, ButtonSecondary, SegmentedControl
import storage


class ConfigView(tk.Frame):
    def __init__(self, parent, app, mode: str):
        super().__init__(parent, bg=THEME['bg'])
        self.app = app
        self.mode = mode
        self._build_ui()

    def _build_ui(self):
        container = tk.Frame(self, bg=THEME['bg'])
        container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        if self.mode == 'PvE':
            mode_title = "Player vs AI (PvE)"
        else:
            mode_title = "Player vs Player (PvP)"

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

        # Player 1 Profile
        tk.Label(card, text="Player 1 Name:", font=lbl_font, bg=THEME['surface'], fg=THEME['text']).grid(row=row, column=0, sticky="w", pady=6)
        p1_box = tk.Frame(card, bg=THEME['surface'])
        p1_box.grid(row=row, column=1, sticky="w", padx=(12, 0), pady=6)

        self.last_name = storage.get_last_username()
        self.var_p1_name = tk.StringVar(value=self.last_name)
        profiles = storage.get_recent_profiles()

        self.cb_p1_name = ttk.Combobox(p1_box, textvariable=self.var_p1_name, values=profiles, width=16, font=entry_font)
        self.cb_p1_name.pack(side=tk.LEFT)

        self.var_p1_guest = tk.BooleanVar(value=False)
        chk_p1_guest = tk.Checkbutton(
            p1_box,
            text="Play as Guest",
            variable=self.var_p1_guest,
            font=(FONT_NAME, 8),
            bg=THEME['surface'],
            fg=THEME['text_muted'],
            selectcolor=THEME['surface_light'],
            activebackground=THEME['surface'],
            activeforeground=THEME['text'],
            command=self._toggle_p1_guest
        )
        chk_p1_guest.pack(side=tk.LEFT, padx=(8, 0))

        if self.mode == 'PvP':
            # ================= PVP MODE SETTINGS =================
            row += 1
            self.lbl_p2_title = tk.Label(card, text="Player 2 Name:", font=lbl_font, bg=THEME['surface'], fg=THEME['text'])
            self.lbl_p2_title.grid(row=row, column=0, sticky="w", pady=6)

            self.p2_box = tk.Frame(card, bg=THEME['surface'])
            self.p2_box.grid(row=row, column=1, sticky="w", padx=(12, 0), pady=6)

            self.var_p2_name = tk.StringVar(value="Player 2")
            self.ent_p2_name = tk.Entry(
                self.p2_box,
                textvariable=self.var_p2_name,
                font=entry_font,
                bg=THEME['surface_light'],
                fg=THEME['text'],
                insertbackground=THEME['text'],
                width=18,
                bd=0,
                relief=tk.FLAT
            )
            self.ent_p2_name.pack(side=tk.LEFT)

            self.var_p2_guest = tk.BooleanVar(value=False)
            self.chk_p2_guest = tk.Checkbutton(
                self.p2_box,
                text="Play as Guest",
                variable=self.var_p2_guest,
                font=(FONT_NAME, 8),
                bg=THEME['surface'],
                fg=THEME['text_muted'],
                selectcolor=THEME['surface_light'],
                activebackground=THEME['surface'],
                activeforeground=THEME['text'],
                command=self._toggle_p2_guest
            )
            self.chk_p2_guest.pack(side=tk.LEFT, padx=(8, 0))

            # Mode Selection: Local vs Online
            row += 1
            tk.Label(card, text="PvP Mode:", font=lbl_font, bg=THEME['surface'], fg=THEME['text']).grid(row=row, column=0, sticky="w", pady=6)
            self.seg_pvp = SegmentedControl(
                card,
                options=[("Local Device", "Local"), ("Online Network", "Online")],
                default_val="Local",
                on_change=self._on_pvp_type_change
            )
            self.seg_pvp.grid(row=row, column=1, sticky="w", padx=(12, 0), pady=6)

            # Online Network Settings (Conditional)
            row += 1
            self.net_box = tk.Frame(card, bg=THEME['surface_light'], padx=8, pady=6)
            self.seg_net_role = SegmentedControl(
                self.net_box,
                options=[("Host Game", "Host"), ("Join Game", "Join")],
                default_val="Host"
            )
            self.seg_net_role.pack(side=tk.LEFT, padx=(0, 6))

            tk.Label(self.net_box, text="IP:", font=lbl_font, bg=THEME['surface_light'], fg=THEME['text']).pack(side=tk.LEFT, padx=(4, 2))
            self.ent_ip = tk.Entry(self.net_box, width=12, font=entry_font, bg=THEME['surface'], fg=THEME['text'], insertbackground=THEME['text'])
            self.ent_ip.insert(0, "127.0.0.1")
            self.ent_ip.pack(side=tk.LEFT, padx=2)

            tk.Label(self.net_box, text="Port:", font=lbl_font, bg=THEME['surface_light'], fg=THEME['text']).pack(side=tk.LEFT, padx=(4, 2))
            self.ent_port = tk.Entry(self.net_box, width=6, font=entry_font, bg=THEME['surface'], fg=THEME['text'], insertbackground=THEME['text'])
            self.ent_port.insert(0, "5555")
            self.ent_port.pack(side=tk.LEFT, padx=2)

            self.net_box.grid(row=row, column=0, columnspan=2, sticky="ew", pady=6)
            self.net_box.grid_remove()

        else:
            # ================= PVE MODE SETTINGS =================
            row += 1
            tk.Label(card, text="AI Engine Model:", font=lbl_font, bg=THEME['surface'], fg=THEME['text']).grid(row=row, column=0, sticky="w", pady=6)
            self.var_pve_engine = tk.StringVar(value="Standard Minimax")
            cb_pve_engine = ttk.Combobox(
                card,
                textvariable=self.var_pve_engine,
                values=["Standard Minimax", "Proposal: Non-Transitive Alpha-Beta (d=6)"],
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

        # Player 1 Color
        row += 1
        tk.Label(card, text="Player 1 Color:", font=lbl_font, bg=THEME['surface'], fg=THEME['text']).grid(row=row, column=0, sticky="w", pady=6)
        self.var_p1_color = tk.StringVar(value="Emerald Green")
        cb_p1 = ttk.Combobox(card, textvariable=self.var_p1_color, values=list(COLOR_PALETTES.keys()), state="readonly", width=16, font=entry_font)
        cb_p1.grid(row=row, column=1, sticky="w", padx=(12, 0), pady=6)

        # Player 2 / AI Color
        row += 1
        p2_lbl = "AI Color:" if self.mode == 'PvE' else "Player 2 Color:"
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

    def _toggle_p1_guest(self):
        if self.var_p1_guest.get():
            self.var_p1_name.set(storage.generate_guest_name())
        else:
            self.var_p1_name.set(self.last_name or "Player 1")

    def _toggle_p2_guest(self):
        if hasattr(self, 'var_p2_guest') and self.var_p2_guest.get():
            self.var_p2_name.set(storage.generate_guest_name())
        elif hasattr(self, 'var_p2_name'):
            self.var_p2_name.set("Player 2")

    def _on_pvp_type_change(self, val: str):
        if val == "Online":
            self.net_box.grid()
            self.lbl_p2_title.config(text="Opponent Status:")
            self.ent_p2_name.config(state=tk.DISABLED)
            self.var_p2_name.set("Remote Opponent (Wait for connect)")
            self.chk_p2_guest.pack_forget()
        else:
            self.net_box.grid_remove()
            self.lbl_p2_title.config(text="Player 2 Name:")
            self.ent_p2_name.config(state=tk.NORMAL)
            self.var_p2_name.set("Player 2")
            self.chk_p2_guest.pack(side=tk.LEFT, padx=(8, 0))

    def _start_game(self):
        p1_val = self.var_p1_name.get().strip() or "Player 1"
        is_guest_1 = self.var_p1_guest.get() or p1_val.lower().startswith("guest")

        if not is_guest_1:
            storage.save_last_username(p1_val)

        p1_color = COLOR_PALETTES.get(self.var_p1_color.get(), '#2ECC71')
        p2_color = COLOR_PALETTES.get(self.var_p2_color.get(), '#E74C3C')

        # PvP or PvE setup
        time_map = {
            "1 Minute": 60,
            "2 Minutes": 120,
            "3 Minutes": 180,
            "5 Minutes": 300,
            "10 Minutes": 600,
            "No Timer": -1
        }

        p2_val = "AI Opponent"
        is_guest_2 = False
        pvp_type = "Local"
        is_host = True
        ip = "127.0.0.1"
        port = 5555

        if self.mode == 'PvP':
            pvp_type = self.seg_pvp.get()
            if pvp_type == 'Local':
                p2_val = self.var_p2_name.get().strip() or "Player 2"
                is_guest_2 = self.var_p2_guest.get() or p2_val.lower().startswith("guest")
            else:
                is_host = (self.seg_net_role.get() == "Host")
                ip = self.ent_ip.get().strip() or "127.0.0.1"
                try:
                    port = int(self.ent_port.get().strip() or 5555)
                except ValueError:
                    port = 5555
                p2_val = "Connecting..."

        diff = 'normal'
        if self.mode == 'PvE':
            if hasattr(self, 'var_pve_engine') and "Non-Transitive" in self.var_pve_engine.get():
                diff = 'proposed'
            else:
                diff = self.seg_difficulty.get().lower()

        config = {
            'mode': self.mode,
            'p1_name': p1_val,
            'is_guest_1': is_guest_1,
            'p2_name': p2_val,
            'is_guest_2': is_guest_2,
            'difficulty': diff,
            'pvp_type': pvp_type,
            'is_host': is_host,
            'ip': ip,
            'port': port,
            'time_limit': time_map.get(self.var_time.get(), 120),
            'undo_enabled': self.var_undo.get(),
            'p1_color': p1_color,
            'p2_color': p2_color
        }

        self.app.start_game(config)

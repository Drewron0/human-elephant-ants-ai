import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional, Tuple, List
import copy
from game_logic import GameState, Piece, BEATS, TARGET_CORNERS, START_CORNERS, PIECE_NAMES
from ai_engine import get_ai_move
import storage
from network import NetworkManager

# Dynamic Hotkey Configuration
HOTKEYS = {
    'undo': {'seq': '<Control-z>', 'key_str': 'Ctrl+Z', 'label': 'Undo Move'},
    'restart': {'seq': '<Control-r>', 'key_str': 'Ctrl+R', 'label': 'Restart Match'},
    'surrender': {'seq': '<Control-e>', 'key_str': 'Ctrl+E', 'label': 'Surrender / Forfeit'},
    'save': {'seq': '<Control-s>', 'key_str': 'Ctrl+S', 'label': 'Save Game Slot'},
}

THEME = {
    'bg': '#18191A',
    'surface': '#242526',
    'surface_light': '#3A3B3C',
    'border': '#3E4042',
    'text': '#E4E6EB',
    'text_secondary': '#B0B3B8',
    'accent': '#2D88FF',
    'accent_hover': '#1877F2',
    'danger': '#E41E3F',
    'board_light': '#EFEFEF',
    'board_dark': '#B0BEC5',
    'board_grid': '#78909C',
    'target_p1_bg': '#FFF9C4',
    'target_p1_border': '#FBC02D',
    'target_p2_bg': '#FFCDD2',
    'target_p2_border': '#E53935',
    'highlight_select': '#FFE082',
    'highlight_move': '#80CBC4',
    'highlight_capture': '#FF8A80',
    'highlight_last': '#CFD8DC'
}

COLOR_PALETTES = {
    'Emerald Green': '#2ECC71',
    'Sapphire Blue': '#3498DB',
    'Ruby Red': '#E74C3C',
    'Amethyst Purple': '#9B59B6',
    'Amber Orange': '#E67E22',
    'Turquoise Cyan': '#1ABC9C'
}


class ModalOverlay(tk.Frame):
    """An in-window modal dialog that prevents spawning extra OS windows."""
    def __init__(self, parent, title: str, width: int = 440, height: int = 270):
        super().__init__(parent, bg='#000000')
        self.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.backdrop = tk.Frame(self, bg='#121212')
        self.backdrop.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.card = tk.Frame(self.backdrop, bg=THEME['surface'], bd=2, relief=tk.SOLID,
                             highlightbackground=THEME['border'], highlightthickness=1)
        self.card.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=width, height=height)

        header = tk.Frame(self.card, bg=THEME['surface'])
        header.pack(fill=tk.X, padx=16, pady=(16, 8))
        tk.Label(header, text=title, font=("Segoe UI", 13, "bold"),
                 bg=THEME['surface'], fg=THEME['text']).pack(side=tk.LEFT)

        self.body = tk.Frame(self.card, bg=THEME['surface'])
        self.body.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        self.footer = tk.Frame(self.card, bg=THEME['surface'])
        self.footer.pack(fill=tk.X, padx=16, pady=(8, 16))

    def dismiss(self):
        self.destroy()


class MainMenuView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=THEME['bg'])
        self.app = app
        self._build_ui()

    def _build_ui(self):
        container = tk.Frame(self, bg=THEME['bg'])
        container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Title Box
        title_box = tk.Frame(container, bg=THEME['bg'])
        title_box.pack(pady=(0, 24))
        tk.Label(title_box, text="HUMAN • ELEPHANT • ANT",
                 font=("Segoe UI", 24, "bold"), bg=THEME['bg'], fg=THEME['text']).pack()
        tk.Label(title_box, text="9x9 Tactical Board Game",
                 font=("Segoe UI", 12), bg=THEME['bg'], fg=THEME['text_secondary']).pack(pady=(4, 0))

        # Action Buttons Card
        card = tk.Frame(container, bg=THEME['surface'], bd=1, relief=tk.SOLID,
                        highlightbackground=THEME['border'], highlightthickness=1, padx=30, pady=24)
        card.pack()

        btn_style = {
            'font': ("Segoe UI", 11, "bold"),
            'relief': tk.FLAT,
            'bd': 0,
            'cursor': 'hand2',
            'height': 2,
            'width': 26
        }

        # PvE Button
        btn_pve = tk.Button(card, text="Play vs AI (PvE)", bg=THEME['accent'], fg='#FFFFFF',
                            activebackground=THEME['accent_hover'], activeforeground='#FFFFFF',
                            command=lambda: self.app.open_config('PvE'), **btn_style)
        btn_pve.pack(pady=6)

        # PvP Button
        btn_pvp = tk.Button(card, text="Play vs Player (PvP)", bg=THEME['surface_light'], fg=THEME['text'],
                            activebackground=THEME['border'], activeforeground=THEME['text'],
                            command=lambda: self.app.open_config('PvP'), **btn_style)
        btn_pvp.pack(pady=6)

        # Load Game Button
        btn_load = tk.Button(card, text="Load Saved Game", bg=THEME['surface_light'], fg=THEME['text'],
                             activebackground=THEME['border'], activeforeground=THEME['text'],
                             command=lambda: self.app.show_view('saves'), **btn_style)
        btn_load.pack(pady=6)

        # Leaderboard Button
        btn_lb = tk.Button(card, text="Multi-Category Leaderboard", bg=THEME['surface_light'], fg=THEME['text'],
                           activebackground=THEME['border'], activeforeground=THEME['text'],
                           command=lambda: self.app.show_view('leaderboard'), **btn_style)
        btn_lb.pack(pady=6)

        # Tutorial Button
        btn_tut = tk.Button(card, text="Rules & Tutorial", bg=THEME['surface_light'], fg=THEME['text'],
                            activebackground=THEME['border'], activeforeground=THEME['text'],
                            command=lambda: self.app.show_view('tutorial'), **btn_style)
        btn_tut.pack(pady=6)

        # Exit Button
        btn_exit = tk.Button(card, text="Quit Game", bg='#3A2024', fg='#FF6B6B',
                             activebackground=THEME['danger'], activeforeground='#FFFFFF',
                             command=self.app.destroy, **btn_style)
        btn_exit.pack(pady=(12, 4))


class ConfigView(tk.Frame):
    def __init__(self, parent, app, mode: str):
        super().__init__(parent, bg=THEME['bg'])
        self.app = app
        self.mode = mode
        self._build_ui()

    def _build_ui(self):
        container = tk.Frame(self, bg=THEME['bg'])
        container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        title = f"Match Setup — {'Player vs AI (PvE)' if self.mode == 'PvE' else 'Player vs Player (PvP)'}"
        tk.Label(container, text=title, font=("Segoe UI", 20, "bold"),
                 bg=THEME['bg'], fg=THEME['text']).pack(pady=(0, 16))

        card = tk.Frame(container, bg=THEME['surface'], bd=1, relief=tk.SOLID,
                        highlightbackground=THEME['border'], highlightthickness=1, padx=32, pady=20)
        card.pack()

        row = 0
        lbl_font = ("Segoe UI", 10, "bold")
        entry_font = ("Segoe UI", 10)

        # Player 1 Profile / Name & Guest Option
        tk.Label(card, text="Player 1 Profile:", font=lbl_font, bg=THEME['surface'], fg=THEME['text']).grid(row=row, column=0, sticky="w", pady=8)
        
        p1_profile_frame = tk.Frame(card, bg=THEME['surface'])
        p1_profile_frame.grid(row=row, column=1, padx=(12, 0), sticky="ew", pady=8)

        self.last_name = storage.get_last_username()
        self.var_p1_name = tk.StringVar(value=self.last_name)
        profiles = storage.get_recent_profiles()

        self.cb_p1_name = ttk.Combobox(p1_profile_frame, textvariable=self.var_p1_name, values=profiles, width=15, font=entry_font)
        self.cb_p1_name.pack(side=tk.LEFT)

        self.var_is_guest = tk.BooleanVar(value=False)
        self.btn_guest_toggle = tk.Checkbutton(p1_profile_frame, text="Play as Guest", variable=self.var_is_guest,
                                               font=("Segoe UI", 9), bg=THEME['surface'], fg=THEME['text_secondary'],
                                               selectcolor=THEME['surface_light'], activebackground=THEME['surface'],
                                               command=self._on_guest_toggle)
        self.btn_guest_toggle.pack(side=tk.LEFT, padx=(8, 0))

        # Player 2 Name (PvP only)
        if self.mode == 'PvP':
            row += 1
            tk.Label(card, text="Player 2 Profile:", font=lbl_font, bg=THEME['surface'], fg=THEME['text']).grid(row=row, column=0, sticky="w", pady=8)
            p2_profile_frame = tk.Frame(card, bg=THEME['surface'])
            p2_profile_frame.grid(row=row, column=1, padx=(12, 0), sticky="ew", pady=8)
            self.ent_p2_name = tk.Entry(p2_profile_frame, font=entry_font, bg=THEME['surface_light'], fg=THEME['text'],
                                        insertbackground=THEME['text'], width=17, bd=0, relief=tk.FLAT)
            self.ent_p2_name.insert(0, "Player 2")
            self.ent_p2_name.pack(side=tk.LEFT)

        # PvE Difficulty or PvP Mode
        row += 1
        if self.mode == 'PvE':
            tk.Label(card, text="AI Difficulty:", font=lbl_font, bg=THEME['surface'], fg=THEME['text']).grid(row=row, column=0, sticky="w", pady=8)
            self.var_difficulty = tk.StringVar(value="Normal")
            diff_frame = tk.Frame(card, bg=THEME['surface'])
            for d in ["Easy", "Normal", "Hard"]:
                tk.Radiobutton(diff_frame, text=d, variable=self.var_difficulty, value=d,
                               font=entry_font, bg=THEME['surface'], fg=THEME['text'],
                               selectcolor=THEME['surface_light'], activebackground=THEME['surface']).pack(side=tk.LEFT, padx=6)
            diff_frame.grid(row=row, column=1, padx=(12, 0), sticky="w", pady=8)
        else:
            tk.Label(card, text="PvP Mode:", font=lbl_font, bg=THEME['surface'], fg=THEME['text']).grid(row=row, column=0, sticky="w", pady=8)
            self.var_pvp_type = tk.StringVar(value="Local")
            pvp_frame = tk.Frame(card, bg=THEME['surface'])
            tk.Radiobutton(pvp_frame, text="Local (Same PC)", variable=self.var_pvp_type, value="Local",
                           font=entry_font, bg=THEME['surface'], fg=THEME['text'],
                           selectcolor=THEME['surface_light'], activebackground=THEME['surface'],
                           command=self._toggle_net_fields).pack(side=tk.LEFT, padx=6)
            tk.Radiobutton(pvp_frame, text="Online Network", variable=self.var_pvp_type, value="Online",
                           font=entry_font, bg=THEME['surface'], fg=THEME['text'],
                           selectcolor=THEME['surface_light'], activebackground=THEME['surface'],
                           command=self._toggle_net_fields).pack(side=tk.LEFT, padx=6)
            pvp_frame.grid(row=row, column=1, padx=(12, 0), sticky="w", pady=8)

        # Network Fields (Conditional)
        row += 1
        self.net_frame = tk.Frame(card, bg=THEME['surface'])
        self.var_net_role = tk.StringVar(value="Host")
        tk.Radiobutton(self.net_frame, text="Host", variable=self.var_net_role, value="Host",
                       font=entry_font, bg=THEME['surface'], fg=THEME['text'], selectcolor=THEME['surface_light']).pack(side=tk.LEFT, padx=4)
        tk.Radiobutton(self.net_frame, text="Join", variable=self.var_net_role, value="Join",
                       font=entry_font, bg=THEME['surface'], fg=THEME['text'], selectcolor=THEME['surface_light']).pack(side=tk.LEFT, padx=4)
        tk.Label(self.net_frame, text="IP:", font=lbl_font, bg=THEME['surface'], fg=THEME['text']).pack(side=tk.LEFT, padx=(10, 2))
        self.ent_ip = tk.Entry(self.net_frame, width=12, font=entry_font, bg=THEME['surface_light'], fg=THEME['text'])
        self.ent_ip.insert(0, "127.0.0.1")
        self.ent_ip.pack(side=tk.LEFT, padx=2)
        tk.Label(self.net_frame, text="Port:", font=lbl_font, bg=THEME['surface'], fg=THEME['text']).pack(side=tk.LEFT, padx=(6, 2))
        self.ent_port = tk.Entry(self.net_frame, width=6, font=entry_font, bg=THEME['surface_light'], fg=THEME['text'])
        self.ent_port.insert(0, "5555")
        self.ent_port.pack(side=tk.LEFT, padx=2)
        self.net_frame.grid(row=row, column=0, columnspan=2, pady=6, sticky="w")
        self.net_frame.grid_remove()

        # Timer Limit
        row += 1
        tk.Label(card, text="Timer Per Side:", font=lbl_font, bg=THEME['surface'], fg=THEME['text']).grid(row=row, column=0, sticky="w", pady=8)
        self.var_time = tk.StringVar(value="2 Minutes")
        cb_time = ttk.Combobox(card, textvariable=self.var_time, values=["1 Minute", "2 Minutes", "3 Minutes", "5 Minutes", "10 Minutes", "No Timer"],
                               state="readonly", width=16)
        cb_time.grid(row=row, column=1, padx=(12, 0), sticky="w", pady=8)

        # Allow Undo
        row += 1
        tk.Label(card, text="Allow Undo:", font=lbl_font, bg=THEME['surface'], fg=THEME['text']).grid(row=row, column=0, sticky="w", pady=8)
        self.var_undo = tk.BooleanVar(value=True)
        chk_undo = tk.Checkbutton(card, text="Enable Undo (Ctrl+Z)", variable=self.var_undo, font=entry_font,
                                  bg=THEME['surface'], fg=THEME['text'], selectcolor=THEME['surface_light'],
                                  activebackground=THEME['surface'])
        chk_undo.grid(row=row, column=1, padx=(12, 0), sticky="w", pady=8)

        # Player 1 Piece Color
        row += 1
        tk.Label(card, text="Player 1 Color:", font=lbl_font, bg=THEME['surface'], fg=THEME['text']).grid(row=row, column=0, sticky="w", pady=8)
        self.var_p1_color = tk.StringVar(value="Emerald Green")
        cb_p1 = ttk.Combobox(card, textvariable=self.var_p1_color, values=list(COLOR_PALETTES.keys()), state="readonly", width=16)
        cb_p1.grid(row=row, column=1, padx=(12, 0), sticky="w", pady=8)

        # Player 2 / AI Piece Color
        row += 1
        p2_label = "AI Color:" if self.mode == 'PvE' else "Player 2 Color:"
        tk.Label(card, text=p2_label, font=lbl_font, bg=THEME['surface'], fg=THEME['text']).grid(row=row, column=0, sticky="w", pady=8)
        self.var_p2_color = tk.StringVar(value="Ruby Red")
        cb_p2 = ttk.Combobox(card, textvariable=self.var_p2_color, values=list(COLOR_PALETTES.keys()), state="readonly", width=16)
        cb_p2.grid(row=row, column=1, padx=(12, 0), sticky="w", pady=8)

        # Buttons
        row += 1
        btn_box = tk.Frame(card, bg=THEME['surface'])
        btn_box.grid(row=row, column=0, columnspan=2, pady=(20, 8), sticky="ew")

        tk.Button(btn_box, text="Back to Hub", bg=THEME['surface_light'], fg=THEME['text'],
                  font=("Segoe UI", 10, "bold"), bd=0, relief=tk.FLAT, cursor="hand2", padx=16, pady=8,
                  command=lambda: self.app.show_view('menu')).pack(side=tk.LEFT)

        tk.Button(btn_box, text="Start Game", bg=THEME['accent'], fg='#FFFFFF',
                  font=("Segoe UI", 10, "bold"), bd=0, relief=tk.FLAT, cursor="hand2", padx=24, pady=8,
                  command=self._start_game).pack(side=tk.RIGHT)

    def _on_guest_toggle(self):
        if self.var_is_guest.get():
            guest_name = storage.generate_guest_name()
            self.var_p1_name.set(guest_name)
        else:
            self.var_p1_name.set(self.last_name or "Player 1")

    def _toggle_net_fields(self):
        if hasattr(self, 'var_pvp_type') and self.var_pvp_type.get() == "Online":
            self.net_frame.grid()
        else:
            self.net_frame.grid_remove()

    def _start_game(self):
        time_map = {
            "1 Minute": 60,
            "2 Minutes": 120,
            "3 Minutes": 180,
            "5 Minutes": 300,
            "10 Minutes": 600,
            "No Timer": -1
        }

        p1_val = self.var_p1_name.get().strip() or "Player 1"
        is_guest = self.var_is_guest.get() or p1_val.lower().startswith("guest")

        if not is_guest:
            storage.save_last_username(p1_val)

        p2_val = "AI Opponent"
        if self.mode == 'PvP':
            p2_val = self.ent_p2_name.get().strip() if hasattr(self, 'ent_p2_name') else "Player 2"

        config = {
            'mode': self.mode,
            'p1_name': p1_val,
            'is_guest': is_guest,
            'p2_name': p2_val,
            'difficulty': self.var_difficulty.get().lower() if self.mode == 'PvE' else 'normal',
            'pvp_type': self.var_pvp_type.get() if self.mode == 'PvP' else 'Local',
            'is_host': (self.var_net_role.get() == 'Host') if self.mode == 'PvP' else True,
            'ip': self.ent_ip.get().strip() if self.mode == 'PvP' else '127.0.0.1',
            'port': int(self.ent_port.get().strip() or 5555) if self.mode == 'PvP' else 5555,
            'time_limit': time_map.get(self.var_time.get(), 120),
            'undo_enabled': self.var_undo.get(),
            'p1_color': COLOR_PALETTES.get(self.var_p1_color.get(), '#2ECC71'),
            'p2_color': COLOR_PALETTES.get(self.var_p2_color.get(), '#E74C3C')
        }

        self.app.start_game(config)


class GameView(tk.Frame):
    def __init__(self, parent, app, config: Dict[str, Any], saved_state: Optional[Dict[str, Any]] = None):
        super().__init__(parent, bg=THEME['bg'])
        self.app = app
        self.config = config

        self.state = GameState.from_dict(saved_state['state']) if saved_state else GameState()

        # Timers
        time_limit = self.config.get('time_limit', 120)
        self.time_p1 = saved_state.get('p1_time', time_limit) if saved_state else time_limit
        self.time_p2 = saved_state.get('p2_time', time_limit) if saved_state else time_limit

        self.selected_sq: Optional[Tuple[int, int]] = None
        self.valid_targets: List[Tuple[int, int]] = []
        self.last_move: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None
        self.network_mgr: Optional[NetworkManager] = None
        self.timer_id: Optional[str] = None
        self.is_game_active = True

        self._build_ui()
        self._bind_hotkeys()
        self._start_timer()

        if self.config.get('mode') == 'PvP' and self.config.get('pvp_type') == 'Online':
            self._init_network()

    def _build_ui(self):
        # Top banner with Objective & Quick Help
        top_bar = tk.Frame(self, bg=THEME['surface'], height=42, bd=1, relief=tk.SOLID,
                           highlightbackground=THEME['border'], highlightthickness=1)
        top_bar.pack(fill=tk.X, padx=16, pady=(12, 6))

        goal_text = (f"🎯 OBJECTIVE: Move any piece into opponent's target corner! "
                     f"P1 Target: (I, 9) Top-Right | P2 Target: (A, 1) Bottom-Left")
        tk.Label(top_bar, text=goal_text, font=("Segoe UI", 10, "bold"),
                 bg=THEME['surface'], fg='#FFD54F').pack(side=tk.LEFT, padx=16, pady=8)

        tk.Button(top_bar, text="📖 Rules & Combat", font=("Segoe UI", 9, "bold"),
                  bg=THEME['surface_light'], fg=THEME['text'], bd=0, relief=tk.FLAT, cursor="hand2", padx=10,
                  command=self._show_rules_modal).pack(side=tk.RIGHT, padx=12, pady=6)

        # Main Layout (Board on left, Controls on right)
        main_layout = tk.Frame(self, bg=THEME['bg'])
        main_layout.pack(fill=tk.BOTH, expand=True, padx=16, pady=(6, 12))

        # Canvas with coordinate headers
        canvas_card = tk.Frame(main_layout, bg=THEME['surface'], bd=1, relief=tk.SOLID,
                               highlightbackground=THEME['border'], highlightthickness=1, padx=12, pady=12)
        canvas_card.pack(side=tk.LEFT, fill=tk.BOTH)

        # Total canvas 590x590 (Margin 25px around 540x540 board)
        self.canvas = tk.Canvas(canvas_card, width=590, height=590, bg=THEME['bg'], highlightthickness=0)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_board_click)

        # Right Control Panel
        right_panel = tk.Frame(main_layout, bg=THEME['surface'], bd=1, relief=tk.SOLID,
                               highlightbackground=THEME['border'], highlightthickness=1, padx=16, pady=16)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(16, 0))

        # Player Info Cards
        p2_title = self.config.get('p2_name', 'Player 2')
        if self.config.get('mode') == 'PvE':
            p2_title += f" ({self.config.get('difficulty', 'Normal').capitalize()})"

        self.card_p2 = tk.Frame(right_panel, bg=THEME['surface_light'], padx=12, pady=8, bd=1, relief=tk.FLAT)
        self.card_p2.pack(fill=tk.X, pady=(0, 6))
        self.lbl_p2_name = tk.Label(self.card_p2, text=f"● {p2_title}", font=("Segoe UI", 11, "bold"),
                                    bg=THEME['surface_light'], fg=self.config.get('p2_color'))
        self.lbl_p2_name.pack(side=tk.LEFT)
        self.lbl_p2_timer = tk.Label(self.card_p2, text=self._format_time(self.time_p2),
                                     font=("Segoe UI", 12, "bold"), bg=THEME['surface_light'], fg=THEME['text'])
        self.lbl_p2_timer.pack(side=tk.RIGHT)

        p1_title = self.config.get('p1_name', 'Player 1')
        if self.config.get('is_guest'):
            p1_title += " [Guest]"

        self.card_p1 = tk.Frame(right_panel, bg=THEME['surface_light'], padx=12, pady=8, bd=1, relief=tk.FLAT)
        self.card_p1.pack(fill=tk.X, pady=(0, 10))
        self.lbl_p1_name = tk.Label(self.card_p1, text=f"● {p1_title}",
                                    font=("Segoe UI", 11, "bold"), bg=THEME['surface_light'], fg=self.config.get('p1_color'))
        self.lbl_p1_name.pack(side=tk.LEFT)
        self.lbl_p1_timer = tk.Label(self.card_p1, text=self._format_time(self.time_p1),
                                     font=("Segoe UI", 12, "bold"), bg=THEME['surface_light'], fg=THEME['text'])
        self.lbl_p1_timer.pack(side=tk.RIGHT)

        # Status & Metrics
        metrics_frame = tk.Frame(right_panel, bg=THEME['surface'])
        metrics_frame.pack(fill=tk.X, pady=(0, 8))
        self.lbl_turn = tk.Label(metrics_frame, text="Current Turn: P1", font=("Segoe UI", 12, "bold"),
                                 bg=THEME['surface'], fg=THEME['text'])
        self.lbl_turn.pack(side=tk.LEFT)
        self.lbl_stats = tk.Label(metrics_frame, text="Turns: 0 | Undos: 0", font=("Segoe UI", 10),
                                  bg=THEME['surface'], fg=THEME['text_secondary'])
        self.lbl_stats.pack(side=tk.RIGHT)

        # Notation Log
        tk.Label(right_panel, text="Move History (Algebraic Notation):", font=("Segoe UI", 9, "bold"),
                 bg=THEME['surface'], fg=THEME['text_secondary']).pack(anchor="w")
        notation_box = tk.Frame(right_panel, bg=THEME['surface_light'])
        notation_box.pack(fill=tk.BOTH, expand=True, pady=(4, 10))

        scroll = tk.Scrollbar(notation_box)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.list_notation = tk.Listbox(notation_box, bg='#1F2022', fg=THEME['text'],
                                        font=("Consolas", 10), bd=0, yscrollcommand=scroll.set,
                                        selectbackground=THEME['accent'])
        self.list_notation.pack(fill=tk.BOTH, expand=True)
        scroll.config(command=self.list_notation.yview)

        # Buttons Grid (Undo, Restart, Surrender, Save, Hub)
        btn_frame = tk.Frame(right_panel, bg=THEME['surface'])
        btn_frame.pack(fill=tk.X, pady=(4, 0))

        btn_style = {
            'font': ("Segoe UI", 9, "bold"),
            'bd': 0,
            'relief': tk.FLAT,
            'cursor': 'hand2',
            'pady': 6
        }

        # Row 1: Undo & Save
        undo_label = f"Undo ({HOTKEYS['undo']['key_str']})"
        self.btn_undo = tk.Button(btn_frame, text=undo_label, bg=THEME['surface_light'], fg=THEME['text'],
                                  command=self._on_undo, **btn_style)
        self.btn_undo.grid(row=0, column=0, sticky="ew", padx=2, pady=3)

        save_label = f"Save ({HOTKEYS['save']['key_str']})"
        btn_save = tk.Button(btn_frame, text=save_label, bg=THEME['surface_light'], fg=THEME['text'],
                             command=self._on_save, **btn_style)
        btn_save.grid(row=0, column=1, sticky="ew", padx=2, pady=3)

        # Row 2: Restart & Surrender
        restart_label = f"Restart ({HOTKEYS['restart']['key_str']})"
        btn_restart = tk.Button(btn_frame, text=restart_label, bg=THEME['surface_light'], fg=THEME['text'],
                                command=self._on_restart, **btn_style)
        btn_restart.grid(row=1, column=0, sticky="ew", padx=2, pady=3)

        surrender_label = f"Give Up ({HOTKEYS['surrender']['key_str']})"
        btn_surrender = tk.Button(btn_frame, text=surrender_label, bg='#3A2024', fg='#FF6B6B',
                                  command=self._on_surrender, **btn_style)
        btn_surrender.grid(row=1, column=1, sticky="ew", padx=2, pady=3)

        # Row 3: Return to Hub
        btn_hub = tk.Button(btn_frame, text="Return to Hub / Main Menu", bg=THEME['surface_light'], fg=THEME['text_secondary'],
                            command=self._on_back_to_hub, **btn_style)
        btn_hub.grid(row=2, column=0, columnspan=2, sticky="ew", padx=2, pady=(6, 2))

        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        # Hotkeys footer
        hotkeys_bar = tk.Frame(right_panel, bg=THEME['surface'])
        hotkeys_bar.pack(fill=tk.X, pady=(8, 0))
        hk_text = " | ".join([f"{v['key_str']}: {v['label']}" for v in HOTKEYS.values()])
        tk.Label(hotkeys_bar, text=hk_text, font=("Segoe UI", 8),
                 bg=THEME['surface'], fg=THEME['text_secondary']).pack()

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
            return "∞"
        m = seconds // 60
        s = seconds % 60
        return f"{m:02d}:{s:02d}"

    def _draw_board(self):
        self.canvas.delete("all")
        sq_size = 60
        offset = 25

        self.canvas.create_rectangle(0, 0, 590, 590, fill=THEME['surface'], outline='')

        # Draw Coordinate Letters A-I
        cols = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']
        for c in range(9):
            x = offset + c * sq_size + sq_size // 2
            self.canvas.create_text(x, offset // 2, text=cols[c], font=("Segoe UI", 10, "bold"), fill=THEME['text_secondary'])
            self.canvas.create_text(x, offset + 9 * sq_size + offset // 2, text=cols[c], font=("Segoe UI", 10, "bold"), fill=THEME['text_secondary'])

        # Draw Coordinate Numbers 9-1
        for r in range(9):
            y = offset + r * sq_size + sq_size // 2
            num_str = str(9 - r)
            self.canvas.create_text(offset // 2, y, text=num_str, font=("Segoe UI", 10, "bold"), fill=THEME['text_secondary'])
            self.canvas.create_text(offset + 9 * sq_size + offset // 2, y, text=num_str, font=("Segoe UI", 10, "bold"), fill=THEME['text_secondary'])

        # Draw Board Grid
        for r in range(9):
            for c in range(9):
                x0 = offset + c * sq_size
                y0 = offset + r * sq_size
                x1 = x0 + sq_size
                y1 = y0 + sq_size

                base_color = THEME['board_light'] if (r + c) % 2 == 0 else THEME['board_dark']

                is_p1_target = ((r, c) == TARGET_CORNERS[0])
                is_p2_target = ((r, c) == TARGET_CORNERS[1])

                cell_fill = base_color
                outline_color = THEME['board_grid']
                outline_width = 1

                if is_p1_target:
                    cell_fill = THEME['target_p1_bg']
                    outline_color = THEME['target_p1_border']
                    outline_width = 3
                elif is_p2_target:
                    cell_fill = THEME['target_p2_bg']
                    outline_color = THEME['target_p2_border']
                    outline_width = 3

                if self.last_move and ((r, c) == self.last_move[0] or (r, c) == self.last_move[1]):
                    cell_fill = THEME['highlight_last']

                if self.selected_sq == (r, c):
                    cell_fill = THEME['highlight_select']

                self.canvas.create_rectangle(x0, y0, x1, y1, fill=cell_fill, outline=outline_color, width=outline_width)

                if is_p1_target:
                    self.canvas.create_text(x0 + 30, y0 + 12, text="★ P1 GOAL", font=("Segoe UI", 8, "bold"), fill='#D84315')
                elif is_p2_target:
                    self.canvas.create_text(x0 + 30, y0 + 12, text="★ P2 GOAL", font=("Segoe UI", 8, "bold"), fill='#C62828')

                if (r, c) in self.valid_targets:
                    dest_piece = self.state.board[r][c]
                    if dest_piece:
                        self.canvas.create_oval(x0 + 4, y0 + 4, x1 - 4, y1 - 4, outline=THEME['danger'], width=3)
                    else:
                        self.canvas.create_oval(x0 + 24, y0 + 24, x1 - 24, y1 - 24, fill=THEME['highlight_move'], outline='')

                piece = self.state.board[r][c]
                if piece:
                    self._draw_piece(x0, y0, x1, y1, piece)

    def _draw_piece(self, x0: int, y0: int, x1: int, y1: int, piece: Piece):
        color = self.config.get('p1_color', '#2ECC71') if piece.owner == 0 else self.config.get('p2_color', '#E74C3C')

        pad = 6
        self.canvas.create_oval(x0 + pad + 1, y0 + pad + 2, x1 - pad + 1, y1 - pad + 2, fill='#1B1B1B', outline='')
        self.canvas.create_oval(x0 + pad, y0 + pad, x1 - pad, y1 - pad, fill=color, outline='#FFFFFF', width=2)
        self.canvas.create_oval(x0 + pad + 5, y0 + pad + 5, x1 - pad - 5, y1 - pad - 5, outline='#FFFFFF', width=1)

        cx = (x0 + x1) // 2
        cy = (y0 + y1) // 2 - 4
        self.canvas.create_text(cx, cy, text=piece.p_type, font=("Segoe UI", 15, "bold"), fill='#FFFFFF')

        sub_name = PIECE_NAMES.get(piece.p_type, '').upper()
        self.canvas.create_text(cx, cy + 14, text=sub_name, font=("Segoe UI", 6, "bold"), fill='#FFFFFF')

    def _on_board_click(self, event):
        if not self.is_game_active or self.state.winner is not None:
            return

        if self.config.get('mode') == 'PvE' and self.state.current_turn == 1:
            return

        if self.config.get('mode') == 'PvP' and self.config.get('pvp_type') == 'Online':
            my_role = 0 if self.config.get('is_host') else 1
            if self.state.current_turn != my_role:
                return

        offset = 25
        sq_size = 60
        c = (event.x - offset) // sq_size
        r = (event.y - offset) // sq_size

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

        if self.state.winner is not None:
            self._handle_game_over(self.state.winner, "Target Corner Reached")
            return

        if self.config.get('mode') == 'PvE' and self.state.current_turn == 1 and self.is_game_active:
            self.after(350, self._ai_turn)

    def _ai_turn(self):
        if not self.is_game_active or self.state.winner is not None:
            return
        diff = self.config.get('difficulty', 'normal')
        move = get_ai_move(self.state, diff)
        if move:
            self._execute_move(move[0], move[1])

    def _update_ui_state(self):
        self._draw_board()
        p_name = self.config.get('p1_name') if self.state.current_turn == 0 else self.config.get('p2_name')
        color = self.config.get('p1_color') if self.state.current_turn == 0 else self.config.get('p2_color')

        self.lbl_turn.config(text=f"Turn: {p_name}", fg=color)
        self.lbl_stats.config(text=f"Turns: {self.state.total_turns} | Undos: {self.state.undos}")

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
            self.btn_undo.config(state=tk.DISABLED, fg=THEME['text_secondary'])
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
                    self._handle_game_over(1, "P1 Clock Expired")
                    return
            else:
                self.time_p2 -= 1
                self.lbl_p2_timer.config(text=self._format_time(self.time_p2))
                if self.time_p2 <= 0:
                    self._handle_game_over(0, "P2 Clock Expired")
                    return

            self.timer_id = self.after(1000, tick)

        self.timer_id = self.after(1000, tick)

    def _stop_timer(self):
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None

    def _handle_game_over(self, winner: int, reason: str):
        self.is_game_active = False
        self.state.winner = winner
        self._stop_timer()

        winner_name = self.config.get('p1_name') if winner == 0 else self.config.get('p2_name')
        win_color = self.config.get('p1_color') if winner == 0 else self.config.get('p2_color')

        # Save to storage with is_guest tag
        if self.config.get('mode') == 'PvE':
            if winner == 0:
                storage.save_pve_score(
                    username=self.config.get('p1_name', 'Player'),
                    turns=self.state.total_turns,
                    time_left=max(0, self.time_p1),
                    undos=self.state.undos,
                    difficulty=self.config.get('difficulty', 'normal'),
                    is_guest=self.config.get('is_guest', False)
                )
        else:
            storage.update_pvp_stats(self.config.get('p1_name'), won=(winner == 0))
            storage.update_pvp_stats(self.config.get('p2_name'), won=(winner == 1))

        # Show Game Over Modal inside the single window
        modal = ModalOverlay(self, "🏆 Match Result", width=460, height=310)

        tk.Label(modal.body, text=f"{winner_name} Wins!", font=("Segoe UI", 18, "bold"),
                 bg=THEME['surface'], fg=win_color).pack(pady=(10, 4))
        tk.Label(modal.body, text=f"Reason: {reason}", font=("Segoe UI", 11),
                 bg=THEME['surface'], fg=THEME['text_secondary']).pack(pady=(0, 12))

        stats_box = tk.Frame(modal.body, bg=THEME['surface_light'], padx=16, pady=8)
        stats_box.pack(fill=tk.X, pady=4)
        tk.Label(stats_box, text=f"Total Turns: {self.state.total_turns}  •  Undos: {self.state.undos}",
                 font=("Segoe UI", 10), bg=THEME['surface_light'], fg=THEME['text']).pack()
        if self.config.get('time_limit', 120) > 0:
            t_rem = self.time_p1 if winner == 0 else self.time_p2
            tk.Label(stats_box, text=f"Time Remaining: {self._format_time(t_rem)}",
                     font=("Segoe UI", 10), bg=THEME['surface_light'], fg=THEME['text_secondary']).pack(pady=(2, 0))

        btn_style = {'font': ("Segoe UI", 10, "bold"), 'bd': 0, 'relief': tk.FLAT, 'cursor': 'hand2', 'padx': 14, 'pady': 6}

        def on_rematch():
            modal.dismiss()
            self._restart_match()

        def on_hub():
            modal.dismiss()
            self._cleanup()
            self.app.show_view('menu')

        def on_leaderboard():
            modal.dismiss()
            self._cleanup()
            self.app.show_view('leaderboard')

        tk.Button(modal.footer, text="Rematch / Play Again", bg=THEME['accent'], fg='#FFFFFF',
                  command=on_rematch, **btn_style).pack(side=tk.LEFT, padx=4)
        tk.Button(modal.footer, text="Leaderboard", bg=THEME['surface_light'], fg=THEME['text'],
                  command=on_leaderboard, **btn_style).pack(side=tk.LEFT, padx=4)
        tk.Button(modal.footer, text="Main Menu", bg=THEME['surface_light'], fg=THEME['text'],
                  command=on_hub, **btn_style).pack(side=tk.RIGHT, padx=4)

    def _on_undo(self):
        if not self.config.get('undo_enabled') or not self.is_game_active:
            return

        if self.config.get('mode') == 'PvP' and self.config.get('pvp_type') == 'Online':
            return

        if self.config.get('mode') == 'PvE':
            if self.state.undo():
                self.state.undo()
        else:
            self.state.undo()

        self.selected_sq = None
        self.valid_targets = []
        self._update_ui_state()

    def _on_restart(self):
        if not self.is_game_active:
            self._restart_match()
            return

        modal = ModalOverlay(self, "Restart Match Confirmation", width=380, height=190)
        tk.Label(modal.body, text="Are you sure you want to restart the match?\nCurrent match progress will be reset.",
                 font=("Segoe UI", 10), bg=THEME['surface'], fg=THEME['text'], wraplength=340, justify="left").pack(pady=12)

        def confirm():
            modal.dismiss()
            if self.network_mgr:
                self.network_mgr.send_restart()
            self._restart_match()

        tk.Button(modal.footer, text="Cancel", bg=THEME['surface_light'], fg=THEME['text'],
                  font=("Segoe UI", 9, "bold"), bd=0, relief=tk.FLAT, cursor="hand2", padx=14, pady=6,
                  command=modal.dismiss).pack(side=tk.LEFT)
        tk.Button(modal.footer, text="Restart", bg=THEME['danger'], fg='#FFFFFF',
                  font=("Segoe UI", 9, "bold"), bd=0, relief=tk.FLAT, cursor="hand2", padx=16, pady=6,
                  command=confirm).pack(side=tk.RIGHT)

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

        modal = ModalOverlay(self, "Surrender / Give Up", width=380, height=190)
        tk.Label(modal.body, text="Are you sure you want to forfeit this match?\nThe opponent will be awarded victory.",
                 font=("Segoe UI", 10), bg=THEME['surface'], fg=THEME['text'], wraplength=340, justify="left").pack(pady=12)

        def confirm():
            modal.dismiss()
            if self.network_mgr:
                self.network_mgr.send_surrender()
            winner = 1 - self.state.current_turn
            self._handle_game_over(winner, "Surrender / Forfeit")

        tk.Button(modal.footer, text="Cancel", bg=THEME['surface_light'], fg=THEME['text'],
                  font=("Segoe UI", 9, "bold"), bd=0, relief=tk.FLAT, cursor="hand2", padx=14, pady=6,
                  command=modal.dismiss).pack(side=tk.LEFT)
        tk.Button(modal.footer, text="Surrender", bg=THEME['danger'], fg='#FFFFFF',
                  font=("Segoe UI", 9, "bold"), bd=0, relief=tk.FLAT, cursor="hand2", padx=16, pady=6,
                  command=confirm).pack(side=tk.RIGHT)

    def _on_save(self):
        if self.config.get('mode') != 'PvE':
            modal = ModalOverlay(self, "Save Game", width=360, height=180)
            tk.Label(modal.body, text="Mid-game saves are currently available for PvE matches.",
                     font=("Segoe UI", 10), bg=THEME['surface'], fg=THEME['text'], wraplength=320).pack(pady=16)
            tk.Button(modal.footer, text="OK", bg=THEME['accent'], fg='#FFFFFF',
                      font=("Segoe UI", 9, "bold"), bd=0, relief=tk.FLAT, cursor="hand2", padx=16, pady=6,
                      command=modal.dismiss).pack(side=tk.RIGHT)
            return

        modal = ModalOverlay(self, "Save to Game Slot", width=480, height=360)
        tk.Label(modal.body, text="Select a slot to save your current PvE match:",
                 font=("Segoe UI", 10), bg=THEME['surface'], fg=THEME['text_secondary']).pack(anchor="w", pady=(0, 8))

        slots_frame = tk.Frame(modal.body, bg=THEME['surface'])
        slots_frame.pack(fill=tk.BOTH, expand=True)

        existing_saves = storage.get_saved_slots()

        for slot_num in range(1, 6):
            slot_id = f"slot_{slot_num}"
            save_info = existing_saves.get(slot_id)
            row_frame = tk.Frame(slots_frame, bg=THEME['surface_light'], padx=10, pady=6)
            row_frame.pack(fill=tk.X, pady=3)

            if save_info:
                label_txt = f"Slot {slot_num}: {save_info.get('slot_name', 'Saved Game')} — Turns: {save_info.get('state', {}).get('total_turns', 0)} ({save_info.get('timestamp')})"
            else:
                label_txt = f"Slot {slot_num}: [Empty Slot]"

            tk.Label(row_frame, text=label_txt, font=("Segoe UI", 9),
                     bg=THEME['surface_light'], fg=THEME['text']).pack(side=tk.LEFT)

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
                self._show_toast(f"Match saved to Slot {s_num} successfully!")

            tk.Button(row_frame, text="Save Here", font=("Segoe UI", 8, "bold"),
                      bg=THEME['accent'], fg='#FFFFFF', bd=0, relief=tk.FLAT, cursor="hand2", padx=8, pady=3,
                      command=make_save_cmd).pack(side=tk.RIGHT)

        tk.Button(modal.footer, text="Close", bg=THEME['surface_light'], fg=THEME['text'],
                  font=("Segoe UI", 9, "bold"), bd=0, relief=tk.FLAT, cursor="hand2", padx=16, pady=6,
                  command=modal.dismiss).pack(side=tk.RIGHT)

    def _show_toast(self, message: str):
        toast = tk.Label(self, text=message, font=("Segoe UI", 10, "bold"),
                         bg=THEME['accent'], fg='#FFFFFF', padx=16, pady=8)
        toast.place(relx=0.5, rely=0.08, anchor=tk.CENTER)
        self.after(2200, toast.destroy)

    def _on_back_to_hub(self):
        if self.is_game_active and self.state.winner is None and self.state.total_turns > 0:
            modal = ModalOverlay(self, "Return to Main Menu", width=380, height=190)
            tk.Label(modal.body, text="Match is still in progress.\nReturn to hub? (Unsaved progress will be lost)",
                     font=("Segoe UI", 10), bg=THEME['surface'], fg=THEME['text'], wraplength=340).pack(pady=12)

            def confirm():
                modal.dismiss()
                self._cleanup()
                self.app.show_view('menu')

            tk.Button(modal.footer, text="Stay in Match", bg=THEME['surface_light'], fg=THEME['text'],
                      font=("Segoe UI", 9, "bold"), bd=0, relief=tk.FLAT, cursor="hand2", padx=14, pady=6,
                      command=modal.dismiss).pack(side=tk.LEFT)
            tk.Button(modal.footer, text="Return to Hub", bg=THEME['danger'], fg='#FFFFFF',
                      font=("Segoe UI", 9, "bold"), bd=0, relief=tk.FLAT, cursor="hand2", padx=16, pady=6,
                      command=confirm).pack(side=tk.RIGHT)
        else:
            self._cleanup()
            self.app.show_view('menu')

    def _show_rules_modal(self):
        modal = ModalOverlay(self, "Rules & Cyclic Dominance Guide", width=520, height=420)
        content = (
            "🎯 WIN CONDITION:\n"
            "• Move ANY of your pieces into opponent's designated target corner!\n"
            "   - Player 1 (Bottom): Reach Top-Right corner (I, 9)\n"
            "   - Player 2 (Top): Reach Bottom-Left corner (A, 1)\n\n"
            "⚔️ COMBAT SYSTEM (Cyclic Dominance):\n"
            "• Human (H) beats Ant (A)\n"
            "• Ant (A) beats Elephant (E)\n"
            "• Elephant (E) beats Human (H)\n"
            "• Same piece types cannot capture each other (move blocked).\n"
            "• Friendly pieces cannot be captured.\n\n"
            "🚶 MOVEMENT:\n"
            "• All pieces move 1 step in any of the 8 directions (orthogonal or diagonal)."
        )
        tk.Label(modal.body, text=content, font=("Segoe UI", 9), bg=THEME['surface'],
                 fg=THEME['text'], justify="left").pack(anchor="w", pady=4)

        tk.Button(modal.footer, text="Got it!", bg=THEME['accent'], fg='#FFFFFF',
                  font=("Segoe UI", 9, "bold"), bd=0, relief=tk.FLAT, cursor="hand2", padx=18, pady=6,
                  command=modal.dismiss).pack(side=tk.RIGHT)

    def _init_network(self):
        is_host = self.config.get('is_host', True)
        ip = self.config.get('ip', '127.0.0.1')
        port = self.config.get('port', 5555)

        self.network_mgr = NetworkManager(
            is_host=is_host,
            ip=ip,
            port=port,
            on_connect=lambda: self.after(0, lambda: self._show_toast("Opponent connected!")),
            on_move=lambda s, e: self.after(0, lambda: self._execute_move((s[0], s[1]), (e[0], e[1]), from_network=True)),
            on_restart=lambda: self.after(0, self._restart_match),
            on_surrender=lambda: self.after(0, lambda: self._handle_game_over(0 if not is_host else 1, "Opponent Surrendered")),
            on_disconnect=lambda err: self.after(0, lambda: self._show_toast("Opponent disconnected"))
        )
        self.network_mgr.start()

    def _cleanup(self):
        self._stop_timer()
        self._unbind_hotkeys()
        if self.network_mgr:
            self.network_mgr.close()
            self.network_mgr = None


class LeaderboardView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=THEME['bg'])
        self.app = app
        self.sort_by = "turns"
        self.difficulty_category = "all"
        self._build_ui()

    def _build_ui(self):
        container = tk.Frame(self, bg=THEME['bg'])
        container.pack(fill=tk.BOTH, expand=True, padx=40, pady=20)

        # Header
        header = tk.Frame(container, bg=THEME['bg'])
        header.pack(fill=tk.X, pady=(0, 14))
        tk.Label(header, text="Hall of Fame & Multi-Category Leaderboard", font=("Segoe UI", 20, "bold"),
                 bg=THEME['bg'], fg=THEME['text']).pack(side=tk.LEFT)

        tk.Button(header, text="← Back to Hub", font=("Segoe UI", 10, "bold"),
                  bg=THEME['surface_light'], fg=THEME['text'], bd=0, relief=tk.FLAT, cursor="hand2", padx=16, pady=6,
                  command=lambda: self.app.show_view('menu')).pack(side=tk.RIGHT)

        # Tabs: PvE Leaderboard | PvP Stats
        tabs_frame = tk.Frame(container, bg=THEME['bg'])
        tabs_frame.pack(fill=tk.X, pady=(0, 8))

        self.btn_tab_pve = tk.Button(tabs_frame, text="PvE Hall of Fame", font=("Segoe UI", 10, "bold"),
                                     bg=THEME['accent'], fg='#FFFFFF', bd=0, relief=tk.FLAT, cursor="hand2", padx=16, pady=6,
                                     command=lambda: self._set_tab("pve"))
        self.btn_tab_pve.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_tab_pvp = tk.Button(tabs_frame, text="PvP Records", font=("Segoe UI", 10, "bold"),
                                     bg=THEME['surface_light'], fg=THEME['text'], bd=0, relief=tk.FLAT, cursor="hand2", padx=16, pady=6,
                                     command=lambda: self._set_tab("pvp"))
        self.btn_tab_pvp.pack(side=tk.LEFT)

        # PvE Multi-Category Filter Bar
        self.pve_toolbar = tk.Frame(container, bg=THEME['surface'], padx=12, pady=8, bd=1, relief=tk.SOLID,
                                    highlightbackground=THEME['border'], highlightthickness=1)
        self.pve_toolbar.pack(fill=tk.X, pady=(0, 8))

        # Category: Difficulty Filter
        tk.Label(self.pve_toolbar, text="Category:", font=("Segoe UI", 9, "bold"),
                 bg=THEME['surface'], fg=THEME['text_secondary']).pack(side=tk.LEFT, padx=(0, 4))

        self.diff_buttons = {}
        for d_title, d_val in [("All", "all"), ("Easy", "easy"), ("Normal", "normal"), ("Hard", "hard")]:
            bg_col = THEME['accent'] if d_val == "all" else THEME['surface_light']
            fg_col = '#FFFFFF' if d_val == "all" else THEME['text']
            btn = tk.Button(self.pve_toolbar, text=d_title, font=("Segoe UI", 8, "bold"),
                            bg=bg_col, fg=fg_col, bd=0, relief=tk.FLAT, cursor="hand2", padx=8, pady=3,
                            command=lambda v=d_val: self._set_difficulty_filter(v))
            btn.pack(side=tk.LEFT, padx=2)
            self.diff_buttons[d_val] = btn

        # Separator
        tk.Label(self.pve_toolbar, text=" |  Sort:", font=("Segoe UI", 9, "bold"),
                 bg=THEME['surface'], fg=THEME['text_secondary']).pack(side=tk.LEFT, padx=(8, 4))

        # Category: Metric Sort
        self.metric_buttons = {}
        for m_title, m_val in [("Lowest Turns", "turns"), ("Fastest Time Left", "time"), ("Fewest Undos", "undos")]:
            bg_col = THEME['accent'] if m_val == "turns" else THEME['surface_light']
            fg_col = '#FFFFFF' if m_val == "turns" else THEME['text']
            btn = tk.Button(self.pve_toolbar, text=m_title, font=("Segoe UI", 8, "bold"),
                            bg=bg_col, fg=fg_col, bd=0, relief=tk.FLAT, cursor="hand2", padx=8, pady=3,
                            command=lambda m=m_val: self._set_sort(m))
            btn.pack(side=tk.LEFT, padx=2)
            self.metric_buttons[m_val] = btn

        # Table container
        table_card = tk.Frame(container, bg=THEME['surface'], bd=1, relief=tk.SOLID,
                              highlightbackground=THEME['border'], highlightthickness=1)
        table_card.pack(fill=tk.BOTH, expand=True)

        # Treeview
        columns = ("rank", "player", "category", "turns", "time_left", "undos", "date")
        self.tree = ttk.Treeview(table_card, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("rank", text="#")
        self.tree.heading("player", text="Player Profile")
        self.tree.heading("category", text="Category / Difficulty")
        self.tree.heading("turns", text="Turns")
        self.tree.heading("time_left", text="Time Remaining")
        self.tree.heading("undos", text="Undos")
        self.tree.heading("date", text="Date Achieved")

        self.tree.column("rank", width=40, anchor=tk.CENTER)
        self.tree.column("player", width=140, anchor=tk.W)
        self.tree.column("category", width=120, anchor=tk.CENTER)
        self.tree.column("turns", width=70, anchor=tk.CENTER)
        self.tree.column("time_left", width=110, anchor=tk.CENTER)
        self.tree.column("undos", width=70, anchor=tk.CENTER)
        self.tree.column("date", width=130, anchor=tk.CENTER)

        scroll = ttk.Scrollbar(table_card, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Bottom Actions Bar
        actions_bar = tk.Frame(container, bg=THEME['bg'])
        actions_bar.pack(fill=tk.X, pady=(12, 0))

        tk.Button(actions_bar, text="Delete Selected Entry", font=("Segoe UI", 9, "bold"),
                  bg=THEME['surface_light'], fg='#FF8A80', bd=0, relief=tk.FLAT, cursor="hand2", padx=14, pady=6,
                  command=self._delete_selected).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(actions_bar, text="Clear Current Category", font=("Segoe UI", 9, "bold"),
                  bg='#3A2024', fg='#FF6B6B', bd=0, relief=tk.FLAT, cursor="hand2", padx=14, pady=6,
                  command=self._clear_category).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(actions_bar, text="Clear All Records", font=("Segoe UI", 9, "bold"),
                  bg='#3A2024', fg='#FF6B6B', bd=0, relief=tk.FLAT, cursor="hand2", padx=14, pady=6,
                  command=self._clear_all).pack(side=tk.LEFT)

        self.current_tab = "pve"
        self._refresh_pve_table()

    def _set_tab(self, tab: str):
        self.current_tab = tab
        if tab == "pve":
            self.btn_tab_pve.config(bg=THEME['accent'], fg='#FFFFFF')
            self.btn_tab_pvp.config(bg=THEME['surface_light'], fg=THEME['text'])
            self.pve_toolbar.pack(fill=tk.X, pady=(0, 8))
            self._refresh_pve_table()
        else:
            self.btn_tab_pvp.config(bg=THEME['accent'], fg='#FFFFFF')
            self.btn_tab_pve.config(bg=THEME['surface_light'], fg=THEME['text'])
            self.pve_toolbar.pack_forget()
            self._refresh_pvp_table()

    def _set_difficulty_filter(self, diff: str):
        self.difficulty_category = diff
        for k, btn in self.diff_buttons.items():
            if k == diff:
                btn.config(bg=THEME['accent'], fg='#FFFFFF')
            else:
                btn.config(bg=THEME['surface_light'], fg=THEME['text'])
        self._refresh_pve_table()

    def _set_sort(self, key: str):
        self.sort_by = key
        for k, btn in self.metric_buttons.items():
            if k == key:
                btn.config(bg=THEME['accent'], fg='#FFFFFF')
            else:
                btn.config(bg=THEME['surface_light'], fg=THEME['text'])
        self._refresh_pve_table()

    def _refresh_pve_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.tree["columns"] = ("rank", "player", "category", "turns", "time_left", "undos", "date")
        self.tree.heading("rank", text="#")
        self.tree.heading("player", text="Player Profile")
        self.tree.heading("category", text="Category / Difficulty")
        self.tree.heading("turns", text="Turns")
        self.tree.heading("time_left", text="Time Remaining")
        self.tree.heading("undos", text="Undos")
        self.tree.heading("date", text="Date Achieved")

        records = storage.get_pve_leaderboard(sort_by=self.sort_by, difficulty=self.difficulty_category)
        for i, r in enumerate(records):
            time_str = f"{r['time_left'] // 60}:{r['time_left'] % 60:02d}" if r['time_left'] >= 0 else "∞"
            uname = r['username']
            if r.get('is_guest'):
                uname += " [Guest]"
            diff_label = f"{r.get('difficulty', 'Normal')} Mode"
            self.tree.insert("", tk.END, iid=r['id'], values=(
                i + 1, uname, diff_label,
                r['turns'], time_str, r['undos'], r['timestamp']
            ))

    def _refresh_pvp_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.tree["columns"] = ("player", "wins", "losses", "rate", "last_played")
        self.tree.heading("player", text="Player Profile")
        self.tree.heading("wins", text="Wins")
        self.tree.heading("losses", text="Losses")
        self.tree.heading("rate", text="Win Rate")
        self.tree.heading("last_played", text="Last Match")

        pvp_data = storage.get_pvp_stats()
        for uname, stats in pvp_data.items():
            wins = stats.get('wins', 0)
            losses = stats.get('losses', 0)
            total = wins + losses
            rate_str = f"{(wins / total * 100):.1f}%" if total > 0 else "N/A"
            self.tree.insert("", tk.END, iid=uname, values=(
                uname, wins, losses, rate_str, stats.get('last_played', '')
            ))

    def _delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            return

        sel_id = selected[0]
        if self.current_tab == "pve":
            storage.delete_pve_score(sel_id)
            self._refresh_pve_table()
        else:
            storage.delete_pvp_player(sel_id)
            self._refresh_pvp_table()

    def _clear_category(self):
        if self.current_tab != "pve":
            return
        cat_name = self.difficulty_category.capitalize() if self.difficulty_category != "all" else "All"
        modal = ModalOverlay(self, "Clear Category Records", width=380, height=190)
        tk.Label(modal.body, text=f"Clear records for '{cat_name}' category?\nThis cannot be undone.",
                 font=("Segoe UI", 10), bg=THEME['surface'], fg=THEME['text'], wraplength=340).pack(pady=12)

        def confirm():
            modal.dismiss()
            storage.clear_pve_leaderboard(difficulty=self.difficulty_category)
            self._refresh_pve_table()

        tk.Button(modal.footer, text="Cancel", bg=THEME['surface_light'], fg=THEME['text'],
                  font=("Segoe UI", 9, "bold"), bd=0, relief=tk.FLAT, cursor="hand2", padx=14, pady=6,
                  command=modal.dismiss).pack(side=tk.LEFT)
        tk.Button(modal.footer, text="Clear", bg=THEME['danger'], fg='#FFFFFF',
                  font=("Segoe UI", 9, "bold"), bd=0, relief=tk.FLAT, cursor="hand2", padx=16, pady=6,
                  command=confirm).pack(side=tk.RIGHT)

    def _clear_all(self):
        modal = ModalOverlay(self, "Clear All Records Confirmation", width=380, height=190)
        tk.Label(modal.body, text=f"Clear all {'PvE Leaderboard' if self.current_tab == 'pve' else 'PvP'} records?\nThis action cannot be undone.",
                 font=("Segoe UI", 10), bg=THEME['surface'], fg=THEME['text'], wraplength=340).pack(pady=12)

        def confirm():
            modal.dismiss()
            if self.current_tab == "pve":
                storage.clear_pve_leaderboard("all")
                self._refresh_pve_table()
            else:
                storage.clear_pvp_stats()
                self._refresh_pvp_table()

        tk.Button(modal.footer, text="Cancel", bg=THEME['surface_light'], fg=THEME['text'],
                  font=("Segoe UI", 9, "bold"), bd=0, relief=tk.FLAT, cursor="hand2", padx=14, pady=6,
                  command=modal.dismiss).pack(side=tk.LEFT)
        tk.Button(modal.footer, text="Clear All", bg=THEME['danger'], fg='#FFFFFF',
                  font=("Segoe UI", 9, "bold"), bd=0, relief=tk.FLAT, cursor="hand2", padx=16, pady=6,
                  command=confirm).pack(side=tk.RIGHT)


class SavedGamesView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=THEME['bg'])
        self.app = app
        self._build_ui()

    def _build_ui(self):
        container = tk.Frame(self, bg=THEME['bg'])
        container.pack(fill=tk.BOTH, expand=True, padx=40, pady=24)

        header = tk.Frame(container, bg=THEME['bg'])
        header.pack(fill=tk.X, pady=(0, 20))
        tk.Label(header, text="Saved Game Slots (PvE Mid-Game)", font=("Segoe UI", 20, "bold"),
                 bg=THEME['bg'], fg=THEME['text']).pack(side=tk.LEFT)

        tk.Button(header, text="← Back to Hub", font=("Segoe UI", 10, "bold"),
                  bg=THEME['surface_light'], fg=THEME['text'], bd=0, relief=tk.FLAT, cursor="hand2", padx=16, pady=6,
                  command=lambda: self.app.show_view('menu')).pack(side=tk.RIGHT)

        self.slots_container = tk.Frame(container, bg=THEME['bg'])
        self.slots_container.pack(fill=tk.BOTH, expand=True)

        self._refresh_slots()

    def _refresh_slots(self):
        for w in self.slots_container.winfo_children():
            w.destroy()

        saves = storage.get_saved_slots()

        for slot_num in range(1, 6):
            slot_id = f"slot_{slot_num}"
            data = saves.get(slot_id)

            card = tk.Frame(self.slots_container, bg=THEME['surface'], bd=1, relief=tk.SOLID,
                            highlightbackground=THEME['border'], highlightthickness=1, padx=20, pady=12)
            card.pack(fill=tk.X, pady=6)

            left_box = tk.Frame(card, bg=THEME['surface'])
            left_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            if data:
                cfg = data.get('config', {})
                state_data = data.get('state', {})
                diff = cfg.get('difficulty', 'Normal').capitalize()
                turns = state_data.get('total_turns', 0)
                t_str = data.get('timestamp', '')

                tk.Label(left_box, text=f"Slot {slot_num}: PvE Match ({diff})",
                         font=("Segoe UI", 12, "bold"), bg=THEME['surface'], fg=THEME['accent']).pack(anchor="w")
                detail_text = f"Saved: {t_str}  •  Turns: {turns}  •  Undos: {state_data.get('undos', 0)}"
                tk.Label(left_box, text=detail_text, font=("Segoe UI", 9),
                         bg=THEME['surface'], fg=THEME['text_secondary']).pack(anchor="w", pady=(2, 0))

                right_box = tk.Frame(card, bg=THEME['surface'])
                right_box.pack(side=tk.RIGHT)

                def make_load_cmd(s_data=data):
                    self.app.start_game(s_data['config'], saved_state=s_data)

                def make_del_cmd(s_id=slot_id):
                    storage.delete_game_slot(s_id)
                    self._refresh_slots()

                tk.Button(right_box, text="Delete Slot", font=("Segoe UI", 9),
                          bg='#3A2024', fg='#FF6B6B', bd=0, relief=tk.FLAT, cursor="hand2", padx=12, pady=6,
                          command=make_del_cmd).pack(side=tk.LEFT, padx=6)

                tk.Button(right_box, text="Load Game", font=("Segoe UI", 10, "bold"),
                          bg=THEME['accent'], fg='#FFFFFF', bd=0, relief=tk.FLAT, cursor="hand2", padx=16, pady=6,
                          command=make_load_cmd).pack(side=tk.RIGHT)
            else:
                tk.Label(left_box, text=f"Slot {slot_num}: [Empty Save Slot]",
                         font=("Segoe UI", 11, "italic"), bg=THEME['surface'], fg=THEME['text_secondary']).pack(anchor="w")


class TutorialView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=THEME['bg'])
        self.app = app
        self._build_ui()

    def _build_ui(self):
        container = tk.Frame(self, bg=THEME['bg'])
        container.pack(fill=tk.BOTH, expand=True, padx=40, pady=24)

        header = tk.Frame(container, bg=THEME['bg'])
        header.pack(fill=tk.X, pady=(0, 16))
        tk.Label(header, text="How to Play: 9x9 Human • Elephant • Ant",
                 font=("Segoe UI", 20, "bold"), bg=THEME['bg'], fg=THEME['text']).pack(side=tk.LEFT)

        tk.Button(header, text="← Back to Hub", font=("Segoe UI", 10, "bold"),
                  bg=THEME['surface_light'], fg=THEME['text'], bd=0, relief=tk.FLAT, cursor="hand2", padx=16, pady=6,
                  command=lambda: self.app.show_view('menu')).pack(side=tk.RIGHT)

        card = tk.Frame(container, bg=THEME['surface'], bd=1, relief=tk.SOLID,
                        highlightbackground=THEME['border'], highlightthickness=1, padx=24, pady=16)
        card.pack(fill=tk.BOTH, expand=True)

        guide_text = (
            "1. PRIMARY WIN CONDITION (Target Corner Objective)\n"
            "   • Your primary mission is to march ANY of your pieces into your opponent's designated target corner!\n"
            "   • Player 1 (Starts Bottom): Must reach Top-Right Corner (I, 9) / (0, 8).\n"
            "   • Player 2 (Starts Top): Must reach Bottom-Left Corner (A, 1) / (8, 0).\n"
            "   • The victory corners are highlighted in gold and coral on the board!\n\n"
            "2. COMBAT RULES (Cyclic Dominance)\n"
            "   • Human (H) beats Ant (A) — Human steps onto the square and removes the Ant.\n"
            "   • Ant (A) beats Elephant (E) — Ant crawls onto and eliminates the Elephant.\n"
            "   • Elephant (E) beats Human (H) — Elephant tramples and eliminates the Human.\n"
            "   • Same-type matchups (e.g., Human vs. Human): Cannot capture each other (move is blocked).\n"
            "   • Friendly fire: You can NEVER capture or step onto your own pieces!\n\n"
            "3. MOVEMENT MECHANICS\n"
            "   • All pieces move strictly 1 square per turn in any of the 8 adjacent directions\n"
            "     (horizontal, vertical, or diagonal).\n\n"
            "4. TIMERS & HOTKEYS\n"
            "   • Each player has an active countdown timer during their turn.\n"
            "   • Action buttons are clickable on the right control panel:\n"
            "     - Ctrl + Z: Undo move (reverts both Player and AI moves in PvE)\n"
            "     - Ctrl + R: Restart match (with confirmation prompt)\n"
            "     - Ctrl + E: Surrender / forfeit match\n"
            "     - Ctrl + S: Save mid-game state to a save slot"
        )

        tk.Label(card, text=guide_text, font=("Segoe UI", 10), bg=THEME['surface'],
                 fg=THEME['text'], justify="left", wraplength=760).pack(anchor="w")


class GameApp(tk.Tk):
    """Single Window Controller for the Human-Elephant-Ant Application."""
    def __init__(self):
        super().__init__()
        self.title("9x9 Tactical: Human-Elephant-Ant")
        self.geometry("1040x740")
        self.minsize(980, 700)
        self.configure(bg=THEME['bg'])

        self.container = tk.Frame(self, bg=THEME['bg'])
        self.container.pack(fill=tk.BOTH, expand=True)

        self.current_view: Optional[tk.Frame] = None
        self.show_view('menu')

    def show_view(self, view_name: str, **kwargs):
        if self.current_view:
            if hasattr(self.current_view, '_cleanup'):
                self.current_view._cleanup()
            self.current_view.destroy()
            self.current_view = None

        if view_name == 'menu':
            self.current_view = MainMenuView(self.container, self)
        elif view_name == 'config':
            mode = kwargs.get('mode', 'PvE')
            self.current_view = ConfigView(self.container, self, mode=mode)
        elif view_name == 'game':
            config = kwargs.get('config', {})
            saved_state = kwargs.get('saved_state', None)
            self.current_view = GameView(self.container, self, config=config, saved_state=saved_state)
        elif view_name == 'leaderboard':
            self.current_view = LeaderboardView(self.container, self)
        elif view_name == 'saves':
            self.current_view = SavedGamesView(self.container, self)
        elif view_name == 'tutorial':
            self.current_view = TutorialView(self.container, self)

        if self.current_view:
            self.current_view.pack(fill=tk.BOTH, expand=True)

    def open_config(self, mode: str):
        self.show_view('config', mode=mode)

    def start_game(self, config: Dict[str, Any], saved_state: Optional[Dict[str, Any]] = None):
        self.show_view('game', config=config, saved_state=saved_state)
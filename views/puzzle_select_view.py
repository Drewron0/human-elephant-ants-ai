import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, List, Optional

from ui_theme import (
    THEME, FONT_NAME, ButtonPrimary, ButtonSecondary, ButtonDanger,
    draw_board_thumbnail, ThemedModal, bind_mousewheel
)
import storage
from puzzle_logic import (
    PuzzleScenario, PRECONFIGURED_STAGES_6X6, PRECONFIGURED_STAGES_9X9,
    get_all_puzzles, generate_winnable_puzzle
)


class PuzzleSelectView(tk.Frame):
    """
    Apple-styled Stage Selection View with dynamic board thumbnails,
    resizable sidebar, AI model selector, metrics toggle, stage leaderboard, and stage CRUD.
    """
    def __init__(self, parent, app):
        super().__init__(parent, bg=THEME['bg'])
        self.app = app
        self.all_puzzles = get_all_puzzles()
        self.active_category = "preset_6x6"
        self.selected_puzzle_id: str = "stage_6x6_01"
        self.card_widgets: Dict[str, Dict[str, Any]] = {}

        self._build_ui()
        self._populate_grid()
        self._update_sidebar()

    def _build_ui(self):
        # Top Header Bar
        top_bar = tk.Frame(self, bg=THEME['surface'], height=48, bd=0, highlightbackground=THEME['border'], highlightthickness=1)
        top_bar.pack(fill=tk.X, padx=0, pady=0)

        title_box = tk.Frame(top_bar, bg=THEME['surface'])
        title_box.pack(side=tk.LEFT, padx=20, pady=8)

        tk.Label(
            title_box,
            text="Puzzle Stages",
            font=(FONT_NAME, 13, "bold"),
            bg=THEME['surface'],
            fg=THEME['text']
        ).pack(side=tk.LEFT)

        ButtonSecondary(top_bar, text="Back to Main Menu", command=lambda: self.app.show_view('menu')).pack(side=tk.RIGHT, padx=16, pady=8)
        ButtonPrimary(top_bar, text="+ Create Custom Stage", command=self._open_stage_editor).pack(side=tk.RIGHT, padx=(0, 8), pady=8)

        # Resizable Horizontal PanedWindow for Catalog (Left) and Sidebar (Right)
        self.paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg=THEME['border'], sashrelief=tk.FLAT, sashwidth=4, bd=0)
        self.paned.pack(fill=tk.BOTH, expand=True)

        # LEFT CATALOG PANE
        self.left_pane = tk.Frame(self.paned, bg=THEME['bg'])
        self.paned.add(self.left_pane, minsize=480, stretch="always")

        # Category Filter Tabs
        tab_frame = tk.Frame(self.left_pane, bg=THEME['surface_card'], padx=6, pady=4)
        tab_frame.pack(fill=tk.X, padx=16, pady=(12, 8))

        self.btn_tab_preset = ButtonSecondary(tab_frame, text="Standard (6x6)", command=lambda: self._set_category("preset_6x6"))
        self.btn_tab_preset.pack(side=tk.LEFT, padx=3)

        self.btn_tab_9x9 = ButtonSecondary(tab_frame, text="Large Board (9x9)", command=lambda: self._set_category("preset_9x9"))
        self.btn_tab_9x9.pack(side=tk.LEFT, padx=3)

        self.btn_tab_custom = ButtonSecondary(tab_frame, text="Custom Stages", command=lambda: self._set_category("custom"))
        self.btn_tab_custom.pack(side=tk.LEFT, padx=3)

        self.btn_tab_random = ButtonSecondary(tab_frame, text="Random Challenge", command=lambda: self._set_category("random"))
        self.btn_tab_random.pack(side=tk.LEFT, padx=3)

        # Scrollable Grid of Stage Thumbnails
        grid_container = tk.Frame(self.left_pane, bg=THEME['bg'])
        grid_container.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))

        self.grid_canvas = tk.Canvas(grid_container, bg=THEME['bg'], highlightthickness=0)
        grid_scroll = ttk.Scrollbar(grid_container, orient=tk.VERTICAL, command=self.grid_canvas.yview)
        self.scrollable_grid = tk.Frame(self.grid_canvas, bg=THEME['bg'])

        self.scrollable_grid.bind(
            "<Configure>",
            lambda e: self.grid_canvas.configure(scrollregion=self.grid_canvas.bbox("all"))
        )

        self.canvas_window = self.grid_canvas.create_window((0, 0), window=self.scrollable_grid, anchor="nw")
        self.grid_canvas.configure(yscrollcommand=grid_scroll.set)

        self.grid_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        grid_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.grid_canvas.bind("<Configure>", self._on_canvas_configure)
        bind_mousewheel(self.scrollable_grid, self.grid_canvas)
        bind_mousewheel(self.grid_canvas, self.grid_canvas)

        # RIGHT SELECTION SIDEBAR PANE
        self.right_pane = tk.Frame(self.paned, bg=THEME['surface'], bd=0, highlightbackground=THEME['border'], highlightthickness=1)
        self.paned.add(self.right_pane, minsize=320, stretch="never")

        self._build_sidebar_ui()

    def _build_sidebar_ui(self):
        sidebar_scroll_canvas = tk.Canvas(self.right_pane, bg=THEME['surface'], highlightthickness=0)
        scroll_y = ttk.Scrollbar(self.right_pane, orient=tk.VERTICAL, command=sidebar_scroll_canvas.yview)
        content = tk.Frame(sidebar_scroll_canvas, bg=THEME['surface'], padx=16, pady=14)

        content.bind(
            "<Configure>",
            lambda e: sidebar_scroll_canvas.configure(scrollregion=sidebar_scroll_canvas.bbox("all"))
        )
        self.sidebar_window = sidebar_scroll_canvas.create_window((0, 0), window=content, anchor="nw")
        sidebar_scroll_canvas.configure(yscrollcommand=scroll_y.set)

        sidebar_scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        sidebar_scroll_canvas.bind("<Configure>", lambda e: sidebar_scroll_canvas.itemconfig(self.sidebar_window, width=e.width))

        bind_mousewheel(content, sidebar_scroll_canvas)
        bind_mousewheel(sidebar_scroll_canvas, sidebar_scroll_canvas)

        # Selected Stage Info Card
        self.card_info = tk.Frame(content, bg=THEME['surface_light'], padx=12, pady=10, bd=1, relief=tk.SOLID, highlightbackground=THEME['border'], highlightthickness=1)
        self.card_info.pack(fill=tk.X, pady=(0, 10))

        self.lbl_selected_title = tk.Label(self.card_info, text="Selected Stage", font=(FONT_NAME, 11, "bold"), bg=THEME['surface_light'], fg=THEME['text'])
        self.lbl_selected_title.pack(anchor="w")

        self.lbl_selected_desc = tk.Label(self.card_info, text="Stage description...", font=(FONT_NAME, 8), bg=THEME['surface_light'], fg=THEME['text_muted'], wraplength=270, justify="left")
        self.lbl_selected_desc.pack(anchor="w", pady=(3, 6))

        self.lbl_selected_stats = tk.Label(self.card_info, text="6x6 Board | Optimal: 6 steps | Move Limit: 18", font=(FONT_NAME, 8, "bold"), bg=THEME['surface_light'], fg=THEME['accent'])
        self.lbl_selected_stats.pack(anchor="w")

        # Player Profile Selector
        tk.Label(content, text="Player Profile:", font=(FONT_NAME, 9, "bold"), bg=THEME['surface'], fg=THEME['text']).pack(anchor="w", pady=(4, 2))
        self.var_player_name = tk.StringVar(value=storage.get_last_username())
        cb_player = ttk.Combobox(content, textvariable=self.var_player_name, values=storage.get_recent_profiles(), width=24, font=(FONT_NAME, 9))
        cb_player.pack(fill=tk.X, pady=(0, 4))

        self.var_guest = tk.BooleanVar(value=False)
        tk.Checkbutton(
            content,
            text="Play as Guest",
            variable=self.var_guest,
            font=(FONT_NAME, 8),
            bg=THEME['surface'],
            fg=THEME['text_muted'],
            selectcolor=THEME['surface_light'],
            activebackground=THEME['surface'],
            activeforeground=THEME['text'],
            command=self._on_guest_toggle
        ).pack(anchor="w", pady=(0, 8))

        # AI Model Selector
        tk.Label(content, text="AI Defender Model:", font=(FONT_NAME, 9, "bold"), bg=THEME['surface'], fg=THEME['text']).pack(anchor="w", pady=(4, 2))
        self.var_ai_model = tk.StringVar(value="Proposed: Optimized (Alpha-Beta d=6)")
        cb_model = ttk.Combobox(
            content,
            textvariable=self.var_ai_model,
            values=[
                "Proposed: Optimized (Alpha-Beta d=6)",
                "Proposed: Optimized (Alpha-Beta d=3)",
                "Baseline 2: Vanilla Minimax (d=3, Static)",
                "Baseline 1: Random Move Agent"
            ],
            state="readonly",
            font=(FONT_NAME, 9)
        )
        cb_model.pack(fill=tk.X, pady=(0, 10))

        # Show Search Metrics Toggle (Requirement: avoid spoilers)
        metrics_box = tk.Frame(content, bg=THEME['surface_card'], padx=8, pady=6, bd=1, relief=tk.SOLID, highlightbackground=THEME['border'], highlightthickness=1)
        metrics_box.pack(fill=tk.X, pady=(0, 12))

        self.var_show_metrics = tk.BooleanVar(value=False)
        chk_metrics = tk.Checkbutton(
            metrics_box,
            text="Show AI Search Metrics During Game",
            variable=self.var_show_metrics,
            font=(FONT_NAME, 8, "bold"),
            bg=THEME['surface_card'],
            fg=THEME['text'],
            selectcolor=THEME['surface_light'],
            activebackground=THEME['surface_card'],
            activeforeground=THEME['text']
        )
        chk_metrics.pack(anchor="w")

        tk.Label(
            metrics_box,
            text="Keep disabled to avoid move spoilers during gameplay.",
            font=(FONT_NAME, 8),
            bg=THEME['surface_card'],
            fg=THEME['text_muted']
        ).pack(anchor="w", padx=(18, 0))

        # Action Buttons
        ButtonPrimary(content, text="Play Stage", command=self._start_selected_stage).pack(fill=tk.X, pady=(0, 6))

        self.frame_custom_actions = tk.Frame(content, bg=THEME['surface'])
        self.frame_custom_actions.pack(fill=tk.X, pady=(0, 8))

        ButtonSecondary(self.frame_custom_actions, text="Edit Stage", command=self._edit_selected_stage).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        ButtonDanger(self.frame_custom_actions, text="Delete", command=self._delete_selected_stage).pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(2, 0))

        # Stage Leaderboard Box
        tk.Label(content, text="Stage Leaderboard (Best Records):", font=(FONT_NAME, 9, "bold"), bg=THEME['surface'], fg=THEME['text']).pack(anchor="w", pady=(6, 4))
        self.box_leaderboard = tk.Frame(content, bg=THEME['surface_light'], padx=8, pady=6, bd=1, relief=tk.SOLID, highlightbackground=THEME['border'], highlightthickness=1)
        self.box_leaderboard.pack(fill=tk.X)

        self._refresh_stage_leaderboard()

    def _on_canvas_configure(self, event):
        self.grid_canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_guest_toggle(self):
        if self.var_guest.get():
            self.var_player_name.set(storage.generate_guest_name())
        else:
            self.var_player_name.set(storage.get_last_username() or "Player 1")

    def _set_category(self, cat: str):
        self.active_category = cat
        self._highlight_active_tab()
        self._populate_grid()

    def _highlight_active_tab(self):
        tabs = [
            ("preset_6x6", self.btn_tab_preset),
            ("preset_9x9", self.btn_tab_9x9),
            ("custom", self.btn_tab_custom),
            ("random", self.btn_tab_random)
        ]
        for c, btn in tabs:
            if c == self.active_category:
                btn.config(bg=THEME['accent'], fg='#FFFFFF')
            else:
                btn.config(bg=THEME['surface_light'], fg=THEME['text'])

    def _populate_grid(self):
        for widget in self.scrollable_grid.winfo_children():
            widget.destroy()
        self.card_widgets.clear()

        # Gather puzzles for category
        if self.active_category == "preset_6x6":
            puzzles = list(PRECONFIGURED_STAGES_6X6.values())
        elif self.active_category == "preset_9x9":
            puzzles = list(PRECONFIGURED_STAGES_9X9.values())
        elif self.active_category == "custom":
            puzzles = [p for p in get_all_puzzles().values() if p.is_custom]
        else:
            # Random winnable: provide 3 dynamically generated winnable puzzles
            puzzles = [
                generate_winnable_puzzle(board_size=6, min_steps=5, max_steps=7),
                generate_winnable_puzzle(board_size=6, min_steps=6, max_steps=8),
                generate_winnable_puzzle(board_size=6, min_steps=7, max_steps=10)
            ]

        if not puzzles:
            msg_frame = tk.Frame(self.scrollable_grid, bg=THEME['bg'])
            msg_frame.pack(fill=tk.BOTH, expand=True, pady=40)
            tk.Label(msg_frame, text="No stages found in this category.", font=(FONT_NAME, 11), bg=THEME['bg'], fg=THEME['text_muted']).pack()
            if self.active_category == "custom":
                ButtonPrimary(msg_frame, text="Create Stage Now", command=self._open_stage_editor).pack(pady=8)
            return

        # Ensure selected puzzle id exists
        if self.selected_puzzle_id not in [p.id for p in puzzles]:
            self.selected_puzzle_id = puzzles[0].id

        cols = 3
        for idx, puzzle in enumerate(puzzles):
            r = idx // cols
            c = idx % cols

            card = tk.Frame(
                self.scrollable_grid,
                bg=THEME['surface_card'],
                bd=1,
                relief=tk.SOLID,
                highlightbackground=THEME['border'],
                highlightthickness=1,
                padx=8,
                pady=8,
                cursor='hand2'
            )
            card.grid(row=r, column=c, padx=8, pady=8, sticky="nsew")

            # Thumbnail Canvas
            thumb_canvas = tk.Canvas(card, width=130, height=130, bg=THEME['surface_card'], highlightthickness=0)
            thumb_canvas.pack(pady=(0, 6))

            target = (0, puzzle.board_size - 1)
            draw_board_thumbnail(thumb_canvas, puzzle.board_size, puzzle.pieces, target, width=130, height=130)

            # Title (Centered)
            lbl_title = tk.Label(card, text=puzzle.title, font=(FONT_NAME, 9, "bold"), bg=THEME['surface_card'], fg=THEME['text'], wraplength=130, justify="center")
            lbl_title.pack(anchor="center", fill=tk.X)

            lbl_sub = tk.Label(card, text=f"{puzzle.board_size}x{puzzle.board_size} | {puzzle.s_optimal} steps", font=(FONT_NAME, 8), bg=THEME['surface_card'], fg=THEME['text_muted'], justify="center")
            lbl_sub.pack(anchor="center", fill=tk.X, pady=(2, 0))

            # Click binding on all children
            def bind_click(w, p_id=puzzle.id):
                w.bind("<Button-1>", lambda e: self._select_stage(p_id))
            bind_click(card)
            bind_click(thumb_canvas)
            bind_click(lbl_title)
            bind_click(lbl_sub)

            self.card_widgets[puzzle.id] = {'card': card, 'puzzle': puzzle}

        for col_idx in range(cols):
            self.scrollable_grid.columnconfigure(col_idx, weight=1)

        bind_mousewheel(self.scrollable_grid, self.grid_canvas)
        self._refresh_card_highlights()
        self._update_sidebar()

    def _select_stage(self, puzzle_id: str):
        self.selected_puzzle_id = puzzle_id
        self._refresh_card_highlights()
        self._update_sidebar()

    def _refresh_card_highlights(self):
        for p_id, item in self.card_widgets.items():
            card = item['card']
            if p_id == self.selected_puzzle_id:
                card.config(highlightbackground=THEME['accent'], highlightthickness=2)
            else:
                card.config(highlightbackground=THEME['border'], highlightthickness=1)

    def _update_sidebar(self):
        puzzle = None
        if self.selected_puzzle_id in self.card_widgets:
            puzzle = self.card_widgets[self.selected_puzzle_id]['puzzle']
        else:
            all_p = get_all_puzzles()
            puzzle = all_p.get(self.selected_puzzle_id) or list(PRECONFIGURED_STAGES_6X6.values())[0]

        if not puzzle:
            return

        self.lbl_selected_title.config(text=puzzle.title)
        self.lbl_selected_desc.config(text=puzzle.description or "Tactical puzzle scenario.")
        self.lbl_selected_stats.config(text=f"{puzzle.board_size}x{puzzle.board_size} Board | Optimal: {puzzle.s_optimal} steps | Move Limit: {puzzle.s_max}")

        if puzzle.is_custom:
            self.frame_custom_actions.pack(fill=tk.X, pady=(0, 8))
        else:
            self.frame_custom_actions.pack_forget()

        self._refresh_stage_leaderboard()

    def _refresh_stage_leaderboard(self):
        for widget in self.box_leaderboard.winfo_children():
            widget.destroy()

        records = storage.get_stage_leaderboard(self.selected_puzzle_id)
        if not records:
            tk.Label(
                self.box_leaderboard,
                text="No records yet for this stage. Be the first to solve it!",
                font=(FONT_NAME, 8, "italic"),
                bg=THEME['surface_light'],
                fg=THEME['text_muted']
            ).pack(anchor="w")
            return

        for idx, rec in enumerate(records[:5], 1):
            row = tk.Frame(self.box_leaderboard, bg=THEME['surface_light'])
            row.pack(fill=tk.X, pady=1)

            name = rec.get('username', 'Player')
            steps = rec.get('steps', 0)
            delta = rec.get('delay_margin', 0)
            undos = rec.get('undos', 0)

            tk.Label(
                row,
                text=f"{idx}. {name}",
                font=(FONT_NAME, 8, "bold" if idx == 1 else "normal"),
                bg=THEME['surface_light'],
                fg=THEME['text']
            ).pack(side=tk.LEFT)

            tk.Label(
                row,
                text=f"{steps} moves (Delay: +{delta}) | {undos}u",
                font=(FONT_NAME, 8),
                bg=THEME['surface_light'],
                fg=THEME['accent'] if idx == 1 else THEME['text_muted']
            ).pack(side=tk.RIGHT)

    def _open_stage_editor(self):
        self.app.show_view('stage_editor')

    def _edit_selected_stage(self):
        puzzle = self.card_widgets.get(self.selected_puzzle_id, {}).get('puzzle')
        if puzzle and puzzle.is_custom:
            self.app.show_view('stage_editor', edit_stage=puzzle.to_dict())

    def _delete_selected_stage(self):
        modal = ThemedModal(self, "Delete Custom Stage", min_width=360)
        tk.Label(
            modal.body,
            text=f"Are you sure you want to delete this custom stage permanently?",
            font=(FONT_NAME, 9),
            bg=THEME['surface'],
            fg=THEME['text']
        ).pack(pady=10)

        def confirm():
            modal.dismiss()
            storage.delete_custom_stage(self.selected_puzzle_id)
            self._set_category(self.active_category)

        ButtonSecondary(modal.footer, text="Cancel", command=modal.dismiss).pack(side=tk.LEFT)
        ButtonDanger(modal.footer, text="Delete Stage", command=confirm).pack(side=tk.RIGHT)

    def _start_selected_stage(self):
        puzzle = self.card_widgets.get(self.selected_puzzle_id, {}).get('puzzle')
        if not puzzle:
            all_p = get_all_puzzles()
            puzzle = all_p.get(self.selected_puzzle_id) or list(PRECONFIGURED_STAGES_6X6.values())[0]

        p_name = self.var_player_name.get().strip() or "Player 1"
        if not self.var_guest.get() and not p_name.lower().startswith("guest"):
            storage.save_last_username(p_name)

        model_val = self.var_ai_model.get()
        if "Alpha-Beta d=6" in model_val:
            agent_model = 'proposed_d6'
            depth = 6
        elif "Alpha-Beta d=3" in model_val:
            agent_model = 'proposed_d3'
            depth = 3
        elif "Baseline 2" in model_val or "Vanilla" in model_val:
            agent_model = 'baseline_2_vanilla'
            depth = 3
        else:
            agent_model = 'baseline_1_random'
            depth = 1

        config = {
            'mode': 'Puzzle',
            'p1_name': p_name,
            'is_guest_1': self.var_guest.get(),
            'puzzle_scenario': puzzle.id,
            'custom_scenario_obj': puzzle,
            'agent_model': agent_model,
            'agent_model_name': model_val,
            'search_depth': depth,
            'board_size': puzzle.board_size,
            'show_metrics': self.var_show_metrics.get(),
            'undo_enabled': True,
            'p1_color': '#30D158',
            'p2_color': '#FF453A'
        }

        self.app.start_puzzle(config)

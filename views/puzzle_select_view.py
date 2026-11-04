import tkinter as tk
from tkinter import ttk
from typing import Dict, Any

from ui_theme import (
    THEME, FONT_NAME, ButtonPrimary, ButtonSecondary, ButtonDanger,
    draw_board_thumbnail, ThemedModal, bind_mousewheel
)
import storage
from puzzle_logic import get_all_puzzles


class PuzzleSelectView(tk.Frame):
    """Browse and play stages saved by the user in the custom stage editor."""
    def __init__(self, parent, app):
        super().__init__(parent, bg=THEME['bg'])
        self.app = app
        self.selected_puzzle_id: str = ""
        self.card_widgets: Dict[str, Dict[str, Any]] = {}

        self._build_ui()
        self._populate_grid()

    def _build_ui(self):
        # Header bar
        top_bar = tk.Frame(self, bg=THEME['surface'], height=48, bd=0, highlightbackground=THEME['border'], highlightthickness=1)
        top_bar.pack(fill=tk.X, padx=0, pady=0)

        title_box = tk.Frame(top_bar, bg=THEME['surface'])
        title_box.pack(side=tk.LEFT, padx=20, pady=8)

        tk.Label(
            title_box,
            text="Custom Puzzle Stages",
            font=(FONT_NAME, 13, "bold"),
            bg=THEME['surface'],
            fg=THEME['text']
        ).pack(side=tk.LEFT)

        ButtonSecondary(top_bar, text="Back to Main Menu", command=lambda: self.app.show_view('menu')).pack(side=tk.RIGHT, padx=16, pady=8)
        ButtonPrimary(top_bar, text="+ Create Custom Stage", command=self._open_stage_editor).pack(side=tk.RIGHT, padx=(0, 8), pady=8)

        # Paned window container
        self.paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg=THEME['border'], sashrelief=tk.FLAT, sashwidth=4, bd=0)
        self.paned.pack(fill=tk.BOTH, expand=True)

        # Catalog pane
        self.left_pane = tk.Frame(self.paned, bg=THEME['bg'])
        self.paned.add(self.left_pane, minsize=480, stretch="always")

        # Scrollable grid of stage thumbnails
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

        # Selection sidebar pane
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

        # Selected stage info card
        self.card_info = tk.Frame(content, bg=THEME['surface_light'], padx=12, pady=10, bd=1, relief=tk.SOLID, highlightbackground=THEME['border'], highlightthickness=1)
        self.card_info.pack(fill=tk.X, pady=(0, 10))

        self.lbl_selected_title = tk.Label(self.card_info, text="Selected Stage", font=(FONT_NAME, 11, "bold"), bg=THEME['surface_light'], fg=THEME['text'])
        self.lbl_selected_title.pack(anchor="w")

        self.lbl_selected_desc = tk.Label(self.card_info, text="Stage description...", font=(FONT_NAME, 8), bg=THEME['surface_light'], fg=THEME['text_muted'], wraplength=270, justify="left")
        self.lbl_selected_desc.pack(anchor="w", pady=(3, 6))

        self.lbl_selected_stats = tk.Label(self.card_info, text="", font=(FONT_NAME, 8, "bold"), bg=THEME['surface_light'], fg=THEME['accent'], wraplength=270, justify="left")
        self.lbl_selected_stats.pack(anchor="w")

        # Player profile selector
        tk.Label(content, text="Player Profile:", font=(FONT_NAME, 9, "bold"), bg=THEME['surface'], fg=THEME['text']).pack(anchor="w", pady=(4, 2))
        self.var_player_name = tk.StringVar(value=storage.get_last_username())
        cb_player = ttk.Combobox(content, textvariable=self.var_player_name, values=storage.get_recent_profiles(), width=24, font=(FONT_NAME, 9))
        cb_player.pack(fill=tk.X, pady=(0, 4))

        # AI model selector
        tk.Label(content, text="AI Defender Model:", font=(FONT_NAME, 9, "bold"), bg=THEME['surface'], fg=THEME['text']).pack(anchor="w", pady=(4, 2))
        self.var_ai_model = tk.StringVar(value="Exact Defender (best defense)")
        cb_model = ttk.Combobox(
            content,
            textvariable=self.var_ai_model,
            values=[
                "Exact Defender (best defense)",
                "Practice: Vanilla Minimax (d=3, Static)",
                "Practice: Random Move Agent"
            ],
            state="readonly",
            font=(FONT_NAME, 9)
        )
        cb_model.pack(fill=tk.X, pady=(0, 10))
        tk.Label(content, text="Exact Defender follows proven best replies. Practice baselines can play weaker moves.",
                 font=(FONT_NAME, 8), bg=THEME['surface'], fg=THEME['text_muted'],
                 wraplength=270, justify="left").pack(anchor="w", pady=(0, 8))

        # Show search metrics toggle
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

        # Action buttons
        self.btn_play = ButtonPrimary(content, text="Play Stage", command=self._start_selected_stage)
        self.btn_play.pack(fill=tk.X, pady=(0, 6))

        self.frame_custom_actions = tk.Frame(content, bg=THEME['surface'])
        ButtonSecondary(self.frame_custom_actions, text="Edit Stage", command=self._edit_selected_stage).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        ButtonDanger(self.frame_custom_actions, text="Delete", command=self._delete_selected_stage).pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(2, 0))

        # Stage leaderboard box
        tk.Label(content, text="Stage Leaderboard (Best Records):", font=(FONT_NAME, 9, "bold"), bg=THEME['surface'], fg=THEME['text']).pack(anchor="w", pady=(6, 4))
        self.box_leaderboard = tk.Frame(content, bg=THEME['surface_light'], padx=8, pady=6, bd=1, relief=tk.SOLID, highlightbackground=THEME['border'], highlightthickness=1)
        self.box_leaderboard.pack(fill=tk.X)


    def _on_canvas_configure(self, event):
        self.grid_canvas.itemconfig(self.canvas_window, width=event.width)

    def _populate_grid(self):
        for widget in self.scrollable_grid.winfo_children():
            widget.destroy()
        self.card_widgets.clear()

        puzzles = list(get_all_puzzles().values())
        if not puzzles:
            self.selected_puzzle_id = ''
            tk.Label(self.scrollable_grid, text="No custom stages yet.\nCreate a custom stage to start playing.",
                     font=(FONT_NAME, 11), bg=THEME['bg'], fg=THEME['text_muted']).pack(pady=40)
            self._update_sidebar()
            return

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

            thumb_canvas = tk.Canvas(card, width=130, height=130, bg=THEME['surface_card'], highlightthickness=0)
            thumb_canvas.pack(pady=(0, 6))

            target = (0, puzzle.board_size - 1)
            draw_board_thumbnail(thumb_canvas, puzzle.board_size, puzzle.pieces, target, width=130, height=130)

            lbl_title = tk.Label(card, text=puzzle.title, font=(FONT_NAME, 9, "bold"), bg=THEME['surface_card'], fg=THEME['text'], wraplength=130, justify="center")
            lbl_title.pack(anchor="center", fill=tk.X)

            minimum = f"Min: {puzzle.s_optimal} steps" if puzzle.s_optimal is not None else "Minimum not set"
            lbl_sub = tk.Label(card, text=f"{puzzle.board_size}x{puzzle.board_size} | {minimum}", font=(FONT_NAME, 8), bg=THEME['surface_card'], fg=THEME['text_muted'], justify="center")
            lbl_sub.pack(anchor="center", fill=tk.X, pady=(2, 0))

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
        self.btn_play.config(state='normal')
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
        puzzle = self.card_widgets.get(self.selected_puzzle_id, {}).get('puzzle')
        if not puzzle:
            self.lbl_selected_title.config(text='No custom stage selected')
            self.lbl_selected_desc.config(text='Create a custom stage using the button above.')
            self.lbl_selected_stats.config(text='')
            self.btn_play.config(state='disabled')
            self.frame_custom_actions.pack_forget()
            for widget in self.box_leaderboard.winfo_children():
                widget.destroy()
            return

        self.lbl_selected_title.config(text=puzzle.title)
        self.lbl_selected_desc.config(text=puzzle.description or "Tactical puzzle scenario.")
        details = f"{puzzle.board_size}x{puzzle.board_size} Board | {puzzle.step_summary}\nMove Limit: {puzzle.s_max}"
        if puzzle.s_optimal is None:
            details += '\nEdit this stage to enter its minimum steps.'
        self.lbl_selected_stats.config(text=details)
        self.btn_play.config(state='disabled' if puzzle.s_optimal is None else 'normal')

        self.frame_custom_actions.pack(fill=tk.X, pady=(0, 8))

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
                text=f"{steps} moves | {undos}u",
                font=(FONT_NAME, 8),
                bg=THEME['surface_light'],
                fg=THEME['accent'] if idx == 1 else THEME['text_muted']
            ).pack(side=tk.RIGHT)

    def _open_stage_editor(self):
        self.app.show_view('stage_editor')

    def _edit_selected_stage(self):
        puzzle = self.card_widgets.get(self.selected_puzzle_id, {}).get('puzzle')
        if puzzle:
            self.app.show_view('stage_editor', edit_stage=puzzle.to_dict())

    def _delete_selected_stage(self):
        if self.selected_puzzle_id not in self.card_widgets:
            return
        modal = ThemedModal(self, "Delete Custom Stage", min_width=360)
        tk.Label(
            modal.body,
            text="Are you sure you want to delete this custom stage permanently?",
            font=(FONT_NAME, 9),
            bg=THEME['surface'],
            fg=THEME['text']
        ).pack(pady=10)

        def confirm():
            modal.dismiss()
            storage.delete_custom_stage(self.selected_puzzle_id)
            self._populate_grid()

        ButtonSecondary(modal.footer, text="Cancel", command=modal.dismiss).pack(side=tk.LEFT)
        ButtonDanger(modal.footer, text="Delete Stage", command=confirm).pack(side=tk.RIGHT)

    def _start_selected_stage(self):
        puzzle = self.card_widgets.get(self.selected_puzzle_id, {}).get('puzzle')
        if not puzzle or puzzle.s_optimal is None:
            return

        p_name = self.var_player_name.get().strip() or "Player 1"
        storage.save_last_username(p_name)

        model_val = self.var_ai_model.get()
        if "Exact Defender" in model_val or "Alpha-Beta d=6" in model_val:
            agent_model = 'exact_defender'
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

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, List, Tuple, Optional

from ui_theme import (
    THEME, FONT_NAME, ButtonPrimary, ButtonSecondary, ButtonDanger,
    ThemedModal, draw_star
)
import storage
from puzzle_logic import bfs_safe_path, PuzzleScenario


class StageEditorView(tk.Frame):
    """
    Apple-styled Stage Editor providing full CRUD for custom Chess-Sut puzzle stages.
    Includes visual board editor, piece palette, and real-time winnability verification.
    """
    def __init__(self, parent, app, edit_stage: Optional[Dict[str, Any]] = None):
        super().__init__(parent, bg=THEME['bg'])
        self.app = app
        self.edit_stage_id = edit_stage.get('id') if edit_stage else None

        # State
        self.board_size = edit_stage.get('board_size', 6) if edit_stage else 6
        self.stage_title = edit_stage.get('title', 'My Custom Stage') if edit_stage else 'My Custom Stage'
        self.stage_desc = edit_stage.get('description', '') if edit_stage else 'Custom tactical puzzle scenario.'

        # Placed pieces: dict mapping (r, c) -> (owner, p_type)
        self.placed_pieces: Dict[Tuple[int, int], Tuple[int, str]] = {}
        if edit_stage and 'pieces' in edit_stage:
            for p in edit_stage['pieces']:
                self.placed_pieces[(p[0], p[1])] = (p[2], p[3])
        else:
            # Default starter layout on 6x6
            self.placed_pieces[(self.board_size - 1, 0)] = (0, 'H')
            self.placed_pieces[(2, 3)] = (1, 'E')

        # Active tool: 'P0_H', 'P0_E', 'P0_A', 'P1_H', 'P1_E', 'P1_A', 'ERASER'
        self.active_tool: str = 'P1_E'
        self.last_verification: Optional[Dict[str, Any]] = None

        self._build_ui()
        self._verify_winnability(silent=True)

    def _build_ui(self):
        # Top Bar
        top_bar = tk.Frame(self, bg=THEME['surface'], height=48, bd=0, highlightbackground=THEME['border'], highlightthickness=1)
        top_bar.pack(fill=tk.X, padx=0, pady=0)

        title_box = tk.Frame(top_bar, bg=THEME['surface'])
        title_box.pack(side=tk.LEFT, padx=20, pady=8)

        mode_name = "Edit Custom Stage" if self.edit_stage_id else "Stage Builder & Editor"
        tk.Label(
            title_box,
            text=mode_name,
            font=(FONT_NAME, 13, "bold"),
            bg=THEME['surface'],
            fg=THEME['text']
        ).pack(side=tk.LEFT)

        ButtonSecondary(top_bar, text="Cancel & Exit", command=lambda: self.app.show_view('puzzle_select')).pack(side=tk.RIGHT, padx=16, pady=8)
        ButtonPrimary(top_bar, text="Save Custom Stage", command=self._save_stage).pack(side=tk.RIGHT, padx=(0, 8), pady=8)

        # Resizable PanedWindow: Canvas (Left) & Controls (Right)
        self.paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg=THEME['border'], sashrelief=tk.FLAT, sashwidth=4, bd=0)
        self.paned.pack(fill=tk.BOTH, expand=True)

        # Left Board Canvas Pane
        self.left_pane = tk.Frame(self.paned, bg=THEME['bg'])
        self.paned.add(self.left_pane, minsize=480, stretch="always")

        canvas_card = tk.Frame(self.left_pane, bg=THEME['surface'], bd=1, relief=tk.SOLID, highlightbackground=THEME['border'], highlightthickness=1, padx=10, pady=10)
        canvas_card.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self.canvas = tk.Canvas(canvas_card, width=540, height=540, bg=THEME['bg'], highlightthickness=0)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        # Right Controls & Palette Pane
        self.right_pane = tk.Frame(self.paned, bg=THEME['surface'], bd=0, highlightbackground=THEME['border'], highlightthickness=1)
        self.paned.add(self.right_pane, minsize=320, stretch="never")

        content = tk.Frame(self.right_pane, bg=THEME['surface'], padx=16, pady=16)
        content.pack(fill=tk.BOTH, expand=True)

        # Stage Metadata
        tk.Label(content, text="Stage Title:", font=(FONT_NAME, 9, "bold"), bg=THEME['surface'], fg=THEME['text']).pack(anchor="w", pady=(0, 2))
        self.var_title = tk.StringVar(value=self.stage_title)
        tk.Entry(content, textvariable=self.var_title, font=(FONT_NAME, 9), bg=THEME['surface_light'], fg=THEME['text'], insertbackground=THEME['text'], bd=0).pack(fill=tk.X, pady=(0, 8))

        tk.Label(content, text="Stage Description:", font=(FONT_NAME, 9, "bold"), bg=THEME['surface'], fg=THEME['text']).pack(anchor="w", pady=(0, 2))
        self.var_desc = tk.StringVar(value=self.stage_desc)
        tk.Entry(content, textvariable=self.var_desc, font=(FONT_NAME, 9), bg=THEME['surface_light'], fg=THEME['text'], insertbackground=THEME['text'], bd=0).pack(fill=tk.X, pady=(0, 10))

        # Board Size Selection
        tk.Label(content, text="Board Size:", font=(FONT_NAME, 9, "bold"), bg=THEME['surface'], fg=THEME['text']).pack(anchor="w", pady=(0, 2))
        self.var_size = tk.StringVar(value=f"{self.board_size}x{self.board_size}")
        cb_size = ttk.Combobox(content, textvariable=self.var_size, values=["6x6", "9x9"], state="readonly", font=(FONT_NAME, 9))
        cb_size.pack(fill=tk.X, pady=(0, 12))
        cb_size.bind("<<ComboboxSelected>>", self._on_size_change)

        # Piece Palette
        tk.Label(content, text="Placement Palette:", font=(FONT_NAME, 9, "bold"), bg=THEME['surface'], fg=THEME['text']).pack(anchor="w", pady=(0, 4))
        palette_card = tk.Frame(content, bg=THEME['surface_card'], padx=8, pady=8, bd=1, relief=tk.SOLID, highlightbackground=THEME['border'], highlightthickness=1)
        palette_card.pack(fill=tk.X, pady=(0, 12))

        self.palette_buttons = {}

        tools = [
            ("P0_H", "Player Human (H)", '#30D158'),
            ("P0_E", "Player Elephant (E)", '#30D158'),
            ("P0_A", "Player Ant (A)", '#30D158'),
            ("P1_E", "AI Elephant (E)", '#FF453A'),
            ("P1_H", "AI Human (H)", '#FF453A'),
            ("P1_A", "AI Ant (A)", '#FF453A'),
            ("ERASER", "Eraser Tool", THEME['surface_light'])
        ]

        for code, label, col in tools:
            btn = tk.Button(
                palette_card,
                text=label,
                font=(FONT_NAME, 8, "bold" if code == self.active_tool else "normal"),
                bg=THEME['surface_light'],
                fg=col if col != THEME['surface_light'] else THEME['text'],
                bd=1,
                relief=tk.SOLID,
                highlightbackground=THEME['border'],
                cursor='hand2',
                padx=8,
                pady=4,
                command=lambda c=code: self._set_tool(c)
            )
            btn.pack(fill=tk.X, pady=2)
            self.palette_buttons[code] = btn

        # Verification Box
        self.box_verification = tk.Frame(content, bg=THEME['surface_card'], padx=10, pady=8, bd=1, relief=tk.SOLID, highlightbackground=THEME['border'], highlightthickness=1)
        self.box_verification.pack(fill=tk.X, pady=(0, 12))

        self.lbl_verify_status = tk.Label(self.box_verification, text="Winnability: Unverified", font=(FONT_NAME, 9, "bold"), bg=THEME['surface_card'], fg=THEME['warning'])
        self.lbl_verify_status.pack(anchor="w")

        self.lbl_verify_detail = tk.Label(self.box_verification, text="Click verify to check safe path.", font=(FONT_NAME, 8), bg=THEME['surface_card'], fg=THEME['text_muted'], wraplength=270, justify="left")
        self.lbl_verify_detail.pack(anchor="w", pady=(2, 4))

        ButtonSecondary(self.box_verification, text="Verify Winnability (BFS)", command=self._verify_winnability).pack(anchor="w")

        # Bottom Actions
        ButtonPrimary(content, text="Save Stage", command=self._save_stage).pack(fill=tk.X, pady=(0, 4))
        ButtonSecondary(content, text="Clear Board", command=self._clear_board).pack(fill=tk.X, pady=(0, 4))

        if self.edit_stage_id:
            ButtonDanger(content, text="Delete Stage", command=self._delete_stage).pack(fill=tk.X)

        self._refresh_palette_highlight()
        self._draw_board()

    def _set_tool(self, tool_code: str):
        self.active_tool = tool_code
        self._refresh_palette_highlight()

    def _refresh_palette_highlight(self):
        for code, btn in self.palette_buttons.items():
            if code == self.active_tool:
                btn.config(bg=THEME['accent'], fg='#FFFFFF')
            else:
                btn.config(bg=THEME['surface_light'], fg=THEME['text'])

    def _on_size_change(self, event=None):
        val = self.var_size.get()
        new_size = 6 if "6x6" in val else 9
        if new_size != self.board_size:
            self.board_size = new_size
            # Retain only pieces within new bounds
            self.placed_pieces = {k: v for k, v in self.placed_pieces.items() if k[0] < new_size and k[1] < new_size}
            # Ensure player has start piece
            start_coord = (self.board_size - 1, 0)
            if start_coord not in self.placed_pieces:
                self.placed_pieces[start_coord] = (0, 'H')
            self._draw_board()
            self._verify_winnability(silent=True)

    def _draw_board(self):
        self.canvas.delete("all")
        size = self.board_size
        sq_size = 540 // size
        target = (0, size - 1)

        # Draw Cells
        for r in range(size):
            for c in range(size):
                x0 = c * sq_size
                y0 = r * sq_size
                x1 = x0 + sq_size
                y1 = y0 + sq_size

                fill = THEME['board_light'] if (r + c) % 2 == 0 else THEME['board_dark']
                if (r, c) == target:
                    fill = THEME['corner_p1']

                self.canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline=THEME['board_grid'], width=1)

                if (r, c) == target:
                    draw_star(self.canvas, (x0 + x1) / 2, (y0 + y1) / 2, max(6, sq_size * 0.3), fill='#F57F17', outline='')

                # Draw Piece
                if (r, c) in self.placed_pieces:
                    owner, pt = self.placed_pieces[(r, c)]
                    color = '#30D158' if owner == 0 else '#FF453A'
                    pad = max(6, sq_size // 8)
                    self.canvas.create_oval(x0 + pad, y0 + pad, x1 - pad, y1 - pad, fill=color, outline='#FFFFFF', width=2)
                    self.canvas.create_text((x0 + x1) // 2, (y0 + y1) // 2, text=pt, font=(FONT_NAME, max(9, sq_size // 4), "bold"), fill='#FFFFFF')

    def _on_canvas_click(self, event):
        size = self.board_size
        sq_size = 540 // size
        c = event.x // sq_size
        r = event.y // sq_size

        if not (0 <= r < size and 0 <= c < size):
            return

        if self.active_tool == 'ERASER':
            if (r, c) in self.placed_pieces:
                del self.placed_pieces[(r, c)]
        else:
            owner = 0 if self.active_tool.startswith('P0') else 1
            pt = self.active_tool.split('_')[1]
            self.placed_pieces[(r, c)] = (owner, pt)

        self._draw_board()
        self._verify_winnability(silent=True)

    def _clear_board(self):
        self.placed_pieces.clear()
        self.placed_pieces[(self.board_size - 1, 0)] = (0, 'H')
        self._draw_board()
        self._verify_winnability(silent=True)

    def _verify_winnability(self, silent: bool = False) -> bool:
        start_coord = (self.board_size - 1, 0)
        target_coord = (0, self.board_size - 1)

        pieces_list = [(r, c, owner, pt) for (r, c), (owner, pt) in self.placed_pieces.items()]

        # Check that player piece exists
        player_pieces = [p for p in pieces_list if p[2] == 0]
        if not player_pieces:
            self.lbl_verify_status.config(text="Status: No Player Pieces", fg=THEME['danger'])
            self.lbl_verify_detail.config(text="Place at least one green Player piece (e.g. at bottom-left corner).")
            return False

        d, path = bfs_safe_path(self.board_size, pieces_list, start_coord, target_coord, 'H')

        if d is not None:
            s_max = 3 * d
            self.last_verification = {'winnable': True, 's_optimal': d, 'path': path}
            self.lbl_verify_status.config(text=f"Status: WINNABLE (S_optimal = {d})", fg=THEME['success'])
            self.lbl_verify_detail.config(text=f"Safe optimal route found in {d} moves. S_max threshold: {s_max} moves.")
            if not silent:
                modal = ThemedModal(self, "Verification Successful", min_width=340)
                tk.Label(modal.body, text=f"Stage is 100% winnable!\nOptimal Solution: {d} steps.\nStep Limit (S_max): {s_max} steps.", font=(FONT_NAME, 9), bg=THEME['surface'], fg=THEME['text'], justify="center").pack(pady=10)
                ButtonPrimary(modal.footer, text="Great", command=modal.dismiss).pack(side=tk.RIGHT)
            return True
        else:
            self.last_verification = {'winnable': False, 's_optimal': 0, 'path': []}
            self.lbl_verify_status.config(text="Status: UNWINNABLE", fg=THEME['danger'])
            self.lbl_verify_detail.config(text="Target corner is unreachable or trapped in predator attack zones. Adjust pieces.")
            if not silent:
                modal = ThemedModal(self, "Verification Failed", min_width=340)
                tk.Label(modal.body, text="No safe path exists from start to target!\nPlease adjust defender positions to allow a viable safe corridor.", font=(FONT_NAME, 9), bg=THEME['surface'], fg='#FF453A', justify="center").pack(pady=10)
                ButtonPrimary(modal.footer, text="Close", command=modal.dismiss).pack(side=tk.RIGHT)
            return False

    def _save_stage(self):
        if not self._verify_winnability(silent=True):
            modal = ThemedModal(self, "Cannot Save Unwinnable Stage", min_width=360)
            tk.Label(modal.body, text="Stage must be verified as winnable before saving.\nPlease adjust piece layout so a safe path exists to the star corner.", font=(FONT_NAME, 9), bg=THEME['surface'], fg=THEME['danger']).pack(pady=10)
            ButtonPrimary(modal.footer, text="Understood", command=modal.dismiss).pack(side=tk.RIGHT)
            return

        title = self.var_title.get().strip() or "Custom Stage"
        desc = self.var_desc.get().strip() or "Custom tactical scenario."
        pieces_list = [(r, c, owner, pt) for (r, c), (owner, pt) in self.placed_pieces.items()]
        s_opt = self.last_verification.get('s_optimal', 6) if self.last_verification else 6
        path = self.last_verification.get('path', []) if self.last_verification else []

        payload = {
            'id': self.edit_stage_id,
            'title': title,
            'description': desc,
            'board_size': self.board_size,
            's_optimal': s_opt,
            'pieces': pieces_list,
            'optimal_path': path,
            'is_custom': True
        }

        saved_id = storage.save_custom_stage(payload)
        self.app.show_view('puzzle_select')

    def _delete_stage(self):
        if not self.edit_stage_id:
            return
        modal = ThemedModal(self, "Delete Stage", min_width=340)
        tk.Label(modal.body, text="Are you sure you want to delete this custom stage permanently?", font=(FONT_NAME, 9), bg=THEME['surface'], fg=THEME['text']).pack(pady=10)

        def confirm():
            modal.dismiss()
            storage.delete_custom_stage(self.edit_stage_id)
            self.app.show_view('puzzle_select')

        ButtonSecondary(modal.footer, text="Cancel", command=modal.dismiss).pack(side=tk.LEFT)
        ButtonDanger(modal.footer, text="Delete", command=confirm).pack(side=tk.RIGHT)

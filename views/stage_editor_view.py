import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, List, Tuple, Optional

from ui_theme import (
    THEME, FONT_NAME, ButtonPrimary, ButtonSecondary, ButtonDanger,
    ThemedModal, draw_star
)
import storage
from puzzle_logic import find_optimal_winning_path, PuzzleScenario


class StageEditorView(tk.Frame):
    """
    Apple-styled Stage Editor providing full CRUD for custom Chess-Sut puzzle stages.
    Includes visual board editor, piece palette, and manual winnability verification.
    """
    def __init__(self, parent, app, edit_stage: Optional[Any] = None, stage: Optional[Any] = None, stage_to_edit: Optional[Any] = None, **kwargs):
        super().__init__(parent, bg=THEME['bg'])
        self.app = app

        raw = edit_stage if edit_stage is not None else (stage if stage is not None else stage_to_edit)
        if hasattr(raw, 'to_dict'):
            stage_dict = raw.to_dict()
        elif isinstance(raw, dict):
            stage_dict = raw
        else:
            stage_dict = None

        self.edit_stage_id = stage_dict.get('id') if stage_dict else None
        self.board_size = stage_dict.get('board_size', 6) if stage_dict else 6
        self.stage_title = stage_dict.get('title', 'My Custom Stage') if stage_dict else 'My Custom Stage'
        self.stage_desc = stage_dict.get('description', '') if stage_dict else 'Custom tactical puzzle scenario.'

        # Placed pieces: dict mapping (r, c) -> (owner, p_type)
        self.placed_pieces: Dict[Tuple[int, int], Tuple[int, str]] = {}
        if stage_dict and 'pieces' in stage_dict:
            for p in stage_dict['pieces']:
                self.placed_pieces[(p[0], p[1])] = (p[2], p[3])
        else:
            # Starter tactical squadron (multiple pieces for both sides)
            size = self.board_size
            self.placed_pieces[(size - 1, 0)] = (0, 'H')
            self.placed_pieces[(size - 1, 1)] = (0, 'E')
            self.placed_pieces[(size - 2, 0)] = (0, 'A')
            self.placed_pieces[(2, 3)] = (1, 'E')
            self.placed_pieces[(1, 4)] = (1, 'H')

        # Active tool: 'P0_H', 'P0_E', 'P0_A', 'P1_H', 'P1_E', 'P1_A', 'ERASER'
        self.active_tool: str = 'P1_E'
        self.last_verification: Optional[Dict[str, Any]] = None
        self.current_sq_size: int = 70
        self._resize_job = None

        self._build_ui()
        self._bind_shortcuts()

    def _bind_shortcuts(self):
        self.app.bind("<Key-1>", lambda e: self._set_tool('P0_H'))
        self.app.bind("<Key-2>", lambda e: self._set_tool('P0_E'))
        self.app.bind("<Key-3>", lambda e: self._set_tool('P0_A'))
        self.app.bind("<Key-4>", lambda e: self._set_tool('P1_E'))
        self.app.bind("<Key-5>", lambda e: self._set_tool('P1_H'))
        self.app.bind("<Key-6>", lambda e: self._set_tool('P1_A'))
        self.app.bind("<Key-7>", lambda e: self._set_tool('ERASER'))
        self.app.bind("<Key-0>", lambda e: self._set_tool('ERASER'))

    def _unbind_shortcuts(self):
        for k in ["1", "2", "3", "4", "5", "6", "7", "0"]:
            self.app.unbind(f"<Key-{k}>")

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

        # Left Board Canvas Pane (Responsive & Debounced)
        self.left_pane = tk.Frame(self.paned, bg=THEME['bg'])
        self.paned.add(self.left_pane, minsize=440, stretch="always")
        self.left_pane.bind("<Configure>", self._on_pane_resize)

        self.canvas_card = tk.Frame(self.left_pane, bg=THEME['surface'], bd=1, relief=tk.SOLID, highlightbackground=THEME['border'], highlightthickness=1, padx=10, pady=10)
        self.canvas_card.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        init_dim = self.current_sq_size * self.board_size
        self.canvas = tk.Canvas(self.canvas_card, width=init_dim, height=init_dim, bg=THEME['bg'], highlightthickness=0)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Button-2>", self._on_canvas_right_click)
        self.canvas.bind("<Button-3>", self._on_canvas_right_click)

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
        cb_size = ttk.Combobox(content, textvariable=self.var_size, values=["6x6", "7x7", "8x8", "9x9"], state="readonly", font=(FONT_NAME, 9))
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
                font=(FONT_NAME, 9),
                bg=THEME['surface_light'],
                fg=col if col != THEME['surface_light'] else THEME['text'],
                bd=0,
                relief=tk.FLAT,
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
        ButtonSecondary(content, text="Reset to Default Squad", command=self._clear_board).pack(fill=tk.X, pady=(0, 4))

        if self.edit_stage_id:
            ButtonDanger(content, text="Delete Stage", command=self._delete_stage).pack(fill=tk.X, pady=(0, 4))

        # Clean Hotkey Footer
        footer = tk.Frame(content, bg=THEME['surface'], pady=6)
        footer.pack(fill=tk.X, pady=(6, 0))
        tk.Label(
            footer,
            text="Hotkeys: [1-3] Player Units  |  [4-6] AI Units  |  [7/0] Eraser\nRight-click: Quick Erase",
            font=(FONT_NAME, 8),
            bg=THEME['surface'],
            fg=THEME['text_muted'],
            justify="center"
        ).pack(fill=tk.X)

        self._refresh_palette_highlight()
        self._draw_board()

    def _on_pane_resize(self, event):
        if self._resize_job is not None:
            try:
                self.after_cancel(self._resize_job)
            except Exception:
                pass
        self._resize_job = self.after(35, lambda w=event.width, h=event.height: self._apply_pane_resize(w, h))

    def _apply_pane_resize(self, width: int, height: int):
        self._resize_job = None
        dim = max(300, min(width - 32, height - 32, 600))
        new_sq = dim // self.board_size
        total_dim = new_sq * self.board_size

        if new_sq == self.current_sq_size and self.canvas.winfo_width() == total_dim:
            return

        self.current_sq_size = new_sq
        self.canvas.config(width=total_dim, height=total_dim)
        self._draw_board()

    def _set_tool(self, tool_code: str):
        self.active_tool = tool_code
        self._refresh_palette_highlight()

    def _refresh_palette_highlight(self):
        for code, btn in self.palette_buttons.items():
            if code == self.active_tool:
                btn.config(bg=THEME['accent'], fg='#FFFFFF')
            else:
                col = '#30D158' if code.startswith('P0') else ('#FF453A' if code.startswith('P1') else THEME['text'])
                btn.config(bg=THEME['surface_light'], fg=col)

    def _on_size_change(self, event=None):
        val = self.var_size.get()
        try:
            new_size = int(val.split('x')[0])
        except Exception:
            new_size = 6
        if new_size != self.board_size:
            self.board_size = new_size
            self.placed_pieces = {k: v for k, v in self.placed_pieces.items() if k[0] < new_size and k[1] < new_size}
            start_coord = (self.board_size - 1, 0)
            if start_coord not in self.placed_pieces:
                self.placed_pieces[start_coord] = (0, 'H')
            w = max(440, self.left_pane.winfo_width())
            h = max(440, self.left_pane.winfo_height())
            self._apply_pane_resize(w, h)
            self._invalidate_verification()

    def _draw_board(self):
        self.canvas.delete("all")
        size = self.board_size
        sq_size = self.current_sq_size
        target = (0, size - 1)
        player_home = (size - 1, 0)

        for r in range(size):
            for c in range(size):
                x0 = c * sq_size
                y0 = r * sq_size
                x1 = x0 + sq_size
                y1 = y0 + sq_size

                fill = THEME['board_light'] if (r + c) % 2 == 0 else THEME['board_dark']
                if (r, c) == target:
                    fill = THEME['corner_p1']
                elif (r, c) == player_home:
                    fill = THEME['corner_p2']

                self.canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline=THEME['board_grid'], width=1)

                if (r, c) == target:
                    draw_star(self.canvas, (x0 + x1) / 2, (y0 + y1) / 2, max(6, sq_size * 0.3), fill='#F57F17', outline='')
                elif (r, c) == player_home:
                    draw_star(self.canvas, (x0 + x1) / 2, (y0 + y1) / 2, max(6, sq_size * 0.3), fill='#C62828', outline='')

                if (r, c) in self.placed_pieces:
                    owner, pt = self.placed_pieces[(r, c)]
                    color = '#30D158' if owner == 0 else '#FF453A'
                    pad = max(4, sq_size // 8)
                    self.canvas.create_oval(x0 + pad, y0 + pad, x1 - pad, y1 - pad, fill=color, outline='#FFFFFF', width=2)
                    self.canvas.create_text((x0 + x1) // 2, (y0 + y1) // 2, text=pt, font=(FONT_NAME, max(9, sq_size // 4), "bold"), fill='#FFFFFF')

    def _on_canvas_right_click(self, event):
        size = self.board_size
        sq_size = self.current_sq_size
        c = event.x // sq_size
        r = event.y // sq_size

        if not (0 <= r < size and 0 <= c < size):
            return

        if (r, c) in self.placed_pieces:
            del self.placed_pieces[(r, c)]
            self._draw_board()
            self._invalidate_verification()

    def _on_canvas_click(self, event):
        size = self.board_size
        sq_size = self.current_sq_size
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
        self._invalidate_verification()

    def _clear_board(self):
        self.placed_pieces.clear()
        size = self.board_size
        self.placed_pieces[(size - 1, 0)] = (0, 'H')
        self.placed_pieces[(size - 1, 1)] = (0, 'E')
        self.placed_pieces[(size - 2, 0)] = (0, 'A')
        self.placed_pieces[(2, 3)] = (1, 'E')
        self.placed_pieces[(1, 4)] = (1, 'H')
        self._draw_board()
        self._invalidate_verification()

    def _invalidate_verification(self):
        self.last_verification = None
        self.lbl_verify_status.config(text="Winnability: Unverified", fg=THEME['warning'])
        self.lbl_verify_detail.config(text="Board changed. Click verify to check safe path.")

    def _verify_winnability(self, silent: bool = False) -> bool:
        target_coord = (0, self.board_size - 1)
        pieces_list = [(r, c, owner, pt) for (r, c), (owner, pt) in self.placed_pieces.items()]

        player_pieces = [p for p in pieces_list if p[2] == 0]
        if not player_pieces:
            self.lbl_verify_status.config(text="Status: No Player Pieces", fg=THEME['danger'])
            self.lbl_verify_detail.config(text="Place at least one green Player piece on the board.")
            return False

        d, path, best_pc = find_optimal_winning_path(self.board_size, pieces_list, target_coord)

        if d is not None:
            s_max = 3 * d
            piece_name = {'H': 'Human', 'E': 'Elephant', 'A': 'Ant'}.get(best_pc[2], best_pc[2]) if best_pc else "Piece"
            self.last_verification = {'winnable': True, 's_optimal': d, 'path': path, 'best_piece': best_pc}
            self.lbl_verify_status.config(text=f"Status: WINNABLE ({d} Steps)", fg=THEME['success'])
            self.lbl_verify_detail.config(text=f"Safe path found in {d} moves using {piece_name}. Move limit: {s_max} moves.")
            if not silent:
                modal = ThemedModal(self, "Verification Successful", min_width=340)
                tk.Label(modal.body, text=f"Stage is 100% winnable!\nOptimal Steps: {d}\nMove Limit: {s_max}\nBest Lead: {piece_name}", font=(FONT_NAME, 9), bg=THEME['surface'], fg=THEME['text'], justify="center").pack(pady=10)
                ButtonPrimary(modal.footer, text="Understood", command=modal.dismiss).pack(side=tk.RIGHT)
            return True
        else:
            self.last_verification = {'winnable': False, 's_optimal': 0, 'path': [], 'best_piece': None}
            self.lbl_verify_status.config(text="Status: UNWINNABLE", fg=THEME['danger'])
            self.lbl_verify_detail.config(text="Target corner is unreachable or trapped in predator zones. Adjust pieces.")
            if not silent:
                modal = ThemedModal(self, "Verification Failed", min_width=340)
                tk.Label(modal.body, text="No safe path exists from any player piece to the star corner!\nPlease adjust defender positions or add supporting player units.", font=(FONT_NAME, 9), bg=THEME['surface'], fg=THEME['danger'], justify="center").pack(pady=10)
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

        storage.save_custom_stage(payload)
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

    def _cleanup(self):
        self._unbind_shortcuts()
        if self._resize_job is not None:
            try:
                self.after_cancel(self._resize_job)
            except Exception:
                pass
            self._resize_job = None

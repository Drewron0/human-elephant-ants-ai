import tkinter as tk
from tkinter import ttk
import math
from typing import Callable, List, Optional, Any, Tuple

# Restrained system typography adhering to Apple Design guidelines
FONT_NAME = "Segoe UI"

# Apple Design System Dark Palette: restrained, subtle depth, high legibility
THEME = {
    'bg': '#121214',
    'surface': '#1C1C1E',
    'surface_light': '#2C2C2E',
    'surface_card': '#242426',
    'border': '#38383A',
    'border_subtle': '#262628',
    'text': '#F2F2F7',
    'text_muted': '#8E8E93',
    'accent': '#0A84FF',
    'accent_hover': '#0071E3',
    'danger': '#FF453A',
    'danger_hover': '#D70015',
    'success': '#30D158',
    'warning': '#FF9F0A',
    'board_light': '#E5E5EA',
    'board_dark': '#AEAEB2',
    'board_grid': '#636366',
    'corner_p1': '#FFE082',
    'corner_p2': '#FFCDD2',
    'move_dot': '#1C1C1E',
    'capture_square': '#FF453A',
    'select_square': '#FFE082',
    'last_move': '#D1D1D6'
}

COLOR_PALETTES = {
    'Emerald Green': '#30D158',
    'Sapphire Blue': '#0A84FF',
    'Ruby Red': '#FF453A',
    'Amethyst Purple': '#BF5AF2',
    'Amber Orange': '#FF9F0A',
    'Turquoise Cyan': '#64D2FF'
}

HOTKEYS = {
    'undo': {'seq': '<Control-z>', 'key_str': 'Ctrl+Z', 'label': 'Undo'},
    'restart': {'seq': '<Control-r>', 'key_str': 'Ctrl+R', 'label': 'Restart'},
    'surrender': {'seq': '<Control-e>', 'key_str': 'Ctrl+E', 'label': 'Surrender'},
    'save': {'seq': '<Control-s>', 'key_str': 'Ctrl+S', 'label': 'Save Slot'}
}


def setup_ttk_styles(root: tk.Tk):
    style = ttk.Style(root)
    style.theme_use('clam')

    # Dark Combobox Styling
    style.configure(
        'TCombobox',
        background=THEME['surface_light'],
        foreground=THEME['text'],
        fieldbackground=THEME['surface_light'],
        darkcolor=THEME['border'],
        lightcolor=THEME['border'],
        bordercolor=THEME['border'],
        arrowcolor=THEME['text'],
        padding=5
    )
    style.map(
        'TCombobox',
        fieldbackground=[('readonly', THEME['surface_light']), ('focus', THEME['surface_light'])],
        foreground=[('readonly', THEME['text'])],
        background=[('readonly', THEME['surface_light'])]
    )

    # Dark Treeview Styling
    style.configure(
        'Treeview',
        background=THEME['surface'],
        foreground=THEME['text'],
        fieldbackground=THEME['surface'],
        rowheight=28,
        font=(FONT_NAME, 9),
        borderwidth=0
    )
    style.configure(
        'Treeview.Heading',
        background=THEME['surface_light'],
        foreground=THEME['text'],
        font=(FONT_NAME, 9, 'bold'),
        borderwidth=1,
        relief=tk.FLAT
    )
    style.map(
        'Treeview',
        background=[('selected', THEME['accent'])],
        foreground=[('selected', '#FFFFFF')]
    )

    # Dark Scrollbar Styling
    style.configure(
        'Vertical.TScrollbar',
        background=THEME['surface_light'],
        darkcolor=THEME['surface'],
        lightcolor=THEME['surface'],
        troughcolor=THEME['surface'],
        bordercolor=THEME['surface'],
        arrowcolor=THEME['text_muted']
    )
    style.configure(
        'Horizontal.TScrollbar',
        background=THEME['surface_light'],
        darkcolor=THEME['surface'],
        lightcolor=THEME['surface'],
        troughcolor=THEME['surface'],
        bordercolor=THEME['surface'],
        arrowcolor=THEME['text_muted']
    )


def draw_star(canvas: tk.Canvas, cx: float, cy: float, radius: float, fill: str, outline: str = ''):
    points = []
    inner_radius = radius * 0.45
    for i in range(10):
        r = radius if i % 2 == 0 else inner_radius
        angle = i * (math.pi / 5) - (math.pi / 2)
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.extend([x, y])
    canvas.create_polygon(points, fill=fill, outline=outline, width=1)


def draw_board_thumbnail(canvas: tk.Canvas, board_size: int, pieces: List[Tuple[int, int, int, str]],
                         target_coord: Tuple[int, int], width: int = 140, height: int = 140,
                         p1_color: str = '#30D158', p2_color: str = '#FF453A') -> None:
    """Renders a clean, scalable mini-board thumbnail for the stage selection grid."""
    canvas.delete("all")
    usable_dim = min(width, height) - 8
    cell_size = max(10, usable_dim // board_size)
    total_grid_w = cell_size * board_size
    total_grid_h = cell_size * board_size
    offset_x = (width - total_grid_w) // 2
    offset_y = (height - total_grid_h) // 2

    canvas.create_rectangle(offset_x - 1, offset_y - 1, offset_x + total_grid_w + 1, offset_y + total_grid_h + 1,
                            fill=THEME['surface_card'], outline=THEME['border'], width=1)

    player_home = (board_size - 1, 0)

    # Draw cells
    for r in range(board_size):
        for c in range(board_size):
            x0 = offset_x + c * cell_size
            y0 = offset_y + r * cell_size
            x1 = x0 + cell_size
            y1 = y0 + cell_size

            fill = THEME['board_light'] if (r + c) % 2 == 0 else THEME['board_dark']
            if (r, c) == target_coord:
                fill = THEME['corner_p1']
            elif (r, c) == player_home:
                fill = THEME['corner_p2']

            canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline=THEME['board_grid'], width=1)

            if (r, c) == target_coord:
                draw_star(canvas, (x0 + x1) / 2, (y0 + y1) / 2, max(4, cell_size * 0.32), fill='#F57F17', outline='')
            elif (r, c) == player_home:
                draw_star(canvas, (x0 + x1) / 2, (y0 + y1) / 2, max(4, cell_size * 0.32), fill='#C62828', outline='')

    # Draw pieces
    for r, c, owner, pt in pieces:
        if 0 <= r < board_size and 0 <= c < board_size:
            x0 = offset_x + c * cell_size
            y0 = offset_y + r * cell_size
            x1 = x0 + cell_size
            y1 = y0 + cell_size
            pad = max(2, cell_size // 6)
            color = p1_color if owner == 0 else p2_color

            canvas.create_oval(x0 + pad, y0 + pad, x1 - pad, y1 - pad, fill=color, outline='#FFFFFF', width=1)
            if cell_size >= 16:
                cx = (x0 + x1) // 2
                cy = (y0 + y1) // 2
                canvas.create_text(cx, cy, text=pt, font=(FONT_NAME, max(7, cell_size // 3), "bold"), fill='#FFFFFF')


def bind_mousewheel(widget: tk.Widget, scroll_target: tk.Widget) -> None:
    """
    Recursively binds mouse wheel and touchpad events so scrolling anywhere over
    the widget or its descendants smoothly scrolls the target canvas/listbox.
    """
    def _on_mousewheel(event):
        if event.delta:
            scroll_units = int(-1 * (event.delta / 120))
            if scroll_units == 0:
                scroll_units = -1 if event.delta > 0 else 1
            scroll_target.yview_scroll(scroll_units, "units")
        elif event.num == 4:
            scroll_target.yview_scroll(-1, "units")
        elif event.num == 5:
            scroll_target.yview_scroll(1, "units")
        return "break"

    def _bind_recursive(w):
        w.bind("<MouseWheel>", _on_mousewheel, add="+")
        w.bind("<Button-4>", _on_mousewheel, add="+")
        w.bind("<Button-5>", _on_mousewheel, add="+")
        for child in w.winfo_children():
            _bind_recursive(child)

    _bind_recursive(widget)


class ButtonPrimary(tk.Button):
    def __init__(self, parent, text: str, command: Optional[Callable] = None, width: Optional[int] = None, **kwargs):
        super().__init__(
            parent,
            text=text,
            command=command,
            font=(FONT_NAME, 9),
            bg=THEME['accent'],
            fg='#FFFFFF',
            activebackground=THEME['accent_hover'],
            activeforeground='#FFFFFF',
            bd=0,
            relief=tk.FLAT,
            cursor='hand2',
            padx=12,
            pady=6,
            width=width,
            **kwargs
        )


class ButtonSecondary(tk.Button):
    def __init__(self, parent, text: str, command: Optional[Callable] = None, width: Optional[int] = None, **kwargs):
        super().__init__(
            parent,
            text=text,
            command=command,
            font=(FONT_NAME, 9),
            bg=THEME['surface_light'],
            fg=THEME['text'],
            activebackground=THEME['border'],
            activeforeground=THEME['text'],
            bd=0,
            relief=tk.FLAT,
            cursor='hand2',
            padx=12,
            pady=6,
            width=width,
            **kwargs
        )


class ButtonDanger(tk.Button):
    def __init__(self, parent, text: str, command: Optional[Callable] = None, width: Optional[int] = None, **kwargs):
        super().__init__(
            parent,
            text=text,
            command=command,
            font=(FONT_NAME, 9),
            bg=THEME['danger'],
            fg='#FFFFFF',
            activebackground=THEME['danger_hover'],
            activeforeground='#FFFFFF',
            bd=0,
            relief=tk.FLAT,
            cursor='hand2',
            padx=12,
            pady=6,
            width=width,
            **kwargs
        )


class SegmentedControl(tk.Frame):
    """Clean custom segmented button group with Apple-like pill aesthetics."""
    def __init__(self, parent, options: List[Tuple[str, str]], default_val: str, on_change: Optional[Callable[[str], None]] = None):
        super().__init__(parent, bg=THEME['surface_card'], bd=1, relief=tk.SOLID, highlightbackground=THEME['border'], highlightthickness=1)
        self.options = options
        self.selected_val = default_val
        self.on_change = on_change
        self.buttons = {}

        for text, val in options:
            btn = tk.Button(
                self,
                text=text,
                font=(FONT_NAME, 9),
                bd=0,
                relief=tk.FLAT,
                cursor='hand2',
                padx=12,
                pady=4,
                command=lambda v=val: self.select(v)
            )
            btn.pack(side=tk.LEFT, padx=1, pady=1)
            self.buttons[val] = btn

        self._refresh()

    def select(self, val: str):
        self.selected_val = val
        self._refresh()
        if self.on_change:
            self.on_change(val)

    def _refresh(self):
        for val, btn in self.buttons.items():
            if val == self.selected_val:
                btn.config(bg=THEME['accent'], fg='#FFFFFF', activebackground=THEME['accent'], activeforeground='#FFFFFF')
            else:
                btn.config(bg=THEME['surface_card'], fg=THEME['text_muted'], activebackground=THEME['border'], activeforeground=THEME['text'])

    def get(self) -> str:
        return self.selected_val


class ThemedModal(tk.Frame):
    """
    In-window modal dialog that dynamically fits content and guarantees
    the header and footer buttons are never cutoff on any screen resolution.
    """
    def __init__(self, parent, title: str, min_width: int = 460):
        super().__init__(parent, bg='#000000')
        self.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.backdrop = tk.Frame(self, bg='#0E0E10')
        self.backdrop.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.card = tk.Frame(
            self.backdrop,
            bg=THEME['surface'],
            bd=1,
            relief=tk.SOLID,
            highlightbackground=THEME['border'],
            highlightthickness=1
        )
        self.card.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Header
        header = tk.Frame(self.card, bg=THEME['surface'])
        header.pack(fill=tk.X, padx=20, pady=(16, 10))
        tk.Label(
            header,
            text=title,
            font=(FONT_NAME, 12, 'bold'),
            bg=THEME['surface'],
            fg=THEME['text']
        ).pack(side=tk.LEFT)

        # Body container
        self.body = tk.Frame(self.card, bg=THEME['surface'], width=min_width)
        self.body.pack(fill=tk.BOTH, expand=True, padx=20, pady=8)

        # Pinned Footer (Action buttons)
        self.footer = tk.Frame(self.card, bg=THEME['surface'])
        self.footer.pack(fill=tk.X, padx=20, pady=(12, 16))

    def dismiss(self):
        self.destroy()

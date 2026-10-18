import tkinter as tk
from tkinter import ttk
import math
from typing import Callable, List, Optional, Any, Tuple

FONT_NAME = "Trebuchet MS"

THEME = {
    'bg': '#191A21',
    'surface': '#22232E',
    'surface_light': '#2E303E',
    'border': '#3B3D4E',
    'text': '#EBECEF',
    'text_muted': '#8D90A3',
    'accent': '#3D5AFE',
    'accent_hover': '#536DFE',
    'danger': '#E53935',
    'danger_hover': '#D32F2F',
    'board_light': '#E8ECEF',
    'board_dark': '#9AA5B1',
    'board_grid': '#57606A',
    'corner_p1': '#FFE082',
    'corner_p2': '#FFCDD2',
    'move_dot': '#000000',
    'capture_square': '#D32F2F',
    'select_square': '#FFF59D',
    'last_move': '#CFD8DC'
}

COLOR_PALETTES = {
    'Emerald Green': '#2ECC71',
    'Sapphire Blue': '#3498DB',
    'Ruby Red': '#E74C3C',
    'Amethyst Purple': '#9B59B6',
    'Amber Orange': '#E67E22',
    'Turquoise Cyan': '#1ABC9C'
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
        padding=4
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


class ButtonPrimary(tk.Button):
    def __init__(self, parent, text: str, command: Optional[Callable] = None, width: Optional[int] = None, **kwargs):
        super().__init__(
            parent,
            text=text,
            command=command,
            font=(FONT_NAME, 10, 'bold'),
            bg=THEME['accent'],
            fg='#FFFFFF',
            activebackground=THEME['accent_hover'],
            activeforeground='#FFFFFF',
            bd=0,
            relief=tk.FLAT,
            cursor='hand2',
            padx=14,
            pady=7,
            width=width,
            **kwargs
        )


class ButtonSecondary(tk.Button):
    def __init__(self, parent, text: str, command: Optional[Callable] = None, width: Optional[int] = None, **kwargs):
        super().__init__(
            parent,
            text=text,
            command=command,
            font=(FONT_NAME, 9, 'bold'),
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
            font=(FONT_NAME, 9, 'bold'),
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
    """Clean custom segmented button group that never turns black or glitches."""
    def __init__(self, parent, options: List[Tuple[str, str]], default_val: str, on_change: Optional[Callable[[str], None]] = None):
        super().__init__(parent, bg=THEME['surface_light'], bd=1, relief=tk.SOLID, highlightbackground=THEME['border'], highlightthickness=1)
        self.options = options
        self.selected_val = default_val
        self.on_change = on_change
        self.buttons = {}

        for text, val in options:
            btn = tk.Button(
                self,
                text=text,
                font=(FONT_NAME, 9, 'bold'),
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
                btn.config(bg=THEME['surface_light'], fg=THEME['text'], activebackground=THEME['border'], activeforeground=THEME['text'])

    def get(self) -> str:
        return self.selected_val


class ThemedModal(tk.Frame):
    """
    Robust in-window modal dialog that dynamically fits content and guarantees
    the header and footer buttons are never cutoff on any screen resolution.
    """
    def __init__(self, parent, title: str, min_width: int = 460):
        super().__init__(parent, bg='#000000')
        self.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.backdrop = tk.Frame(self, bg='#101116')
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
            font=(FONT_NAME, 13, 'bold'),
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

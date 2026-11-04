import tkinter as tk
from tkinter import ttk
import math
from functools import lru_cache
from pathlib import Path
from typing import Callable, List, Optional, Any, Tuple
from PIL import Image, ImageTk
from game_logic import BEATS, PIECE_NAMES

# Restrained system typography adhering to Apple Design guidelines
FONT_NAME = "Segoe UI"

# Light semantic surfaces keep boards, forms and dialogs in one appearance.
THEME = {
    'bg': '#F4F5F7',
    'surface': '#FFFFFF',
    'surface_light': '#ECEEF2',
    'surface_card': '#F7F8FA',
    'border': '#D7DAE0',
    'border_subtle': '#E8EAEE',
    'text': '#202124',
    'text_muted': '#60636B',
    'accent': '#0066CC',
    'accent_hover': '#0055AA',
    'danger': '#B42318',
    'danger_hover': '#8F1D14',
    'danger_soft': '#FCECEB',
    'success': '#237A43',
    'warning': '#8C5B00',
    'backdrop': '#DDE0E6',
    'board_light': '#F3F5F8',
    'board_dark': '#D3DAE4',
    'board_grid': '#BEC7D3',
    'corner_p1': '#FBE7AB',
    'corner_p2': '#F8D6D2',
    'move_dot': '#303F50',
    'capture_square': '#F3B6B0',
    'select_square': '#A7CCF5',
    'last_move': '#DCE9F8'
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
    'surrender': {'seq': '<Control-e>', 'key_str': 'Ctrl+E', 'label': 'Surrender'}
}


def setup_ttk_styles(root: tk.Tk):
    style = ttk.Style(root)
    style.theme_use('clam')
    root.option_add('*Font', (FONT_NAME, 10))
    root.option_add('*Entry.background', THEME['surface_light'])
    root.option_add('*Entry.foreground', THEME['text'])
    root.option_add('*Entry.insertBackground', THEME['text'])
    root.option_add('*Entry.selectBackground', THEME['accent'])
    root.option_add('*Entry.selectForeground', '#FFFFFF')
    root.option_add('*Entry.highlightColor', THEME['accent'])
    root.option_add('*Entry.highlightBackground', THEME['border'])
    root.option_add('*Entry.highlightThickness', 1)
    root.option_add('*Listbox.highlightThickness', 0)
    root.option_add('*TCombobox*Listbox.background', THEME['surface'])
    root.option_add('*TCombobox*Listbox.foreground', THEME['text'])
    root.option_add('*TCombobox*Listbox.selectBackground', THEME['accent'])
    root.option_add('*TCombobox*Listbox.selectForeground', '#FFFFFF')

    # Combobox and popup colors use the same light appearance.
    style.configure(
        'TCombobox',
        background=THEME['surface_light'],
        foreground=THEME['text'],
        fieldbackground=THEME['surface_light'],
        darkcolor=THEME['border'],
        lightcolor=THEME['border'],
        bordercolor=THEME['border'],
        arrowcolor=THEME['text'],
        padding=8
    )
    style.map(
        'TCombobox',
        fieldbackground=[('readonly', THEME['surface_light']), ('focus', THEME['surface_light'])],
        foreground=[('readonly', THEME['text'])],
        background=[('readonly', THEME['surface_light'])],
        bordercolor=[('focus', THEME['accent'])],
        selectbackground=[('readonly', THEME['surface_light'])],
        selectforeground=[('readonly', THEME['text'])]
    )

    # Tables use space and alignment rather than heavy header bands.
    style.configure(
        'Treeview',
        background=THEME['surface'],
        foreground=THEME['text'],
        fieldbackground=THEME['surface'],
        rowheight=36,
        font=(FONT_NAME, 10),
        borderwidth=0
    )
    style.configure(
        'Treeview.Heading',
        background=THEME['surface'],
        foreground=THEME['text_muted'],
        font=(FONT_NAME, 10, 'bold'),
        borderwidth=0,
        relief=tk.FLAT
    )
    style.map(
        'Treeview',
        background=[('selected', THEME['accent'])],
        foreground=[('selected', '#FFFFFF')]
    )

    style.configure('TProgressbar', background=THEME['accent'],
                    troughcolor=THEME['surface_light'], borderwidth=0)

    # Neutral scrollbars recede behind the content.
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


@lru_cache(maxsize=3)
def _piece_art(piece_type: str) -> Image.Image:
    filename = {'H': 'orang.png', 'E': 'gajah.png', 'A': 'semut.png'}[piece_type]
    with Image.open(Path(__file__).resolve().parent / 'assets' / filename) as source:
        image = source.convert('RGBA')
    return image.crop(image.getchannel('A').getbbox())


def draw_piece_image(canvas: tk.Canvas, cx: int, cy: int, piece_type: str, size: int) -> None:
    """Keep Tk image references on the canvas, caching only its current piece size."""
    if getattr(canvas, '_piece_image_size', None) != size:
        canvas._piece_image_size = size
        canvas._piece_images = {}
    if piece_type not in canvas._piece_images:
        image = _piece_art(piece_type).copy()
        image.thumbnail((size, size), Image.Resampling.LANCZOS)
        canvas._piece_images[piece_type] = ImageTk.PhotoImage(image, master=canvas)
    canvas.create_image(cx, cy, image=canvas._piece_images[piece_type])


class CaptureLegend(tk.Frame):
    """Show the actual capture cycle with the same artwork as the board."""
    def __init__(self, parent):
        bg = parent.cget('bg')
        super().__init__(parent, bg=bg)
        tk.Label(self, text='Legend', font=(FONT_NAME, 12, 'bold'),
                 bg=bg, fg=THEME['text']).pack(anchor='w', pady=(0, 8))
        for attacker, target in BEATS.items():
            row = tk.Frame(self, bg=bg)
            row.pack(fill=tk.X, pady=2)
            art = tk.Canvas(row, width=36, height=36, bg=bg, highlightthickness=0)
            art.pack(side=tk.LEFT)
            draw_piece_image(art, 18, 18, attacker, 32)
            tk.Label(row, text=f'{PIECE_NAMES[attacker]} beats {PIECE_NAMES[target]}',
                     font=(FONT_NAME, 10), bg=bg, fg=THEME['text']).pack(
                         side=tk.LEFT, padx=8)
            target_art = tk.Canvas(row, width=36, height=36, bg=bg, highlightthickness=0)
            target_art.pack(side=tk.LEFT)
            draw_piece_image(target_art, 18, 18, target, 32)
        note = tk.Label(self, text='Same types cannot capture each other.',
                        font=(FONT_NAME, 9), bg=bg, fg=THEME['text_muted'],
                        justify=tk.LEFT, anchor='w')
        note.pack(fill=tk.X, pady=(8, 0))
        self.bind('<Configure>', lambda event: note.config(wraplength=max(1, event.width)))


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
            cx = (x0 + x1) // 2
            cy = (y0 + y1) // 2
            draw_piece_image(canvas, cx, cy, pt, max(1, cell_size - 2 * pad - 2))


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


def _button_feedback(button: tk.Button, hover: str):
    normal = button.cget('bg')
    button.configure(highlightthickness=2, highlightbackground=normal,
                     highlightcolor=THEME['accent'], disabledforeground=THEME['text_muted'])
    button.bind('<Enter>', lambda event: button.configure(bg=hover)
                if str(button.cget('state')) != tk.DISABLED else None)
    button.bind('<Leave>', lambda event: button.configure(bg=normal))


class ButtonPrimary(tk.Button):
    def __init__(self, parent, text: str, command: Optional[Callable] = None, width: Optional[int] = None, **kwargs):
        super().__init__(
            parent,
            text=text,
            command=command,
            font=(FONT_NAME, 10),
            bg=THEME['accent'],
            fg='#FFFFFF',
            activebackground=THEME['accent_hover'],
            activeforeground='#FFFFFF',
            bd=0,
            relief=tk.FLAT,
            cursor='hand2',
            padx=16,
            pady=10,
            width=width,
            **kwargs
        )
        _button_feedback(self, THEME['accent_hover'])


class ButtonSecondary(tk.Button):
    def __init__(self, parent, text: str, command: Optional[Callable] = None, width: Optional[int] = None, **kwargs):
        super().__init__(
            parent,
            text=text,
            command=command,
            font=(FONT_NAME, 10),
            bg=THEME['surface_light'],
            fg=THEME['text'],
            activebackground=THEME['border'],
            activeforeground=THEME['text'],
            bd=0,
            relief=tk.FLAT,
            cursor='hand2',
            padx=16,
            pady=10,
            width=width,
            **kwargs
        )
        _button_feedback(self, THEME['border'])


class ButtonDanger(tk.Button):
    def __init__(self, parent, text: str, command: Optional[Callable] = None, width: Optional[int] = None, **kwargs):
        super().__init__(
            parent,
            text=text,
            command=command,
            font=(FONT_NAME, 10),
            bg=THEME['danger_soft'],
            fg=THEME['danger'],
            activebackground=THEME['danger'],
            activeforeground='#FFFFFF',
            bd=0,
            relief=tk.FLAT,
            cursor='hand2',
            padx=16,
            pady=10,
            width=width,
            **kwargs
        )
        _button_feedback(self, THEME['danger_soft'])


class SegmentedControl(tk.Frame):
    """Clean custom segmented button group with Apple-like pill aesthetics."""
    def __init__(self, parent, options: List[Tuple[str, str]], default_val: str, on_change: Optional[Callable[[str], None]] = None):
        super().__init__(parent, bg=THEME['surface_light'], bd=0)
        self.options = options
        self.selected_val = default_val
        self.on_change = on_change
        self.buttons = {}

        for text, val in options:
            btn = tk.Button(
                self,
                text=text,
                font=(FONT_NAME, 10),
                bd=0,
                relief=tk.FLAT,
                cursor='hand2',
                padx=12,
                pady=8,
                highlightcolor=THEME['accent'],
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
                btn.config(bg=THEME['surface'], fg=THEME['text'], activebackground=THEME['surface'], activeforeground=THEME['text'], relief=tk.SUNKEN)
            else:
                btn.config(bg=THEME['surface_light'], fg=THEME['text_muted'], activebackground=THEME['border'], activeforeground=THEME['text'], relief=tk.FLAT)

    def get(self) -> str:
        return self.selected_val


class ThemedModal(tk.Frame):
    """
    In-window modal dialog that dynamically fits content and guarantees
    the header and footer buttons are never cutoff on any screen resolution.
    """
    def __init__(self, parent, title: str, min_width: int = 460):
        super().__init__(parent, bg=THEME['backdrop'])
        self.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.backdrop = tk.Frame(self, bg=THEME['backdrop'])
        self.backdrop.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.card = tk.Frame(
            self.backdrop,
            bg=THEME['surface'],
            bd=0,
            relief=tk.FLAT,
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
            font=(FONT_NAME, 14, 'bold'),
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

---
name: desktop-game-ui
description: Design and implement modern, high-DPI desktop games and tactical board interfaces in Python (Tkinter + Pillow) with Linear and Apple HIG aesthetics, procedural supersampled vector rendering, tactile keyboard-navigable widgets, and clean decoupled game-AI architecture.
---

# Modern Desktop Game UI & Architecture Framework

This skill guides you in designing and building polished, modern desktop games and tactical board interfaces in Python using Tkinter and Pillow. It establishes a high-craft aesthetic inspired by Apple HIG and Linear, avoiding common "AI slop" patterns (walls of text, emojis, gaudy casino gradients, pixelated native Tkinter widgets).

---

## 1. Core Aesthetic Principles (Anti-Slop Standards)

1. **Strict ASCII Character Hygiene**:
   - Never use emojis or non-standard Unicode glyphs (e.g., bullet symbols `\u2022`, curly quotes, or non-keyboard symbols).
   - Always use standard keyboard characters (`-`, `*`, `...`, `[-]`, `[+]`).

2. **Restrained, Natural Color System**:
   - Backgrounds: Warm paper / linen tint (`#F7F7F4` or `#F4F3EE`). Never pure `#000000` or stark `#FFFFFF` canvas.
   - Surfaces: Crisp white cards (`#FFFFFF`) with subtle 1px borders (`#E1E3DC` or `#DDD7CC`).
   - Text: High-contrast ink (`#1A1A1B`) for primary headings, muted ink (`#595C57`) for secondary info.
   - Accents: Purposeful nature & timber tones (Forest Pine `#2F6B2B`, Warm Oak / Clay Red `#B3362B`, Amber Gold `#F7CF3D`). Avoid golden casino gradients.

3. **Confident Typography & Concise Copy**:
   - Never generate walls of wordy robotic filler text.
   - Use punchy, confident titles (`hero: 46pt`, `title: 22pt`) and minimalist category pills (`SOLO PLAY`, `CAMPAIGN`).
   - Communicate mechanics through visual diagrams (e.g., circular combat cycles, board thumbnails) rather than verbose text.

4. **Breathing Room & Margins**:
   - Always apply generous outer margins (32-40px) and inner card padding (16-24px).
   - Never allow text or buttons to touch card borders.

---

## 2. Supersampled Procedural Vector Graphics (Pillow + Tkinter)

Native Tkinter canvas drawing lacks anti-aliased curves and produces jagged edges. Solve this by rendering all procedural graphics in Pillow at 3x supersampling and downscaling with `LANCZOS`.

```python
import math
from functools import lru_cache
from PIL import Image, ImageDraw

SUPERSAMPLE = 3

def _hex_rgba(color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    val = color.lstrip("#")
    return int(val[0:2], 16), int(val[2:4], 16), int(val[4:6], 16), alpha

def shrink(image: Image.Image, width: int, height: int) -> Image.Image:
    """Downscale supersampled drawing to final size with antialiasing."""
    return image.resize((max(1, width), max(1, height)), Image.Resampling.LANCZOS)

@lru_cache(maxsize=128)
def icon_image(name: str, size: int, color: str) -> Image.Image:
    """Procedurally draw monochrome icons (SF Symbols spirit) without font dependencies."""
    s = size * SUPERSAMPLE * 2
    ink = _hex_rgba(color)
    image = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    stroke = max(2, s // 9)

    if name == "undo":
        # Draw circular counter-clockwise arrow
        draw.arc([s * 0.2, s * 0.2, s * 0.8, s * 0.8], 200, 170, fill=ink, width=stroke)
        draw.polygon([(s * 0.08, s * 0.3), (s * 0.34, s * 0.3), (s * 0.19, s * 0.55)], fill=ink)
    elif name == "play":
        # Draw clean triangle
        draw.polygon([(s * 0.3, s * 0.2), (s * 0.8, s * 0.5), (s * 0.3, s * 0.8)], fill=ink)
    elif name == "close":
        draw.line([(s * 0.25, s * 0.25), (s * 0.75, s * 0.75)], fill=ink, width=stroke)
        draw.line([(s * 0.75, s * 0.25), (s * 0.25, s * 0.75)], fill=ink, width=stroke)

    return shrink(image, size, size)
```

---

## 3. High-DPI Desktop Awareness & Design Tokens (`theme.py`)

Always enable per-monitor DPI scaling on Windows at application startup:

```python
import ctypes
import sys

def enable_high_dpi() -> None:
    if not sys.platform.startswith("win"):
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        ctypes.windll.user32.SetProcessDPIAware()
```

### Design Token Scale
Keep design tokens small and strictly enforced:
- **Spacing Scale**: `SPACE_S = 8`, `SPACE_M = 16`, `SPACE_L = 24`, `MARGIN = 32`, `GUTTER = 24`.
- **Corner Radius**: Standardized `RADIUS = 12`.
- **Type Scale**:
  - `hero`: 46pt Bold
  - `title`: 22pt Bold
  - `heading`: 15pt Bold
  - `body`: 14pt Regular
  - `caption`: 12pt Regular

---

## 4. Tactile Controls & The Tkinter Width Trap

### The Tkinter Button Width Trap
In Tkinter, `tk.Button(width=X)` calculates `width` in **text character columns**, not pixels!
- Setting `width=140` renders a button 990 pixels wide, breaking layouts and throwing click hit-boxes off screen.
- **Rule**: Style `tk.Button` with natural padding (`padx=16, pady=7`) or draw buttons using fixed-size Canvas wrappers with state-driven images (Rest, Hover, Pressed, Focused).

### Raised Button with Bevel & Keyboard Navigation
A modern game button must provide tactile depth (a 2px bottom shadow / bevel that depresses on press):

```python
class RaisedButton(tk.Canvas):
    """
    3D raised game button with supersampled borders, vector icon,
    hover elevation, press-sink, and full keyboard accessibility.
    """
    def __init__(self, parent, text: str, command, variant="primary", icon=None, tall=False):
        super().__init__(parent, highlightthickness=0, bg=COLORS["page"], cursor="hand2")
        self.text = text
        self.command = command
        self.variant = variant
        self.icon = icon
        self.tall = tall
        self.state = "rest" # rest | hover | pressed

        self.bind("<Enter>", lambda _e: self._set_state("hover"))
        self.bind("<Leave>", lambda _e: self._set_state("rest"))
        self.bind("<Button-1>", lambda _e: self._set_state("pressed"))
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Return>", lambda _e: self.command())
        self.bind("<space>", lambda _e: self.command())

    def _on_release(self, event):
        if self.state == "pressed":
            self._set_state("hover")
            if self.command:
                self.command()
```

---

## 5. Architectural Separation of Concerns

Organize the repository cleanly to decouple game logic, search AI, and GUI:

```
project_root/
├── config/
│   └── settings.py          # Centralized constants, layouts, evaluation weights, paths
├── src/
│   ├── core/
│   │   └── game_logic.py    # Pure rules, coordinates, immutable piece model, move generation
│   ├── ai/
│   │   ├── search.py        # Minimax, Alpha-Beta, Iterative Deepening, telemetry
│   │   ├── evaluation.py    # Non-transitive heuristic functions E(s)
│   │   └── exact_defender.py# Provable game-tree endgame solver
│   ├── benchmark/
│   │   └── runner.py        # Headless game simulation & statistical CSV exporter
│   ├── storage.py           # Atomic JSON persistence (custom stages, leaderboards)
│   └── ui/
│       ├── app.py           # Controller / Window manager
│       ├── theme.py         # Apple HIG & Linear tokens, metrics, font scales
│       ├── art.py           # Supersampled vector & token renderers
│       ├── widgets.py       # Tactile RaisedButton, PillButton, SegmentedControl
│       ├── board.py         # Sub-pixel game board layer
│       ├── scene.py         # Base SceneView with dynamic responsive layout()
│       └── views/           # Self-contained view controllers (menu, game, editor)
└── tests/                   # Automated unit tests for logic, AI, and UI
```

### Golden Rules for Clean Code:
1. **Zero UI Imports in Core Logic**: `src/core/` and `src/ai/` must never import `tkinter`, `PIL`, or UI modules.
2. **Background AI Execution**: Never run heuristic minimax or exact solvers on the Tkinter main thread. Use `threading.Thread` or a `BackgroundTask` class to avoid UI freezes.
3. **Cloned State for Search**: Game tree exploration must clone state (`state.clone()`) rather than mutating live display state.

---

## 6. Circular Combat Cycle Pattern

When game pieces feature non-transitive relationships (like Rock-Paper-Scissors or Gajah-Orang-Semut):
1. Embed a **Circular Cycle Diagram** inside the board container (anchored to the bottom-right).
2. Draw 3 circular token nodes connected by curved directional arrows (`math.cos`, `math.sin`, and `_curved_arrow`).
3. Include an interactive toggle (`[-]` / `[+]`) so experienced players can collapse it when not needed.
4. Keep the sidebar dedicated to HUD metrics (Turn, Undos, Timers, Move History, Action Buttons).

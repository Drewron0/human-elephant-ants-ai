"""Theme configuration: color palette, typography scales, and UI layout metrics."""

import tkinter as tk
from tkinter import font as tkfont
from typing import Final

COLORS: Final[dict[str, str]] = {
    "page": "#F7F7F4",
    "card": "#FFFFFF",
    "card_alt": "#F2F3EF",
    "line": "#E1E3DC",
    "line_strong": "#8A8D86",
    "scroll_thumb": "#C8CAC3",
    "ink": "#1A1A1B",
    "ink_muted": "#595C57",
    "on_accent": "#FFFFFF",
    "accent": "#3B7A35",
    "accent_hover": "#32692D",
    "accent_pressed": "#285825",
    "accent_soft": "#E6F0E3",
    "gold": "#F7CF3D",
    "gold_hover": "#F2C318",
    "gold_pressed": "#D9A90A",
    "danger": "#B3362B",
    "secondary": "#FFFFFF",
    "secondary_hover": "#F2F3EF",
    "secondary_pressed": "#E6E8E1",
    "disabled": "#ECEDE8",
    "disabled_ink": "#5C5F59",
    "focus": "#1E6FD9",
    "tile_light": "#FFFFFF",
    "tile_dark": "#ECEEE7",
    "goal_tile": "#F7DC6F",
    "goal_star": "#E0A100",
    "home_tile": "#EFC4BC",
    "home_star": "#B3362B",
    "token_body": "#FFFFFF",
    "move_dot": "#3B7A35",
    "selected": "#6AAA64",
    "capture": "#B3362B",
    "last_move": "#FBF2BF",
    "scene_sky_top": "#BFE3F2",
    "scene_sky_low": "#EEF8EA",
    "scene_sun": "#FBE38A",
    "scene_cloud": "#FFFFFF",
    "scene_hill_far": "#B9DDA6",
    "scene_hill_mid": "#8FC67C",
    "scene_hill_near": "#6AAA64",
}

TEAM_COLORS: Final[dict[str, str]] = {
    "Forest Green": "#2F6B2B",
    "Clay Red": "#B3362B",
    "Deep Lake": "#1F5FBF",
    "Royal Plum": "#7B2D8E",
    "Sunset Orange": "#B8500B",
    "Night Slate": "#334155",
}
DEFAULT_PLAYER_COLOR: Final[str] = "Forest Green"
DEFAULT_AI_COLOR: Final[str] = "Clay Red"

HOTKEYS: Final[dict[str, dict[str, str]]] = {
    "undo": {"seq": "<Control-z>", "key_str": "Ctrl+Z", "label": "Undo"},
    "restart": {"seq": "<Control-r>", "key_str": "Ctrl+R", "label": "Restart"},
    "surrender": {"seq": "<Control-e>", "key_str": "Ctrl+E", "label": "Give Up"},
}

TYPE_SCALE: Final[dict[str, tuple[int, bool]]] = {
    "hero": (46, True),
    "title": (22, True),
    "heading": (15, True),
    "body": (14, False),
    "caption": (12, False),
}
FONT_FAMILIES: Final[tuple[str, ...]] = (
    "Segoe UI",
    "SF Pro Text",
    "Helvetica Neue",
    "Noto Sans",
    "DejaVu Sans",
)
SEMIBOLD_FAMILY: Final[str] = "Segoe UI Semibold"

MIN_TARGET: Final[int] = 44
RADIUS: Final[int] = 12
SPACE_S: Final[int] = 8
SPACE_M: Final[int] = 16
SPACE_L: Final[int] = 24
MARGIN: Final[int] = 32
GUTTER: Final[int] = 24
BASE_DPI: Final[float] = 96.0
COMPACT_DENSITY: Final[float] = 0.88
REGULAR_DENSITY: Final[float] = 1.0
LARGE_DENSITY: Final[float] = 1.14
COMPACT_WIDTH: Final[int] = 960
COMPACT_HEIGHT: Final[int] = 640
LARGE_WIDTH: Final[int] = 1700
LARGE_HEIGHT: Final[int] = 950
MIN_WINDOW: Final[tuple[int, int]] = (760, 560)
DEFAULT_WINDOW: Final[tuple[int, int]] = (1280, 800)


class Metrics:
    """Current interface scale: display DPI multiplied by window density."""

    def __init__(self) -> None:
        self.dpi_factor = 1.0
        self.density = REGULAR_DENSITY

    @property
    def scale(self) -> float:
        """Return the combined scale factor."""
        return self.dpi_factor * self.density

    def px(self, value: float) -> int:
        """Convert design points into device pixels."""
        return max(1, round(value * self.scale))

    def window(self, value: int) -> int:
        """Scale a window dimension by display DPI only."""
        return round(value * self.dpi_factor)

    def target(self) -> int:
        """Return the minimum interactive target size, unaffected by compact density."""
        return round(MIN_TARGET * self.dpi_factor)

    def density_for(self, width: int, height: int) -> float:
        """Choose the density for a window size in device pixels."""
        logical_width = width / self.dpi_factor
        logical_height = height / self.dpi_factor
        if logical_width < COMPACT_WIDTH or logical_height < COMPACT_HEIGHT:
            return COMPACT_DENSITY
        if logical_width >= LARGE_WIDTH and logical_height >= LARGE_HEIGHT:
            return LARGE_DENSITY
        return REGULAR_DENSITY


METRICS = Metrics()


def font(role: str) -> str:
    """Return the named font for a text style."""
    return f"ChessSut{role}"


def create_fonts(root: tk.Misc) -> dict[str, tkfont.Font]:
    """Create one named font per text style; views then reference them by name."""
    available = set(tkfont.families(root))
    family = next((name for name in FONT_FAMILIES if name in available), "TkDefaultFont")
    has_semibold = SEMIBOLD_FAMILY in available
    fonts = {}
    for role, (size, emphasized) in TYPE_SCALE.items():
        fonts[role] = tkfont.Font(
            root=root,
            name=font(role),
            family=SEMIBOLD_FAMILY if emphasized and has_semibold else family,
            size=-METRICS.px(size),
            weight="bold" if emphasized and not has_semibold else "normal",
        )
    return fonts


def rescale_fonts(fonts: dict[str, tkfont.Font]) -> None:
    """Apply the current scale; widgets using named fonts update automatically."""
    for role, named_font in fonts.items():
        named_font.configure(size=-METRICS.px(TYPE_SCALE[role][0]))

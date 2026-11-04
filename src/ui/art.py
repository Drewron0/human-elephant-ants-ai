"""Pillow renderers for tokens, tiles, panels, buttons and icons.

Each renderer draws at a supersampled size and downscales, which gives smooth
antialiased edges that Tk canvases cannot produce, and caches by exact size.
"""

import math
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter

from config import settings
from src.core.game_logic import PieceSpec
from src.ui.theme import COLORS

SUPERSAMPLE = 3
PIECE_FILES: dict[str, str] = {"H": "orang.png", "E": "gajah.png", "A": "semut.png"}
PRESS_SINK = 0.6
TILE_GAP_RATIO = 0.05
TILE_RADIUS_DIVISOR = 8
ARROW_ARC = (20, 285)
ARROW_HALF_BASE = 0.17
ARROW_LENGTH = 0.24
SCENE_SCALE = 2
SCENE_STEP = 6
SCENE_SOFTEN = 1.4
SCENE_HILLS: tuple[tuple[str, float, float, float, float], ...] = (
    ("scene_hill_far", 0.58, 0.05, 1.3, 0.4),
    ("scene_hill_mid", 0.70, 0.06, 1.0, 2.2),
    ("scene_hill_near", 0.84, 0.05, 1.6, 4.1),
)
SCENE_CLOUDS: tuple[tuple[float, float, float], ...] = (
    (0.12, 0.17, 0.09),
    (0.34, 0.09, 0.06),
    (0.70, 0.20, 0.07),
    (0.90, 0.33, 0.05),
)
ICON_NAMES = (
    "back",
    "chevron",
    "undo",
    "restart",
    "flag",
    "help",
    "play",
    "plus",
    "edit",
    "trash",
    "close",
    "check",
    "stop",
    "export",
    "chart",
    "trophy",
)


def _hex_rgba(color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    """Convert ``#RRGGBB`` into an RGBA tuple."""
    value = color.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), alpha


def _shrink(image: Image.Image, width: int, height: int) -> Image.Image:
    """Downscale a supersampled drawing to its final size."""
    return image.resize((max(1, width), max(1, height)), Image.Resampling.LANCZOS)


@lru_cache(maxsize=3)
def piece_art(piece_type: str) -> Image.Image:
    """Load a character image with its transparent margins removed."""
    if piece_type not in PIECE_FILES:
        raise ValueError(f"Unknown piece type: {piece_type}")
    with Image.open(settings.ASSETS_DIR / PIECE_FILES[piece_type]) as source:
        image = source.convert("RGBA")
    return image.crop(image.getchannel("A").getbbox())


@lru_cache(maxsize=64)
def panel_image(
    width: int, height: int, radius: int, fill: str, edge: str, edge_width: int = 1
) -> Image.Image:
    """Render a flat rounded surface with a thin border."""
    scale = SUPERSAMPLE
    card = Image.new("RGBA", (width * scale, height * scale), (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle(
        [0, 0, width * scale - 1, height * scale - 1],
        radius=radius * scale,
        fill=_hex_rgba(fill),
        outline=_hex_rgba(edge),
        width=edge_width * scale,
    )
    return _shrink(card, width, height)


@lru_cache(maxsize=256)
def pill_image(
    width: int, height: int, radius: int, fill: str, border: str, focused: bool
) -> Image.Image:
    """Render a flat rounded control, with a focus ring when it has keyboard focus."""
    scale = SUPERSAMPLE
    w, h = width * scale, height * scale
    image = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    inset = 3 * scale if focused else 0
    r = radius * scale
    draw.rounded_rectangle(
        [inset, inset, w - 1 - inset, h - 1 - inset],
        radius=max(1, r - inset),
        fill=_hex_rgba(fill),
        outline=_hex_rgba(border),
        width=scale,
    )
    if focused:
        draw.rounded_rectangle(
            [0, 0, w - 1, h - 1],
            radius=r,
            outline=_hex_rgba(COLORS["focus"]),
            width=2 * scale,
        )
    return _shrink(image, width, height)


@lru_cache(maxsize=64)
def raised_button_image(
    width: int,
    height: int,
    radius: int,
    depth: int,
    face: str,
    lip: str,
    pressed: bool,
    focused: bool,
) -> Image.Image:
    """Render a game button: a face resting on a darker lip that gives it thickness."""
    scale = SUPERSAMPLE
    w, h = width * scale, height * scale
    image = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    inset = 3 * scale if focused else 0
    r = radius * scale
    lift = depth * scale
    sink = round(lift * PRESS_SINK) if pressed else 0
    left, right, top, bottom = inset, w - 1 - inset, inset, h - 1 - inset
    draw.rounded_rectangle([left, top + sink, right, bottom], radius=r, fill=_hex_rgba(lip))
    draw.rounded_rectangle(
        [left, top + sink, right, bottom - lift + sink], radius=r, fill=_hex_rgba(face)
    )
    if focused:
        draw.rounded_rectangle(
            [0, 0, w - 1, h - 1],
            radius=r + inset,
            outline=_hex_rgba(COLORS["focus"]),
            width=2 * scale,
        )
    return _shrink(image, width, height)


@lru_cache(maxsize=128)
def token_image(piece_type: str, owner: int, color: str, diameter: int) -> Image.Image:
    """Render a piece: round tokens for the player, rounded squares for the defender.

    The two silhouettes keep ownership readable without relying on color alone.
    """
    scale = SUPERSAMPLE
    size = diameter * scale
    margin = max(scale, size // 11)
    box = [margin, margin, size - margin, size - margin]
    rim = max(scale * 2, size // 16)
    corner = size // 6
    inner = [box[0] + rim, box[1] + rim, box[2] - rim, box[3] - rim]

    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    if owner == 0:
        draw.ellipse(box, fill=_hex_rgba(color))
        draw.ellipse(inner, fill=_hex_rgba(COLORS["token_body"]))
    else:
        draw.rounded_rectangle(box, radius=corner, fill=_hex_rgba(color))
        draw.rounded_rectangle(
            inner, radius=max(1, corner - rim), fill=_hex_rgba(COLORS["token_body"])
        )

    art = piece_art(piece_type).copy()
    art_box = int((inner[2] - inner[0]) * 0.82)
    art.thumbnail((art_box, art_box), Image.Resampling.LANCZOS)
    center_x = (inner[0] + inner[2]) // 2
    center_y = (inner[1] + inner[3]) // 2
    image.alpha_composite(art, (center_x - art.width // 2, center_y - art.height // 2))
    return _shrink(image, diameter, diameter)


def _draw_star(draw: ImageDraw.ImageDraw, cx: float, cy: float, radius: float, color: str) -> None:
    """Draw a five-pointed star for the goal corners."""
    points = []
    for index in range(10):
        length = radius if index % 2 == 0 else radius * 0.46
        angle = index * math.pi / 5 - math.pi / 2
        points.append((cx + length * math.cos(angle), cy + length * math.sin(angle)))
    draw.polygon(points, fill=_hex_rgba(color))


@lru_cache(maxsize=8)
def board_base_image(board_size: int, square: int) -> Image.Image:
    """Render the tile grid: separated square tiles with two marked goal corners."""
    scale = SUPERSAMPLE
    sq = square * scale
    gap = max(scale, round(sq * TILE_GAP_RATIO))
    grid = sq * board_size
    image = Image.new("RGBA", (grid, grid), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    goal = (0, board_size - 1)
    home = (board_size - 1, 0)
    for row in range(board_size):
        for col in range(board_size):
            x0, y0 = col * sq + gap // 2, row * sq + gap // 2
            box = (x0, y0, x0 + sq - gap - 1, y0 + sq - gap - 1)
            if (row, col) == goal:
                fill, star = COLORS["goal_tile"], COLORS["goal_star"]
            elif (row, col) == home:
                fill, star = COLORS["home_tile"], COLORS["home_star"]
            else:
                fill = COLORS["tile_light"] if (row + col) % 2 == 0 else COLORS["tile_dark"]
                star = ""
            draw.rectangle(
                box, fill=_hex_rgba(fill), outline=_hex_rgba(COLORS["line"]), width=scale
            )
            if star:
                _draw_star(draw, x0 + (sq - gap) / 2, y0 + (sq - gap) / 2, sq * 0.27, star)
    return _shrink(image, square * board_size, square * board_size)


@lru_cache(maxsize=32)
def overlay_image(kind: str, square: int) -> Image.Image:
    """Render one square-sized board marker: select, move, capture, last or cursor."""
    scale = SUPERSAMPLE
    size = square * scale
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    stroke = max(2 * scale, size // 16)
    gap = max(scale, round(size * TILE_GAP_RATIO)) // 2
    near, far = gap, size - gap - 1
    box = [near, near, far, far]
    radius = max(scale, size // TILE_RADIUS_DIVISOR)
    if kind == "last":
        draw.rounded_rectangle(box, radius=radius, fill=_hex_rgba(COLORS["last_move"], 200))
    elif kind == "select":
        draw.rounded_rectangle(
            box,
            radius=radius,
            fill=_hex_rgba(COLORS["selected"], 70),
            outline=_hex_rgba(COLORS["selected"]),
            width=stroke,
        )
    elif kind == "move":
        dot = size // 8
        center = size // 2
        draw.ellipse(
            [center - dot, center - dot, center + dot, center + dot],
            fill=_hex_rgba(COLORS["move_dot"]),
        )
    elif kind == "capture":
        draw.rounded_rectangle(
            box, radius=radius, outline=_hex_rgba(COLORS["capture"]), width=stroke
        )
    elif kind == "cursor":
        draw.rounded_rectangle(box, radius=radius, outline=_hex_rgba(COLORS["focus"]), width=stroke)
    else:
        raise ValueError(f"Unknown board overlay: {kind}")
    return _shrink(image, square, square)


def board_thumbnail(
    board_size: int,
    pieces: list[PieceSpec],
    dimension: int,
    player_color: str,
    defender_color: str,
) -> Image.Image:
    """Render a small stage preview with the same look as the real board."""
    square = dimension // board_size
    base = board_base_image(board_size, square).copy()
    for r, c, owner, piece_type in pieces:
        if 0 <= r < board_size and 0 <= c < board_size:
            color = player_color if owner == 0 else defender_color
            token = token_image(piece_type, owner, color, max(6, square))
            base.alpha_composite(token, (c * square, r * square))
    return base


def _curved_arrow(
    draw: ImageDraw.ImageDraw,
    center: tuple[float, float],
    radius: float,
    start: float,
    end: float,
    color: str,
    stroke: int,
) -> None:
    """Draw a clockwise arc from ``start`` to ``end`` radians with an arrowhead."""
    cx, cy = center
    steps = 24
    points = [
        (
            cx + radius * math.cos(start + (end - start) * step / steps),
            cy + radius * math.sin(start + (end - start) * step / steps),
        )
        for step in range(steps + 1)
    ]
    draw.line(points, fill=_hex_rgba(color), width=stroke, joint="curve")
    tip = points[-1]
    heading = math.atan2(tip[1] - points[-3][1], tip[0] - points[-3][0])
    head = stroke * 3.2
    draw.polygon(
        [
            (tip[0] + math.cos(heading) * head, tip[1] + math.sin(heading) * head),
            (tip[0] + math.cos(heading + 2.3) * head, tip[1] + math.sin(heading + 2.3) * head),
            (tip[0] + math.cos(heading - 2.3) * head, tip[1] + math.sin(heading - 2.3) * head),
        ],
        fill=_hex_rgba(color),
    )


@lru_cache(maxsize=6)
def cycle_diagram_image(dimension: int, token_color: str) -> Image.Image:
    """Render the Elephant, Human and Ant capture cycle with clockwise arrows."""
    scale = SUPERSAMPLE
    size = dimension * scale
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    center = (size / 2, size / 2 + size * 0.03)
    orbit = size * 0.33
    token = int(dimension * 0.36)
    angles = (-math.pi / 2, math.pi / 6, 5 * math.pi / 6)
    gap = 0.62
    for index in range(3):
        start = angles[index] + gap
        end = angles[(index + 1) % 3] - gap
        if end < start:
            end += 2 * math.pi
        _curved_arrow(
            draw, center, orbit, start, end, COLORS["line_strong"], max(scale, size // 60)
        )
    for piece_type, angle in zip("EHA", angles, strict=True):
        x = center[0] + orbit * math.cos(angle)
        y = center[1] + orbit * math.sin(angle)
        badge = token_image(piece_type, 0, token_color, token).resize(
            (token * scale, token * scale), Image.Resampling.BICUBIC
        )
        image.alpha_composite(badge, (int(x - badge.width / 2), int(y - badge.height / 2)))
    return _shrink(image, dimension, dimension)


def _icon_arc_arrow(
    draw: ImageDraw.ImageDraw, size: int, color: tuple[int, ...], flip: bool
) -> None:
    """Draw the circular arrow shared by undo and restart; undo is its mirror image."""
    stroke = size // 9
    center = size / 2
    radius = size * 0.36
    box = [center - radius, center - radius, center + radius, center + radius]
    gap_end, arrow_angle = ARROW_ARC
    start, end = (180 - arrow_angle, 180 - gap_end) if flip else (gap_end, arrow_angle)
    draw.arc(box, start, end, fill=color, width=stroke)
    angle = math.radians(arrow_angle)
    x = center + radius * math.cos(angle)
    y = center + radius * math.sin(angle)
    forward = (-math.sin(angle), math.cos(angle))
    side = (forward[1], -forward[0])
    half_base, length = size * ARROW_HALF_BASE, size * ARROW_LENGTH
    head = [
        (x + side[0] * half_base, y + side[1] * half_base),
        (x - side[0] * half_base, y - side[1] * half_base),
        (x + forward[0] * length, y + forward[1] * length),
    ]
    if flip:
        head = [(size - point_x, point_y) for point_x, point_y in head]
    draw.polygon(head, fill=color)


def _scene_cloud(draw: ImageDraw.ImageDraw, x: float, y: float, size: float) -> None:
    """Draw a soft cloud from a few overlapping ellipses."""
    fill = _hex_rgba(COLORS["scene_cloud"])
    for offset, lift, scale in ((-0.9, 0.0, 0.7), (0.0, 0.25, 1.0), (0.9, 0.0, 0.75)):
        radius = size * scale
        left, top = x + offset * size - radius, y - lift * size - radius * 0.55
        draw.ellipse([left, top, left + radius * 2, top + radius * 1.1], fill=fill)


@lru_cache(maxsize=2)
def menu_background_image(width: int, height: int) -> Image.Image:
    """Render the menu's meadow: sky, sun, clouds and three layers of hills."""
    w, h = max(1, width // SCENE_SCALE), max(1, height // SCENE_SCALE)
    top = Image.new("RGB", (w, h), COLORS["scene_sky_top"])
    low = Image.new("RGB", (w, h), COLORS["scene_sky_low"])
    fade = Image.linear_gradient("L").resize((w, h))
    image = Image.composite(low, top, fade).convert("RGBA")

    sun = h * 0.11
    draw = ImageDraw.Draw(image)
    sun_x, sun_y = w * 0.84, h * 0.17
    draw.ellipse(
        [sun_x - sun, sun_y - sun, sun_x + sun, sun_y + sun], fill=_hex_rgba(COLORS["scene_sun"])
    )
    for x, y, size in SCENE_CLOUDS:
        _scene_cloud(draw, w * x, h * y, h * size)
    for color, level, swell, waves, phase in SCENE_HILLS:
        crest = [
            (x, h * (level + swell * math.sin(x / w * math.tau * waves + phase)))
            for x in range(0, w + SCENE_STEP, SCENE_STEP)
        ]
        draw.polygon([*crest, (w, h), (0, h)], fill=_hex_rgba(COLORS[color]))
    soft = image.convert("RGB").filter(ImageFilter.GaussianBlur(SCENE_SOFTEN))
    return soft.resize((width, height), Image.Resampling.BICUBIC)


@lru_cache(maxsize=128)
def icon_image(name: str, size: int, color: str) -> Image.Image:
    """Render a simple monochrome symbol, in the spirit of SF Symbols."""
    if name not in ICON_NAMES:
        raise ValueError(f"Unknown icon: {name}")
    s = size * SUPERSAMPLE * 2
    ink = _hex_rgba(color)
    image = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    stroke = s // 9
    if name == "back":
        draw.line(
            [(s * 0.64, s * 0.16), (s * 0.3, s * 0.5), (s * 0.64, s * 0.84)],
            fill=ink,
            width=stroke,
            joint="curve",
        )
    elif name == "chevron":
        draw.line(
            [(s * 0.16, s * 0.34), (s * 0.5, s * 0.68), (s * 0.84, s * 0.34)],
            fill=ink,
            width=stroke,
            joint="curve",
        )
    elif name == "undo":
        _icon_arc_arrow(draw, s, ink, True)
    elif name == "restart":
        _icon_arc_arrow(draw, s, ink, False)
    elif name == "flag":
        draw.line([(s * 0.26, s * 0.1), (s * 0.26, s * 0.9)], fill=ink, width=stroke)
        draw.polygon([(s * 0.3, s * 0.13), (s * 0.84, s * 0.33), (s * 0.3, s * 0.54)], fill=ink)
    elif name == "help":
        draw.ellipse([s * 0.08, s * 0.08, s * 0.92, s * 0.92], outline=ink, width=stroke)
        draw.arc([s * 0.34, s * 0.24, s * 0.66, s * 0.54], 180, 60, fill=ink, width=stroke)
        draw.line([(s * 0.52, s * 0.52), (s * 0.5, s * 0.62)], fill=ink, width=stroke)
        dot = s * 0.055
        draw.ellipse([s * 0.5 - dot, s * 0.72 - dot, s * 0.5 + dot, s * 0.72 + dot], fill=ink)
    elif name == "play":
        draw.polygon([(s * 0.24, s * 0.12), (s * 0.86, s * 0.5), (s * 0.24, s * 0.88)], fill=ink)
    elif name == "plus":
        draw.line([(s * 0.5, s * 0.14), (s * 0.5, s * 0.86)], fill=ink, width=stroke)
        draw.line([(s * 0.14, s * 0.5), (s * 0.86, s * 0.5)], fill=ink, width=stroke)
    elif name == "edit":
        draw.line([(s * 0.22, s * 0.78), (s * 0.76, s * 0.24)], fill=ink, width=stroke + s // 18)
        draw.polygon([(s * 0.1, s * 0.9), (s * 0.15, s * 0.68), (s * 0.32, s * 0.85)], fill=ink)
    elif name == "trash":
        draw.line([(s * 0.14, s * 0.26), (s * 0.86, s * 0.26)], fill=ink, width=stroke)
        draw.line([(s * 0.38, s * 0.12), (s * 0.62, s * 0.12)], fill=ink, width=stroke)
        draw.polygon(
            [(s * 0.22, s * 0.34), (s * 0.78, s * 0.34), (s * 0.7, s * 0.92), (s * 0.3, s * 0.92)],
            fill=ink,
        )
    elif name == "close":
        draw.line([(s * 0.2, s * 0.2), (s * 0.8, s * 0.8)], fill=ink, width=stroke)
        draw.line([(s * 0.8, s * 0.2), (s * 0.2, s * 0.8)], fill=ink, width=stroke)
    elif name == "check":
        draw.line(
            [(s * 0.14, s * 0.54), (s * 0.4, s * 0.8), (s * 0.86, s * 0.2)],
            fill=ink,
            width=stroke,
            joint="curve",
        )
    elif name == "stop":
        draw.rounded_rectangle([s * 0.18, s * 0.18, s * 0.82, s * 0.82], radius=s // 10, fill=ink)
    elif name == "export":
        draw.line([(s * 0.5, s * 0.1), (s * 0.5, s * 0.62)], fill=ink, width=stroke)
        draw.line(
            [(s * 0.28, s * 0.34), (s * 0.5, s * 0.1), (s * 0.72, s * 0.34)],
            fill=ink,
            width=stroke,
            joint="curve",
        )
        draw.line(
            [(s * 0.14, s * 0.6), (s * 0.14, s * 0.88), (s * 0.86, s * 0.88), (s * 0.86, s * 0.6)],
            fill=ink,
            width=stroke,
            joint="curve",
        )
    elif name == "chart":
        for x, top in ((0.2, 0.54), (0.5, 0.3), (0.8, 0.12)):
            draw.line([(s * x, s * 0.88), (s * x, s * top)], fill=ink, width=stroke + s // 22)
    elif name == "trophy":
        draw.pieslice([s * 0.24, s * -0.2, s * 0.76, s * 0.62], 0, 180, fill=ink)
        draw.arc([s * 0.06, s * 0.14, s * 0.36, s * 0.46], 90, 270, fill=ink, width=stroke // 2)
        draw.arc([s * 0.64, s * 0.14, s * 0.94, s * 0.46], 270, 90, fill=ink, width=stroke // 2)
        draw.line([(s * 0.5, s * 0.6), (s * 0.5, s * 0.82)], fill=ink, width=stroke)
        draw.line([(s * 0.28, s * 0.88), (s * 0.72, s * 0.88)], fill=ink, width=stroke)
    return _shrink(image, size, size)


def window_icon() -> Image.Image:
    """Return the application window icon."""
    return token_image("E", 0, COLORS["accent"], 64)

"""How-to-play guide with the capture cycle shown first."""

import tkinter as tk
from typing import TYPE_CHECKING

from PIL import ImageTk

from config import settings
from src.ui import art
from src.ui.scene import HeaderBar, Panel, SceneView
from src.ui.scrolling import ScrollArea
from src.ui.theme import COLORS, HOTKEYS, METRICS, SPACE_L, SPACE_M, SPACE_S, font
from src.ui.widgets import WrapLabel, section_title

if TYPE_CHECKING:
    from src.ui.app import GameApp

GUIDE_WIDTH = 760
CYCLE_SIZE = 170
GUIDE_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Goal",
        (
            "Move any piece into the star corner of your opponent to win at once.",
            "You start bottom-left and aim for the gold star at the top right.",
            "The AI starts top-right and aims for the red star at the bottom left.",
        ),
    ),
    (
        "Moving",
        (
            "Every piece moves one square per turn in any of the 8 directions.",
            "Green dots mark the squares you can move to.",
            "A red outline marks a piece you can capture.",
            "You can also play with the arrow keys and Return.",
        ),
    ),
    (
        "Puzzles",
        (
            "Each stage has a minimum step target entered by its author.",
            f"The move limit is {settings.PUZZLE_MOVE_LIMIT_MULTIPLIER} times that minimum.",
            "The Exact Defender plays only replies it has proven to be the best.",
            "Long stages can exhaust the proof budget. The defender then waits, "
            "and you decide whether to retry or accept an Alpha-Beta reply.",
        ),
    ),
    (
        "Shortcuts",
        tuple(f"{hotkey['key_str']}: {hotkey['label']}" for hotkey in HOTKEYS.values()),
    ),
)


class TutorialView(SceneView):
    """Presents the rules in short sections."""

    def __init__(self, parent: tk.Misc, app: "GameApp") -> None:
        super().__init__(parent, app)
        self.header = HeaderBar(
            self,
            "How to Play",
            back_text="Menu",
            on_back=lambda: self.app.show_view("menu"),
        )
        self.guide = Panel(self)
        scroll = ScrollArea(self.guide.body)
        scroll.pack(fill=tk.BOTH, expand=True)
        content = scroll.content

        hero = tk.Frame(content, bg=COLORS["card"])
        hero.pack(fill=tk.X)
        image = art.cycle_diagram_image(METRICS.px(CYCLE_SIZE), COLORS["ink_muted"])
        self._cycle_photo = ImageTk.PhotoImage(image, master=hero)
        tk.Label(hero, image=self._cycle_photo, bg=COLORS["card"]).pack(side=tk.LEFT)
        text = tk.Frame(hero, bg=COLORS["card"])
        text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(METRICS.px(SPACE_L), 0))
        tk.Label(
            text,
            text="Every Piece Has a Rival",
            font=font("title"),
            bg=COLORS["card"],
            fg=COLORS["ink"],
            anchor="w",
        ).pack(fill=tk.X)
        WrapLabel(
            text,
            "Elephant beats Human, Human beats Ant, and Ant beats Elephant. "
            "Matching pieces block each other, and you cannot capture your own.",
            fg=COLORS["ink_muted"],
        ).pack(fill=tk.X, pady=(METRICS.px(SPACE_S), 0))

        for title, lines in GUIDE_SECTIONS:
            section_title(content, title).pack(
                fill=tk.X, pady=(METRICS.px(SPACE_L), METRICS.px(SPACE_S))
            )
            for line in lines:
                WrapLabel(content, f"-  {line}", fg=COLORS["ink_muted"]).pack(
                    fill=tk.X, pady=(0, METRICS.px(SPACE_M) // 4)
                )

    def layout(self, width: int, height: int) -> None:
        """Center a readable column under the header."""
        top = self.header.place_top(width)
        margin = top - self.header.height() - self.header.geometry[1]
        guide_w = min(METRICS.px(GUIDE_WIDTH), width - margin * 2)
        self.guide.place((width - guide_w) // 2, top, guide_w, height - top - margin)

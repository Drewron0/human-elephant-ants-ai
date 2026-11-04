"""Chess-Sut desktop application entry point."""

import ctypes
import logging
import sys

from config import settings
from src.ui.app import GameApp


def enable_high_dpi() -> None:
    """Enable per-monitor DPI awareness on Windows so the interface stays sharp."""
    if not sys.platform.startswith("win"):
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        ctypes.windll.user32.SetProcessDPIAware()


def main() -> None:
    """Configure logging and run the application."""
    logging.basicConfig(level=settings.LOG_LEVEL, format=settings.LOG_FORMAT)
    enable_high_dpi()
    GameApp().mainloop()


if __name__ == "__main__":
    main()

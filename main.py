import sys
import ctypes
from gui import GameApp


def enable_high_dpi():
    """Enable Per-Monitor v2 DPI awareness on Windows to prevent GUI blurriness."""
    if sys.platform.startswith('win'):
        try:
            # Per-Monitor v2 DPI awareness
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


def main():
    enable_high_dpi()
    app = GameApp()
    app.mainloop()


if __name__ == "__main__":
    main()
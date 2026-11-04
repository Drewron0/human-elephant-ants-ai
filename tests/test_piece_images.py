import gc
import tkinter as tk
import unittest
from pathlib import Path

from PIL import Image

from ui_theme import _piece_art, draw_board_thumbnail, draw_piece_image


class PieceImageTests(unittest.TestCase):
    def test_art_matches_supplied_images_without_transparent_margins(self):
        assets = Path(__file__).resolve().parents[1] / 'assets'
        for piece_type, filename in [('H', 'orang.png'), ('E', 'gajah.png'), ('A', 'semut.png')]:
            with self.subTest(piece_type=piece_type), Image.open(assets / filename) as source:
                expected = source.convert('RGBA')
                expected = expected.crop(expected.getchannel('A').getbbox())
                actual = _piece_art(piece_type)
                self.assertEqual(actual.size, expected.size)
                self.assertEqual(actual.tobytes(), expected.tobytes())

    def test_canvas_retains_art_and_resizes_without_distorting_it(self):
        root = tk.Tk()
        root.withdraw()
        self.addCleanup(root.destroy)
        canvas = tk.Canvas(root)
        for size in (8, 40, 80, 24):
            canvas.delete('all')
            for piece_type in 'HEA':
                draw_piece_image(canvas, 50, 50, piece_type, size)
                image = canvas._piece_images[piece_type]
                draw_piece_image(canvas, 90, 50, piece_type, size)
                self.assertIs(canvas._piece_images[piece_type], image)
                width, height = _piece_art(piece_type).size
                self.assertEqual(max(image.width(), image.height()), size)
                self.assertLessEqual(abs(image.width() - image.height() * width / height), 1)
            gc.collect()
            self.assertEqual(len(canvas._piece_images), 3)
            for item in canvas.find_all():
                self.assertEqual(canvas.type(item), 'image')
                self.assertGreater(int(root.tk.call('image', 'width', canvas.itemcget(item, 'image'))), 0)

        pieces = [(owner, col, owner, piece_type)
                  for owner in (0, 1) for col, piece_type in enumerate('HEA')]
        draw_board_thumbnail(canvas, 9, pieces, (0, 8), width=130, height=130)
        self.assertEqual(sum(canvas.type(item) == 'image' for item in canvas.find_all()), 6)
        self.assertFalse(any(canvas.type(item) == 'text' for item in canvas.find_all()))


if __name__ == '__main__':
    unittest.main()

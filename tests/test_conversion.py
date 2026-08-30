import tempfile
import unittest
from pathlib import Path

import fitz
from PIL import Image

from utils.pdf_converter import (
    check_file_size, cleanup_temp_files, pdf_to_photos, photos_to_pdf,
)


class ConversionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    async def test_round_trip_preserves_page_count_and_order(self):
        paths = []
        for index, color in enumerate(("red", "blue")):
            path = self.root / f"input-{index}.png"
            with Image.new("RGB", (64, 48), color) as picture:
                picture.save(path)
            paths.append(str(path))
        output = self.root / "result.pdf"
        self.assertTrue(await photos_to_pdf(paths, str(output)))
        with fitz.open(output) as document:
            self.assertEqual(len(document), 2)
        ok, pages = await pdf_to_photos(str(output), str(self.root / "pages"))
        self.assertTrue(ok)
        self.assertEqual([Path(page).name for page in pages], ["page_001.jpg", "page_002.jpg"])
        with Image.open(pages[0]) as first, Image.open(pages[1]) as second:
            self.assertGreater(first.getpixel((10, 10))[0], 240)
            self.assertGreater(second.getpixel((10, 10))[2], 240)

    async def test_transparent_images_use_white_background(self):
        for mode, color in (("RGBA", (0, 0, 0, 0)), ("LA", (0, 0))):
            with self.subTest(mode=mode):
                source = self.root / f"{mode}.png"
                with Image.new(mode, (20, 20), color) as picture:
                    picture.save(source)
                output = self.root / f"{mode}.pdf"
                self.assertTrue(await photos_to_pdf([str(source)], str(output)))
                with fitz.open(output) as document:
                    pixmap = document[0].get_pixmap()
                    self.assertTrue(all(channel > 245 for channel in pixmap.pixel(10, 10)))

    async def test_empty_photo_list_is_rejected(self):
        self.assertFalse(await photos_to_pdf([], str(self.root / "empty.pdf")))
        self.assertFalse((self.root / "empty.pdf").exists())

    async def test_missing_photo_is_rejected(self):
        self.assertFalse(await photos_to_pdf([str(self.root / "missing.png")], str(self.root / "out.pdf")))

    async def test_missing_pdf_is_rejected(self):
        self.assertEqual(await pdf_to_photos(str(self.root / "missing.pdf"), str(self.root / "pages")), (False, []))

    def test_file_size_boundary(self):
        self.assertTrue(check_file_size(1024 * 1024, 1))
        self.assertFalse(check_file_size(1024 * 1024 + 1, 1))

    def test_cleanup_tolerates_already_removed_file(self):
        path = self.root / "temporary.txt"
        path.touch()
        cleanup_temp_files([str(path), str(path)])
        self.assertFalse(path.exists())

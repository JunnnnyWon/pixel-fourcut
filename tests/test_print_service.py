import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from backend.print_service import compose_print


class PrintServiceTests(unittest.TestCase):
    def test_compose_print_places_original_and_ai_images_into_slots(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            original_path = root / "original.png"
            ai_path = root / "ai.png"
            frame_path = root / "frame.png"
            output_path = root / "print.png"

            Image.new("RGB", (800, 600), (220, 40, 40)).save(original_path)
            Image.new("RGB", (800, 600), (40, 90, 220)).save(ai_path)
            Image.new("RGBA", (1200, 1800), (0, 0, 0, 0)).save(frame_path)

            compose_print(
                original_path=original_path,
                ai_path=ai_path,
                frame_path=frame_path,
                output_path=output_path,
            )

            composed = Image.open(output_path).convert("RGBA")

            self.assertEqual(composed.size, (1200, 1800))
            self.assertEqual(composed.getpixel((10, 10))[:3], (255, 255, 255))
            self.assertEqual(composed.getpixel((600, 650))[:3], (220, 40, 40))
            self.assertEqual(composed.getpixel((600, 1300))[:3], (40, 90, 220))

    def test_compose_print_applies_scale_and_offsets_per_slot(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            original_path = root / "original.png"
            ai_path = root / "ai.png"
            frame_path = root / "frame.png"
            output_path = root / "print.png"

            Image.new("RGB", (800, 600), (220, 40, 40)).save(original_path)
            Image.new("RGB", (800, 600), (40, 90, 220)).save(ai_path)
            Image.new("RGBA", (1200, 1800), (0, 0, 0, 0)).save(frame_path)

            compose_print(
                original_path=original_path,
                ai_path=ai_path,
                frame_path=frame_path,
                output_path=output_path,
                layout={
                    "original": {"scale": 0.5, "offset_x": 150, "offset_y": 60},
                    "ai": {"scale": 0.5, "offset_x": -120, "offset_y": -80},
                },
            )

            composed = Image.open(output_path).convert("RGBA")

            self.assertEqual(composed.getpixel((330, 470))[:3], (255, 255, 255))
            self.assertEqual(composed.getpixel((760, 700))[:3], (220, 40, 40))
            self.assertEqual(composed.getpixel((320, 1140))[:3], (40, 90, 220))
            self.assertEqual(composed.getpixel((930, 1490))[:3], (255, 255, 255))


if __name__ == "__main__":
    unittest.main()

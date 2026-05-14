import asyncio
import unittest
import warnings
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, patch

from PIL import Image

from backend.routers import printing as printing_router
from backend.session import session

warnings.filterwarnings("ignore", category=ResourceWarning)


class PrintApiTests(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.tmpdir = TemporaryDirectory()
        root = Path(self.tmpdir.name)
        self.sessions_folder = root / "sessions"
        self.frames_folder = root / "frames"
        self.sessions_folder.mkdir(parents=True, exist_ok=True)
        self.frames_folder.mkdir(parents=True, exist_ok=True)

        Image.new("RGBA", (1200, 1800), (0, 0, 0, 0)).save(self.frames_folder / "frame-test.png")

        self.patchers = [
            patch("backend.routers.printing.manager.broadcast_session", AsyncMock()),
            patch("backend.print_service.FRAMES_FOLDER", str(self.frames_folder)),
        ]
        for patcher in self.patchers:
            patcher.start()

        session.sessions_root = self.sessions_folder
        session.reset()
        session.start_session(session_id="session-a")

        source = root / "input.jpg"
        Image.new("RGB", (800, 600), (220, 40, 40)).save(source)
        shot = session.add_shot_from_file(source, source_name="input.jpg", source_type="test")
        session.finish_capture()
        session.select_shot(shot["shot_id"])
        session.mark_queued("prompt-a")
        session.start_processing_session("session-a")
        Image.new("RGB", (800, 600), (50, 80, 200)).save(root / "result.png")
        session.cache_result_file("session-a", "result.png", (root / "result.png").read_bytes(), "image/png")
        session.mark_result_ready("session-a", result_filename="result.png")

    def tearDown(self):
        for patcher in reversed(self.patchers):
            patcher.stop()
        session.reset()
        self.tmpdir.cleanup()
        self.loop.close()
        asyncio.set_event_loop(None)

    def test_list_frames_returns_available_frame_catalog(self):
        payload = printing_router.list_frames()

        self.assertEqual(len(payload["frames"]), 1)
        self.assertEqual(payload["frames"][0]["frame_id"], "frame-test")

    def test_compose_print_creates_print_output_and_updates_session(self):
        response = self.loop.run_until_complete(
            printing_router.compose_print(
                printing_router.ComposePrintRequest(
                    session_id="session-a",
                    frame_id="frame-test",
                    result_id="result-001",
                    layout=printing_router.ComposePrintLayoutRequest(
                        original=printing_router.SlotLayoutRequest(scale=0.9, offset_x=20, offset_y=-10),
                        ai=printing_router.SlotLayoutRequest(scale=1.1, offset_x=-15, offset_y=25),
                    ),
                )
            )
        )

        detail = session.get_session("session-a")

        self.assertEqual(response["print_output"]["frame_id"], "frame-test")
        self.assertEqual(detail["selected_frame_id"], "frame-test")
        self.assertEqual(detail["selected_generated_result_id"], "result-001")
        self.assertEqual(len(detail["print_outputs"]), 1)
        self.assertEqual(detail["print_outputs"][0]["layout"]["original"]["offset_x"], 20)
        self.assertEqual(detail["print_outputs"][0]["layout"]["ai"]["scale"], 1.1)
        self.assertTrue(Path(detail["print_outputs"][0]["local_path"]).exists())


if __name__ == "__main__":
    unittest.main()

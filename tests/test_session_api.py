import asyncio
import unittest
import warnings
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from backend.routers import run as run_router
from backend.session import session

warnings.filterwarnings("ignore", category=ResourceWarning)


class SessionApiTests(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.tmpdir = TemporaryDirectory()
        root = Path(self.tmpdir.name)
        self.watch_folder = root / "input"
        self.sessions_folder = root / "sessions"
        self.watch_folder.mkdir(parents=True, exist_ok=True)
        self.sessions_folder.mkdir(parents=True, exist_ok=True)

        self.patchers = [
            patch("backend.routers.run.WATCH_FOLDER", str(self.watch_folder)),
            patch("backend.routers.run.manager.broadcast_session", AsyncMock()),
        ]
        for patcher in self.patchers:
            patcher.start()

        session.sessions_root = self.sessions_folder
        session.reset()

    def tearDown(self):
        for patcher in reversed(self.patchers):
            patcher.stop()
        session.reset()
        self.tmpdir.cleanup()
        self.loop.close()
        asyncio.set_event_loop(None)

    def test_start_session_returns_capturing_phase(self):
        body = self.loop.run_until_complete(run_router.start_session())

        self.assertEqual(body["phase"], "capturing")
        self.assertTrue(body["session_id"].startswith("session-"))

    def test_finish_capture_and_select_shot(self):
        self.loop.run_until_complete(run_router.start_session())
        source = Path(self.tmpdir.name) / "input.jpg"
        source.write_bytes(b"fake-image")
        shot = session.add_shot_from_file(source, source_name="input.jpg", source_type="test")

        finish_response = self.loop.run_until_complete(run_router.finish_capture())
        select_response = self.loop.run_until_complete(
            run_router.select_shot(run_router.SelectShotRequest(shot_id=shot["shot_id"]))
        )

        self.assertEqual(finish_response["phase"], "reviewing")
        self.assertEqual(select_response["selected_shot_id"], shot["shot_id"])
        self.assertEqual(select_response["phase"], "reviewing")

    def test_run_selected_requires_selected_shot(self):
        self.loop.run_until_complete(run_router.start_session())
        self.loop.run_until_complete(run_router.finish_capture())

        with self.assertRaises(HTTPException) as exc:
            self.loop.run_until_complete(run_router.run_selected())

        self.assertEqual(exc.exception.status_code, 409)
        self.assertIn("선택된 컷", str(exc.exception.detail))


if __name__ == "__main__":
    unittest.main()

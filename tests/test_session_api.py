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

    def test_can_start_new_session_while_previous_one_is_processing(self):
        first_session = self.loop.run_until_complete(run_router.start_session())
        first_session_id = first_session["session_id"]
        source = Path(self.tmpdir.name) / "input.jpg"
        source.write_bytes(b"fake-image")
        shot = session.add_shot_from_file(source, source_name="input.jpg", source_type="test")
        self.loop.run_until_complete(run_router.finish_capture())
        self.loop.run_until_complete(
            run_router.select_shot(run_router.SelectShotRequest(shot_id=shot["shot_id"]))
        )

        async def fake_enqueue_selected(session_id):
            session.mark_queued("prompt-a", session_id=session_id)
            return "prompt-a"

        with patch("backend.routers.run.runner.enqueue_selected", AsyncMock(side_effect=fake_enqueue_selected)):
            self.loop.run_until_complete(run_router.run_selected())

        next_session = self.loop.run_until_complete(run_router.start_session())

        self.assertEqual(next_session["active_capture_session_id"], next_session["current_session"]["session_id"])
        self.assertEqual(next_session["processing_sessions"][0]["session_id"], first_session_id)

    def test_can_read_session_history_list_and_detail(self):
        first_session = self.loop.run_until_complete(run_router.start_session())
        first_session_id = first_session["session_id"]
        source = Path(self.tmpdir.name) / "input.jpg"
        source.write_bytes(b"fake-image")
        shot = session.add_shot_from_file(source, source_name="input.jpg", source_type="test")
        self.loop.run_until_complete(run_router.finish_capture())
        self.loop.run_until_complete(
            run_router.select_shot(run_router.SelectShotRequest(shot_id=shot["shot_id"]))
        )
        session.mark_completed(first_session_id)

        listing = run_router.list_sessions()
        detail = run_router.get_session_detail(first_session_id)

        self.assertTrue(any(item["session_id"] == first_session_id for item in listing["sessions"]))
        self.assertEqual(detail["session_id"], first_session_id)


if __name__ == "__main__":
    unittest.main()

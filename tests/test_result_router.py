import asyncio
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, patch

from backend.routers import result as result_router
from backend.session import session


class ResultRouterTests(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.tmpdir = TemporaryDirectory()
        root = Path(self.tmpdir.name)
        self.sessions_root = root / "sessions"
        self.sessions_root.mkdir(parents=True, exist_ok=True)

        session.sessions_root = self.sessions_root
        session.reset()
        session.start_session(session_id="session-test-001")
        source = root / "input.jpg"
        source.write_bytes(b"fake-image")
        shot = session.add_shot_from_file(source, source_name="input.jpg", source_type="test")
        session.finish_capture()
        session.select_shot(shot["shot_id"])
        session.mark_queued("prompt-123")
        session.start_processing_session("session-test-001")
        session.cache_result_file("session-test-001", "remote-result.png", b"cached-result", "image/png")
        session.mark_result_ready("session-test-001", "remote-result.png")

    def tearDown(self):
        session.reset()
        self.tmpdir.cleanup()
        self.loop.close()
        asyncio.set_event_loop(None)

    def test_result_route_prefers_local_cached_file(self):
        async def scenario():
            with patch("backend.routers.result.get_output_image_info", AsyncMock()) as remote_info:
                response = await result_router.result("prompt-123")
                self.assertEqual(response.path, session.get_session("session-test-001")["result_local_path"])
                remote_info.assert_not_awaited()

        self.loop.run_until_complete(scenario())


if __name__ == "__main__":
    unittest.main()

import asyncio
import contextlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, patch

from backend import runner
from backend.session import session


class _FakeWebSocket:
    def __init__(self, prompt_id):
        self.prompt_id = prompt_id
        self._sent = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._sent:
            raise StopAsyncIteration
        self._sent = True
        return json.dumps({
            "type": "executed",
            "data": {"prompt_id": self.prompt_id},
        })


class RunnerWorkerTests(unittest.TestCase):
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
        runner._queue = asyncio.Queue()

    def tearDown(self):
        session.reset()
        asyncio.set_event_loop(self.loop)
        runner._queue = asyncio.Queue()
        self.tmpdir.cleanup()
        self.loop.close()
        asyncio.set_event_loop(None)

    def test_worker_marks_result_ready_after_executed_message(self):
        async def scenario():
            await runner._queue.put(("session-test-001", "prompt-123", "client-1"))
            with patch("backend.runner.websockets.connect", return_value=_FakeWebSocket("prompt-123")), \
                 patch("backend.runner.comfy_client.get_output_image", AsyncMock(return_value="result.png")), \
                 patch("backend.runner.manager.broadcast_session", AsyncMock()) as broadcast_session:

                worker = asyncio.create_task(runner.run_worker())
                await asyncio.wait_for(runner._queue.join(), timeout=2)
                ready_session = session.get_session("session-test-001")
                self.assertEqual(ready_session["phase"], "result_ready")
                self.assertEqual(ready_session["result_filename"], "result.png")
                broadcast_session.assert_awaited()
                worker.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await worker

        self.loop.run_until_complete(scenario())


if __name__ == "__main__":
    unittest.main()

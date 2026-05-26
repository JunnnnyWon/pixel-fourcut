import asyncio
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, patch

from backend import runner
from backend.session import session


class RunnerEnqueueTests(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.tmpdir = TemporaryDirectory()
        root = Path(self.tmpdir.name)
        self.sessions_root = root / "sessions"
        self.presets_root = root / "presets"
        self.sessions_root.mkdir(parents=True, exist_ok=True)
        self.presets_root.mkdir(parents=True, exist_ok=True)

        session.sessions_root = self.sessions_root
        session.reset()
        session.start_session(session_id="session-test-001")

        source = root / "input.jpg"
        source.write_bytes(b"fake-image")
        shot = session.add_shot_from_file(source, source_name="input.jpg", source_type="test")
        session.finish_capture()
        session.select_shot(shot["shot_id"])

        (self.presets_root / "active.json").write_text(json.dumps({
            "1": {"class_type": "LoadImage", "inputs": {"image": "placeholder.png"}}
        }), encoding="utf-8")

        self.preset_patcher = patch("backend.runner.PRESETS_FOLDER", str(self.presets_root))
        self.preset_patcher.start()
        runner._queue = asyncio.Queue()

    def tearDown(self):
        self.preset_patcher.stop()
        asyncio.set_event_loop(self.loop)
        runner._queue = asyncio.Queue()
        session.reset()
        self.tmpdir.cleanup()
        self.loop.close()
        asyncio.set_event_loop(None)

    def test_enqueue_selected_marks_queued_and_queues_prompt(self):
        with patch("backend.runner.comfy_client.upload_image", AsyncMock(return_value="uploaded.png")) as upload_image, \
             patch("backend.runner.comfy_client.patch_workflow", return_value={"patched": True}) as patch_workflow, \
             patch("backend.runner.comfy_client.queue_prompt", AsyncMock(return_value="prompt-123")) as queue_prompt:

            prompt_id = asyncio.run(runner.enqueue_selected(session_id="session-test-001"))

        self.assertEqual(prompt_id, "prompt-123")
        processing_session = session.processing_sessions[0]
        self.assertEqual(processing_session["session_id"], "session-test-001")
        self.assertEqual(processing_session["phase"], "queued")
        self.assertEqual(processing_session["prompt_id"], "prompt-123")
        self.assertEqual(runner._queue.qsize(), 1)
        queued_item = asyncio.run(runner._queue.get())
        self.assertEqual(queued_item[3], "shot-001")
        upload_image.assert_awaited_once()
        patch_workflow.assert_called_once()
        queue_prompt.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()

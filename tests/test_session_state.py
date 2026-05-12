import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.session import SessionState


class SessionStateTests(unittest.TestCase):
    def test_start_session_creates_session_and_shots_directory(self):
        with TemporaryDirectory() as tmpdir:
            sessions_root = Path(tmpdir) / "sessions"
            state = SessionState(sessions_root)

            snapshot = state.start_session(session_id="session-test-001")

            self.assertEqual(snapshot["phase"], "capturing")
            self.assertEqual(snapshot["session_id"], "session-test-001")
            self.assertEqual(snapshot["shots"], [])
            self.assertTrue((sessions_root / "session-test-001" / "shots").exists())

    def test_add_shot_copies_file_into_active_session(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            sessions_root = root / "sessions"
            source = root / "input.jpg"
            source.write_bytes(b"fake-image")

            state = SessionState(sessions_root)
            state.start_session(session_id="session-test-001")

            shot = state.add_shot_from_file(source, source_name="input.jpg", source_type="watcher")

            self.assertEqual(state.phase, "capturing")
            self.assertEqual(shot["shot_id"], "shot-001")
            self.assertEqual(shot["filename"], "shot-001.jpg")
            self.assertEqual(shot["source"], "watcher")
            self.assertEqual(len(state.shots), 1)
            self.assertEqual(state.preview_shot_id, "shot-001")
            self.assertEqual(state.preview_shot["filename"], "shot-001.jpg")
            self.assertIsNotNone(state.preview_until)
            self.assertTrue((sessions_root / "session-test-001" / "shots" / "shot-001.jpg").exists())

    def test_finish_capture_and_select_shot_updates_review_state(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            sessions_root = root / "sessions"
            source = root / "input.jpg"
            source.write_bytes(b"fake-image")

            state = SessionState(sessions_root)
            state.start_session(session_id="session-test-001")
            shot = state.add_shot_from_file(source, source_name="input.jpg", source_type="watcher")

            state.finish_capture()
            snapshot = state.select_shot(shot["shot_id"])

            self.assertEqual(snapshot["phase"], "reviewing")
            self.assertEqual(snapshot["selected_shot_id"], shot["shot_id"])
            self.assertEqual(snapshot["selected_shot"]["filename"], "shot-001.jpg")

    def test_mark_processing_and_result_ready(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            sessions_root = root / "sessions"
            source = root / "input.jpg"
            source.write_bytes(b"fake-image")

            state = SessionState(sessions_root)
            state.start_session(session_id="session-test-001")
            shot = state.add_shot_from_file(source, source_name="input.jpg", source_type="watcher")
            state.finish_capture()
            state.select_shot(shot["shot_id"])

            processing = state.mark_processing(prompt_id="prompt-123")
            ready = state.mark_result_ready(result_filename="result.png")

            self.assertEqual(processing["phase"], "processing")
            self.assertEqual(processing["prompt_id"], "prompt-123")
            self.assertEqual(ready["phase"], "result_ready")
            self.assertEqual(ready["result_filename"], "result.png")


if __name__ == "__main__":
    unittest.main()

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

            self.assertEqual(processing["current_session"], None)
            self.assertEqual(processing["processing_sessions"][0]["phase"], "processing")
            self.assertEqual(processing["processing_sessions"][0]["prompt_id"], "prompt-123")
            self.assertEqual(ready["print_ready_sessions"][0]["phase"], "result_ready")
            self.assertEqual(ready["print_ready_sessions"][0]["result_filename"], "result.png")

    def test_can_start_new_capture_session_while_previous_session_is_processing(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            sessions_root = root / "sessions"
            source = root / "input.jpg"
            source.write_bytes(b"fake-image")

            state = SessionState(sessions_root)
            state.start_session(session_id="session-a")
            shot = state.add_shot_from_file(source, source_name="input.jpg", source_type="watcher")
            state.finish_capture()
            state.select_shot(shot["shot_id"])
            state.mark_queued(prompt_id="prompt-a")

            snapshot = state.start_session(session_id="session-b")

            self.assertEqual(snapshot["active_capture_session_id"], "session-b")
            self.assertEqual(snapshot["current_session"]["session_id"], "session-b")
            self.assertEqual(snapshot["processing_sessions"][0]["session_id"], "session-a")
            self.assertEqual(snapshot["processing_sessions"][0]["phase"], "queued")

    def test_result_ready_is_written_back_to_original_processing_session(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            sessions_root = root / "sessions"
            source = root / "input.jpg"
            source.write_bytes(b"fake-image")

            state = SessionState(sessions_root)
            state.start_session(session_id="session-a")
            shot = state.add_shot_from_file(source, source_name="input.jpg", source_type="watcher")
            state.finish_capture()
            state.select_shot(shot["shot_id"])
            state.mark_queued(prompt_id="prompt-a")
            state.start_processing_session("session-a")
            state.start_session(session_id="session-b")

            snapshot = state.mark_result_ready("session-a", result_filename="result-a.png")

            processing_ids = [item["session_id"] for item in snapshot["processing_sessions"]]
            ready_ids = [item["session_id"] for item in snapshot["print_ready_sessions"]]
            self.assertNotIn("session-a", processing_ids)
            self.assertIn("session-a", ready_ids)
            self.assertEqual(snapshot["current_session"]["session_id"], "session-b")

    def test_load_from_disk_restores_previous_sessions(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            sessions_root = root / "sessions"
            source = root / "input.jpg"
            source.write_bytes(b"fake-image")

            original = SessionState(sessions_root)
            original.start_session(session_id="session-a")
            shot = original.add_shot_from_file(source, source_name="input.jpg", source_type="watcher")
            original.finish_capture()
            original.select_shot(shot["shot_id"])
            original.mark_queued(prompt_id="prompt-a")
            original.start_processing_session("session-a")
            original.cache_result_file("session-a", "result-a.png", b"result-bytes", "image/png")
            original.mark_result_ready("session-a", result_filename="result-a.png")
            original.start_session(session_id="session-b")

            restored = SessionState(sessions_root)
            restored.load_from_disk()

            self.assertEqual(restored.current_session["session_id"], "session-b")
            self.assertEqual(restored.print_ready_sessions[0]["session_id"], "session-a")
            self.assertTrue(Path(restored.print_ready_sessions[0]["result_local_path"]).exists())

    def test_cache_result_file_accumulates_generated_results(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            sessions_root = root / "sessions"
            source = root / "input.jpg"
            source.write_bytes(b"fake-image")

            state = SessionState(sessions_root)
            state.start_session(session_id="session-a")
            shot = state.add_shot_from_file(source, source_name="input.jpg", source_type="watcher")
            state.finish_capture()
            state.select_shot(shot["shot_id"])
            state.mark_queued(prompt_id="prompt-a")
            state.start_processing_session("session-a")
            state.cache_result_file("session-a", "result-a.png", b"one", "image/png")
            state.mark_result_ready("session-a", result_filename="result-a.png")
            state.mark_queued(prompt_id="prompt-b", session_id="session-a")
            state.start_processing_session("session-a")
            state.cache_result_file("session-a", "result-b.png", b"two", "image/png")
            state.mark_result_ready("session-a", result_filename="result-b.png")

            detail = state.get_session("session-a")

            self.assertEqual(len(detail["generated_results"]), 2)
            self.assertEqual(detail["generated_results"][0]["source_filename"], "result-a.png")
            self.assertEqual(detail["generated_results"][1]["source_filename"], "result-b.png")


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image

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

    def test_start_session_generates_datetime_session_id_with_suffix_on_collision(self):
        with TemporaryDirectory() as tmpdir:
            sessions_root = Path(tmpdir) / "sessions"
            state = SessionState(sessions_root)

            with patch("backend.session.datetime") as mocked_datetime:
                fixed_now = unittest.mock.Mock()
                fixed_now.strftime.return_value = "20260515_20_30"
                fixed_now.isoformat.return_value = "2026-05-15T20:30:00"
                mocked_datetime.now.return_value = fixed_now

                first = state.start_session()
                state.active_capture_session_id = None
                second = state.start_session()

            self.assertEqual(first["session_id"], "20260515_20_30")
            self.assertEqual(second["session_id"], "20260515_20_30_01")

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

    def test_load_from_disk_restores_latest_active_capture_session(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            sessions_root = root / "sessions"
            source = root / "input.jpg"
            source.write_bytes(b"fake-image")

            original = SessionState(sessions_root)
            original.start_session(session_id="session-current-001")
            shot_a = original.add_shot_from_file(source, source_name="a.jpg", source_type="watcher")
            original.finish_capture()
            original.select_shot(shot_a["shot_id"])

            original.active_capture_session_id = None
            original.start_session(session_id="session-20260514-123318-415861")
            shot_b = original.add_shot_from_file(source, source_name="b.jpg", source_type="watcher")
            original.finish_capture()
            original.select_shot(shot_b["shot_id"])

            restored = SessionState(sessions_root)
            restored.load_from_disk()

            self.assertEqual(restored.current_session["session_id"], "session-20260514-123318-415861")

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

    def test_print_outputs_and_frame_selection_persist(self):
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
            state.cache_result_file("session-a", "result-a.png", b"result-bytes", "image/png")
            state.mark_result_ready("session-a", result_filename="result-a.png")

            composite = Image.new("RGBA", (1200, 1800), (255, 255, 255, 255))
            composite_bytes = root / "composite.png"
            composite.save(composite_bytes)

            state.cache_print_file(
                "session-a",
                frame_id="frame-01-signature-white",
                result_id="result-001",
                content=composite_bytes.read_bytes(),
                media_type="image/png",
                layout={
                    "original": {"scale": 0.95, "offset_x": 12, "offset_y": -8},
                    "ai": {"scale": 1.1, "offset_x": -4, "offset_y": 14},
                },
            )

            restored = SessionState(sessions_root)
            restored.load_from_disk()
            detail = restored.get_session("session-a")

            self.assertEqual(detail["selected_frame_id"], "frame-01-signature-white")
            self.assertEqual(detail["selected_generated_result_id"], "result-001")
            self.assertEqual(len(detail["print_outputs"]), 1)
            self.assertEqual(detail["print_outputs"][0]["layout"]["ai"]["offset_y"], 14)
            self.assertTrue(Path(detail["print_outputs"][0]["local_path"]).exists())


if __name__ == "__main__":
    unittest.main()

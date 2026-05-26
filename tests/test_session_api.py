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
        self.assertRegex(body["session_id"], r"^\d{8}_\d{2}_\d{2}(?:_\d{2})?$")

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

    def test_finish_capture_rejects_zero_shot_session(self):
        self.loop.run_until_complete(run_router.start_session())

        with self.assertRaises(HTTPException) as exc:
            self.loop.run_until_complete(run_router.finish_capture())

        self.assertEqual(exc.exception.status_code, 409)
        self.assertIn("사진이 아직 없습니다", str(exc.exception.detail))

    def test_run_selected_requires_selected_shot(self):
        self.loop.run_until_complete(run_router.start_session())
        source = Path(self.tmpdir.name) / "input.jpg"
        source.write_bytes(b"fake-image")
        session.add_shot_from_file(source, source_name="input.jpg", source_type="test")
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

    def test_retry_capture_and_discard_current_team(self):
        started = self.loop.run_until_complete(run_router.start_session())
        session_id = started["session_id"]
        source = Path(self.tmpdir.name) / "input.jpg"
        source.write_bytes(b"fake-image")
        shot = session.add_shot_from_file(source, source_name="input.jpg", source_type="test")
        self.loop.run_until_complete(run_router.finish_capture())
        self.loop.run_until_complete(
            run_router.select_shot(run_router.SelectShotRequest(shot_id=shot["shot_id"]))
        )

        retried = self.loop.run_until_complete(run_router.retry_capture())
        discarded = self.loop.run_until_complete(
            run_router.discard_session(run_router.SessionActionRequest(session_id=session_id))
        )

        self.assertEqual(retried["phase"], "capturing")
        self.assertEqual(discarded["discarded"], session_id)
        self.assertIsNone(session.current_session)

    def test_can_rerun_previous_session(self):
        started = self.loop.run_until_complete(run_router.start_session())
        session_id = started["session_id"]
        source = Path(self.tmpdir.name) / "input.jpg"
        source.write_bytes(b"fake-image")
        shot = session.add_shot_from_file(source, source_name="input.jpg", source_type="test")
        self.loop.run_until_complete(run_router.finish_capture())
        self.loop.run_until_complete(
            run_router.select_shot(run_router.SelectShotRequest(shot_id=shot["shot_id"]))
        )
        session.mark_completed(session_id)

        with patch("backend.routers.run.runner.enqueue_selected", AsyncMock(return_value="prompt-rerun")):
            rerun = self.loop.run_until_complete(
                run_router.rerun_session(run_router.SessionActionRequest(session_id=session_id))
            )

        self.assertEqual(rerun["prompt_id"], "prompt-rerun")

    def test_complete_session_requires_print_output_first(self):
        started = self.loop.run_until_complete(run_router.start_session())
        session_id = started["session_id"]
        source = Path(self.tmpdir.name) / "input.jpg"
        source.write_bytes(b"fake-image")
        shot = session.add_shot_from_file(source, source_name="input.jpg", source_type="test")
        self.loop.run_until_complete(run_router.finish_capture())
        self.loop.run_until_complete(
            run_router.select_shot(run_router.SelectShotRequest(shot_id=shot["shot_id"]))
        )
        session.mark_queued("prompt-a")
        session.start_processing_session(session_id)
        session.cache_result_file(session_id, "result.png", b"png", "image/png")
        session.mark_result_ready(session_id, result_filename="result.png")

        with self.assertRaises(HTTPException) as exc:
            self.loop.run_until_complete(
                run_router.complete_session(run_router.SessionActionRequest(session_id=session_id))
            )

        self.assertEqual(exc.exception.status_code, 409)
        self.assertIn("최종 인화본을 먼저", str(exc.exception.detail))

    def test_complete_session_requires_printer_dispatch(self):
        started = self.loop.run_until_complete(run_router.start_session())
        session_id = started["session_id"]
        source = Path(self.tmpdir.name) / "input.jpg"
        source.write_bytes(b"fake-image")
        shot = session.add_shot_from_file(source, source_name="input.jpg", source_type="test")
        self.loop.run_until_complete(run_router.finish_capture())
        self.loop.run_until_complete(
            run_router.select_shot(run_router.SelectShotRequest(shot_id=shot["shot_id"]))
        )
        session.mark_queued("prompt-a")
        session.start_processing_session(session_id)
        session.cache_result_file(session_id, "result.png", b"png", "image/png")
        session.mark_result_ready(session_id, result_filename="result.png")
        print_output = session.cache_print_file(
            session_id,
            frame_id="frame-01-signature-white",
            result_id="result-001",
            content=b"png",
            media_type="image/png",
        )

        with self.assertRaises(HTTPException) as exc:
            self.loop.run_until_complete(
                run_router.complete_session(
                    run_router.SessionActionRequest(session_id=session_id, print_id=print_output["print_id"])
                )
            )

        self.assertEqual(exc.exception.status_code, 409)
        self.assertIn("프린터로 출력한 뒤", str(exc.exception.detail))

    def test_complete_session_succeeds_after_printer_dispatch(self):
        started = self.loop.run_until_complete(run_router.start_session())
        session_id = started["session_id"]
        source = Path(self.tmpdir.name) / "input.jpg"
        source.write_bytes(b"fake-image")
        shot = session.add_shot_from_file(source, source_name="input.jpg", source_type="test")
        self.loop.run_until_complete(run_router.finish_capture())
        self.loop.run_until_complete(
            run_router.select_shot(run_router.SelectShotRequest(shot_id=shot["shot_id"]))
        )
        session.mark_queued("prompt-a")
        session.start_processing_session(session_id)
        session.cache_result_file(session_id, "result.png", b"png", "image/png")
        session.mark_result_ready(session_id, result_filename="result.png")
        print_output = session.cache_print_file(
            session_id,
            frame_id="frame-01-signature-white",
            result_id="result-001",
            content=b"png",
            media_type="image/png",
        )
        session.record_printer_job(session_id, print_id=print_output["print_id"], printer_name="SELPHY-LEFT")

        response = self.loop.run_until_complete(
            run_router.complete_session(
                run_router.SessionActionRequest(session_id=session_id, print_id=print_output["print_id"])
            )
        )

        completed = next(item for item in response["completed_sessions"] if item["session_id"] == session_id)
        self.assertEqual(completed["phase"], "completed")

    def test_can_reselect_shot_for_existing_session(self):
        started = self.loop.run_until_complete(run_router.start_session())
        session_id = started["session_id"]
        source_a = Path(self.tmpdir.name) / "input-a.jpg"
        source_b = Path(self.tmpdir.name) / "input-b.jpg"
        source_a.write_bytes(b"fake-image-a")
        source_b.write_bytes(b"fake-image-b")
        shot_a = session.add_shot_from_file(source_a, source_name="input-a.jpg", source_type="test")
        shot_b = session.add_shot_from_file(source_b, source_name="input-b.jpg", source_type="test")
        self.loop.run_until_complete(run_router.finish_capture())
        self.loop.run_until_complete(
            run_router.select_shot(run_router.SelectShotRequest(shot_id=shot_a["shot_id"]))
        )
        session.mark_completed(session_id)

        response = self.loop.run_until_complete(
            run_router.select_session_shot(session_id, run_router.SelectShotRequest(shot_id=shot_b["shot_id"]))
        )

        self.assertEqual(response["selected_shot_id"], shot_b["shot_id"])
        self.assertEqual(response["selected_shot"]["source_filename"], "input-b.jpg")


if __name__ == "__main__":
    unittest.main()

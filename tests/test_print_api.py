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

    def test_list_printers_returns_backend_printer_catalog(self):
        with patch("backend.routers.printing.get_printers", return_value=[{"name": "SELPHY-LEFT"}]):
            payload = printing_router.list_printers()

        self.assertEqual(payload["printers"][0]["name"], "SELPHY-LEFT")

    def test_printer_diagnostics_returns_service_snapshot(self):
        with patch("backend.routers.printing.get_printer_diagnostics", return_value={"visible_printers": [], "hidden_printers": []}):
            payload = printing_router.printer_diagnostics()

        self.assertIn("visible_printers", payload)

    def test_printer_capabilities_returns_service_snapshot(self):
        with patch("backend.routers.printing.get_printer_capabilities", return_value={"preferred_paper": {"name": "Postcard"}}):
            payload = printing_router.printer_capabilities("SELPHY-LEFT")

        self.assertEqual(payload["preferred_paper"]["name"], "Postcard")

    def test_send_to_printer_records_printer_job(self):
        response = self.loop.run_until_complete(
            printing_router.compose_print(
                printing_router.ComposePrintRequest(
                    session_id="session-a",
                    frame_id="frame-test",
                    result_id="result-001",
                )
            )
        )

        with patch("backend.routers.printing.send_image_to_printer", return_value={"status": "sent", "windows_job_id": 41, "job_status": "Spooling", "paper_name": "Postcard", "paper_width": 394, "paper_height": 583}) as send_image:
            payload = self.loop.run_until_complete(
                printing_router.send_to_printer(
                    printing_router.SendPrintRequest(
                        session_id="session-a",
                        print_id=response["print_output"]["print_id"],
                        printer_name="SELPHY-LEFT",
                        copies=2,
                    )
                )
            )

        detail = session.get_session("session-a")

        send_image.assert_called_once()
        self.assertEqual(payload["printer_job"]["printer_name"], "SELPHY-LEFT")
        self.assertEqual(payload["printer_job"]["windows_job_id"], 41)
        self.assertEqual(detail["latest_printer_job"]["copies"], 2)
        self.assertEqual(detail["print_outputs"][0]["windows_job_id"], 41)
        self.assertEqual(detail["print_outputs"][0]["job_status"], "Spooling")
        self.assertEqual(detail["print_outputs"][0]["paper_name"], "Postcard")

    def test_refresh_printer_jobs_updates_live_job_status(self):
        response = self.loop.run_until_complete(
            printing_router.compose_print(
                printing_router.ComposePrintRequest(
                    session_id="session-a",
                    frame_id="frame-test",
                    result_id="result-001",
                )
            )
        )
        session.record_printer_job(
            "session-a",
            print_id=response["print_output"]["print_id"],
            printer_name="SELPHY-LEFT",
            copies=1,
            windows_job_id=41,
        )

        with patch("backend.routers.printing.get_print_job", return_value={
            "windows_job_id": 41,
            "printer_name": "SELPHY-LEFT",
            "document_name": "print-001.png",
            "job_status": "Printing",
            "submitted_time": "2026-05-18T10:00:00",
        }):
            payload = self.loop.run_until_complete(
                printing_router.refresh_printer_jobs("session-a")
            )

        detail = session.get_session("session-a")

        self.assertEqual(payload["printer_jobs"][0]["job_status"], "Printing")
        self.assertEqual(detail["print_outputs"][0]["job_status"], "Printing")

    def test_refresh_printer_jobs_marks_missing_jobs(self):
        response = self.loop.run_until_complete(
            printing_router.compose_print(
                printing_router.ComposePrintRequest(
                    session_id="session-a",
                    frame_id="frame-test",
                    result_id="result-001",
                )
            )
        )
        session.record_printer_job(
            "session-a",
            print_id=response["print_output"]["print_id"],
            printer_name="SELPHY-LEFT",
            copies=1,
            windows_job_id=41,
        )

        with patch("backend.routers.printing.get_print_job", return_value=None):
            payload = self.loop.run_until_complete(
                printing_router.refresh_printer_jobs("session-a")
            )

        detail = session.get_session("session-a")

        self.assertEqual(payload["printer_jobs"][0]["status"], "completed_or_missing")
        self.assertEqual(detail["print_outputs"][0]["status"], "completed_or_missing")

    def test_send_printer_test_page_dispatches_without_session(self):
        with patch("backend.routers.printing.send_image_to_printer", return_value={"status": "sent", "printer_name": "SELPHY-LEFT"}) as send_image:
            payload = printing_router.send_printer_test_page(
                printing_router.TestPrintRequest(printer_name="SELPHY-LEFT", copies=1)
            )

        send_image.assert_called_once()
        self.assertEqual(payload["dispatch"]["printer_name"], "SELPHY-LEFT")


if __name__ == "__main__":
    unittest.main()

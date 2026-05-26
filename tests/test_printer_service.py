import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from backend import printer_service


class PrinterServiceTests(unittest.TestCase):
    def test_list_printers_returns_empty_on_non_windows(self):
        with patch("backend.printer_service.platform.system", return_value="Darwin"):
            printers = printer_service.list_printers()

        self.assertEqual(printers, [])

    def test_list_printers_normalizes_powershell_result(self):
        payload = json.dumps(
            [
                {
                    "Name": "SELPHY-LEFT",
                    "DriverName": "Canon SELPHY CP1500",
                    "PortName": "USB001",
                    "PrinterStatus": 3,
                    "WorkOffline": False,
                }
            ]
        )
        with patch("backend.printer_service.platform.system", return_value="Windows"), \
             patch("backend.printer_service._run_powershell", return_value=payload):
            printers = printer_service.list_printers()

        self.assertEqual(printers[0]["name"], "SELPHY-LEFT")
        self.assertEqual(printers[0]["driver_name"], "Canon SELPHY CP1500")
        self.assertEqual(printers[0]["is_available"], True)

    def test_list_printers_hides_virtual_printers_by_default(self):
        payload = json.dumps(
            [
                {
                    "Name": "Microsoft Print to PDF",
                    "DriverName": "Microsoft Print To PDF",
                    "PortName": "PORTPROMPT:",
                    "PrinterStatus": 0,
                    "WorkOffline": False,
                }
            ]
        )
        with patch("backend.printer_service.platform.system", return_value="Windows"), \
             patch("backend.printer_service._run_powershell", return_value=payload), \
             patch("backend.printer_service.SHOW_VIRTUAL_PRINTERS", False), \
             patch("backend.printer_service.PRINTER_NAME_ALLOWLIST", []):
            printers = printer_service.list_printers()

        self.assertEqual(printers, [])

    def test_get_printer_diagnostics_exposes_visible_and_hidden_lists(self):
        payload = json.dumps(
            [
                {
                    "Name": "Microsoft Print to PDF",
                    "DriverName": "Microsoft Print To PDF",
                    "PortName": "PORTPROMPT:",
                    "PrinterStatus": 0,
                    "WorkOffline": False,
                },
                {
                    "Name": "SELPHY-LEFT",
                    "DriverName": "Canon SELPHY CP1500",
                    "PortName": "USB001",
                    "PrinterStatus": 3,
                    "WorkOffline": False,
                }
            ]
        )
        with patch("backend.printer_service.platform.system", return_value="Windows"), \
             patch("backend.printer_service._run_powershell", return_value=payload), \
             patch("backend.printer_service.list_print_drivers", return_value=[{"name": "Canon SELPHY CP1500", "manufacturer": "Canon"}]), \
             patch("backend.printer_service.list_related_pnp_devices", return_value=[{"friendly_name": "Canon SELPHY CP1500"}]), \
             patch("backend.printer_service.SHOW_VIRTUAL_PRINTERS", False), \
             patch("backend.printer_service.PRINTER_NAME_ALLOWLIST", []):
            diagnostics = printer_service.get_printer_diagnostics()

        self.assertEqual([printer["name"] for printer in diagnostics["visible_printers"]], ["SELPHY-LEFT"])
        self.assertEqual([printer["name"] for printer in diagnostics["hidden_printers"]], ["Microsoft Print to PDF"])
        self.assertEqual(diagnostics["installed_print_drivers"][0]["name"], "Canon SELPHY CP1500")
        self.assertEqual(diagnostics["related_pnp_devices"][0]["friendly_name"], "Canon SELPHY CP1500")

    def test_list_printers_respects_name_allowlist(self):
        payload = json.dumps(
            [
                {
                    "Name": "SELPHY-LEFT",
                    "DriverName": "Canon SELPHY CP1500",
                    "PortName": "USB001",
                    "PrinterStatus": 3,
                    "WorkOffline": False,
                },
                {
                    "Name": "SELPHY-RIGHT",
                    "DriverName": "Canon SELPHY CP1500",
                    "PortName": "USB002",
                    "PrinterStatus": 3,
                    "WorkOffline": False,
                }
            ]
        )
        with patch("backend.printer_service.platform.system", return_value="Windows"), \
             patch("backend.printer_service._run_powershell", return_value=payload), \
             patch("backend.printer_service.PRINTER_NAME_ALLOWLIST", ["SELPHY-RIGHT"]), \
             patch("backend.printer_service.SHOW_VIRTUAL_PRINTERS", True):
            printers = printer_service.list_printers()

        self.assertEqual([printer["name"] for printer in printers], ["SELPHY-RIGHT"])

    def test_list_print_drivers_normalizes_powershell_result(self):
        payload = json.dumps(
            [
                {"Name": "Canon SELPHY CP1500", "Manufacturer": "Canon", "MajorVersion": 4}
            ]
        )
        with patch("backend.printer_service.platform.system", return_value="Windows"), \
             patch("backend.printer_service._run_powershell", return_value=payload):
            drivers = printer_service.list_print_drivers()

        self.assertEqual(drivers[0]["name"], "Canon SELPHY CP1500")

    def test_list_related_pnp_devices_normalizes_powershell_result(self):
        payload = json.dumps(
            [
                {"Status": "OK", "Class": "USB", "FriendlyName": "Canon SELPHY CP1500", "InstanceId": "USB\\VID_04A9"}
            ]
        )
        with patch("backend.printer_service.platform.system", return_value="Windows"), \
             patch("backend.printer_service._run_powershell", return_value=payload):
            devices = printer_service.list_related_pnp_devices()

        self.assertEqual(devices[0]["friendly_name"], "Canon SELPHY CP1500")

    def test_send_image_to_printer_raises_on_non_windows(self):
        with TemporaryDirectory() as tmpdir, patch("backend.printer_service.platform.system", return_value="Darwin"):
            image_path = Path(tmpdir) / "print.png"
            image_path.write_bytes(b"png")

            with self.assertRaises(RuntimeError):
                printer_service.send_image_to_printer(image_path, "SELPHY-LEFT")

    def test_send_image_to_printer_invokes_powershell_and_returns_status(self):
        with TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "print.png"
            image_path.write_bytes(b"png")
            with patch("backend.printer_service.platform.system", return_value="Windows"), \
                 patch("backend.printer_service.list_printers", return_value=[{"name": "SELPHY-LEFT", "is_available": True}]), \
                 patch("backend.printer_service._run_powershell", return_value='{"status":"sent","printer_name":"SELPHY-LEFT","copies":2,"windows_job_id":41,"job_status":"Spooling"}') as run_ps:
                payload = printer_service.send_image_to_printer(image_path, "SELPHY-LEFT", copies=2)

        self.assertEqual(payload["printer_name"], "SELPHY-LEFT")
        self.assertEqual(payload["copies"], 2)
        self.assertEqual(payload["windows_job_id"], 41)
        run_ps.assert_called_once()

    def test_send_image_to_printer_rejects_offline_printer(self):
        with TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "print.png"
            image_path.write_bytes(b"png")
            with patch("backend.printer_service.platform.system", return_value="Windows"), \
                 patch("backend.printer_service.list_printers", return_value=[{"name": "SELPHY-LEFT", "is_available": False}]):
                with self.assertRaises(RuntimeError):
                    printer_service.send_image_to_printer(image_path, "SELPHY-LEFT", copies=1)

    def test_get_print_job_returns_normalized_payload(self):
        payload = json.dumps(
            {
                "ID": 41,
                "PrinterName": "SELPHY-LEFT",
                "DocumentName": "print-001.png",
                "JobStatus": "Printing",
                "SubmittedTime": "2026-05-18T10:00:00",
            }
        )
        with patch("backend.printer_service.platform.system", return_value="Windows"), \
             patch("backend.printer_service._run_powershell", return_value=payload):
            job = printer_service.get_print_job("SELPHY-LEFT", 41)

        self.assertEqual(job["windows_job_id"], 41)
        self.assertEqual(job["job_status"], "Printing")

    def test_create_test_page_writes_image_file(self):
        with TemporaryDirectory() as tmpdir:
            output = printer_service.create_test_page(Path(tmpdir) / "test-page.png", "SELPHY-LEFT")
            self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()

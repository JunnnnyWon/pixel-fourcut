import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from backend.routers import presets as presets_router


class PresetsApiTests(unittest.TestCase):
    def test_list_presets_reports_active_when_only_active_json_exists(self):
        with TemporaryDirectory() as tmpdir:
            presets_dir = Path(tmpdir)
            workflow = {
                "1": {
                    "inputs": {"image": "x.png"},
                    "class_type": "LoadImage",
                }
            }
            (presets_dir / "active.json").write_text(json.dumps(workflow), encoding="utf-8")

            with patch.object(presets_router, "_dir", presets_dir):
                payload = presets_router.list_presets()

            self.assertEqual(payload["presets"], [])
            self.assertEqual(payload["active"], "active")


if __name__ == "__main__":
    unittest.main()

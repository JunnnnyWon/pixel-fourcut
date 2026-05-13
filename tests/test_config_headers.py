import unittest
from unittest.mock import patch

from backend import config


class ComfyHeaderConfigTests(unittest.TestCase):
    def test_build_comfyui_headers_merges_json_and_bearer_token(self):
        with patch.object(config, "COMFYUI_HEADERS_JSON", '{"X-Test":"yes"}'), \
             patch.object(config, "COMFYUI_BEARER_TOKEN", "secret-token"):
            headers = config.get_comfyui_headers()

        self.assertEqual(headers["X-Test"], "yes")
        self.assertEqual(headers["Authorization"], "Bearer secret-token")

    def test_build_comfyui_headers_handles_empty_values(self):
        with patch.object(config, "COMFYUI_HEADERS_JSON", ""), \
             patch.object(config, "COMFYUI_BEARER_TOKEN", ""):
            headers = config.get_comfyui_headers()

        self.assertEqual(headers, {})


if __name__ == "__main__":
    unittest.main()

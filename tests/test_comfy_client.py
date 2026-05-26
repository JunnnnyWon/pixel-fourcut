import unittest

from backend import comfy_client


class ComfyClientTests(unittest.TestCase):
    def test_patch_workflow_replaces_load_image_and_overrides_seed_inputs(self):
        workflow = {
            "1": {"class_type": "LoadImage", "inputs": {"image": "old.png"}},
            "2": {"class_type": "KSampler", "inputs": {"seed": 11, "steps": 20}},
            "3": {"class_type": "RandomNoise", "inputs": {"noise_seed": 22}},
            "4": {"class_type": "Text", "inputs": {"value": "keep-me"}},
        }

        patched = comfy_client.patch_workflow(workflow, "new.png", seed_override=123456)

        self.assertEqual(patched["1"]["inputs"]["image"], "new.png")
        self.assertEqual(patched["2"]["inputs"]["seed"], 123456)
        self.assertEqual(patched["3"]["inputs"]["noise_seed"], 123456)
        self.assertEqual(patched["4"]["inputs"]["value"], "keep-me")
        self.assertEqual(workflow["2"]["inputs"]["seed"], 11)


if __name__ == "__main__":
    unittest.main()

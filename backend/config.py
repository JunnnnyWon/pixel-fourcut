from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

_base = Path(__file__).parent.parent

COMFYUI_URL    = os.getenv("COMFYUI_URL",    "http://localhost:8188")
WATCH_FOLDER   = os.getenv("WATCH_FOLDER",   str(_base / "workspace" / "input"))
PRESETS_FOLDER = os.getenv("PRESETS_FOLDER", str(_base / "workspace" / "presets"))

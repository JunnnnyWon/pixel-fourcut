from dotenv import load_dotenv
import json
import os
from pathlib import Path

load_dotenv()

_base = Path(__file__).parent.parent

COMFYUI_URL    = os.getenv("COMFYUI_URL",    "http://localhost:8188")
COMFYUI_HEADERS_JSON = os.getenv("COMFYUI_HEADERS_JSON", "")
COMFYUI_BEARER_TOKEN = os.getenv("COMFYUI_BEARER_TOKEN", "")
WATCH_FOLDER   = os.getenv("WATCH_FOLDER",   str(_base / "workspace" / "input"))
PRESETS_FOLDER = os.getenv("PRESETS_FOLDER", str(_base / "workspace" / "presets"))
SESSIONS_FOLDER = os.getenv("SESSIONS_FOLDER", str(_base / "workspace" / "sessions"))
FRAMES_FOLDER = os.getenv("FRAMES_FOLDER", str(_base / "frontend" / "src" / "assets" / "frames"))


def get_comfyui_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    if COMFYUI_HEADERS_JSON:
        headers.update(json.loads(COMFYUI_HEADERS_JSON))
    if COMFYUI_BEARER_TOKEN:
        headers["Authorization"] = f"Bearer {COMFYUI_BEARER_TOKEN}"
    return headers

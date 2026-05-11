from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

# 기본 경로: .env 없을 때 프로젝트 내 workspace/ 사용 (Windows/Linux/Mac 공통)
_base = Path(__file__).parent.parent  # pixel_AI/

COMFYUI_URL    = os.getenv("COMFYUI_URL",    "http://localhost:8188")
WATCH_FOLDER   = os.getenv("WATCH_FOLDER",   str(_base / "workspace" / "input"))
PRESETS_FOLDER = os.getenv("PRESETS_FOLDER", str(_base / "workspace" / "presets"))

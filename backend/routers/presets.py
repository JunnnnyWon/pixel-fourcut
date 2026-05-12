import json
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.config import PRESETS_FOLDER

router = APIRouter(prefix="/api/presets")
_dir = Path(PRESETS_FOLDER)


def _ensure_dir():
    _dir.mkdir(parents=True, exist_ok=True)


@router.get("")
def list_presets():
    _ensure_dir()
    active = (_dir / "active.json").resolve()
    presets = []
    for f in sorted(_dir.glob("*.json")):
        if f.name == "active.json":
            continue
        presets.append({"name": f.stem, "active": f.resolve() == active})
    # detect active by content comparison
    active_name = None
    if (_dir / "active.json").exists():
        active_data = (_dir / "active.json").read_text()
        for f in _dir.glob("*.json"):
            if f.name != "active.json" and f.read_text() == active_data:
                active_name = f.stem
                break
    return {"presets": [p["name"] for p in presets], "active": active_name}


@router.post("")
async def upload_preset(name: str, file: UploadFile = File(...)):
    _ensure_dir()
    dest = _dir / f"{name}.json"
    content = await file.read()
    try:
        json.loads(content)  # validate JSON
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON")
    dest.write_bytes(content)
    return {"name": name}


@router.post("/{name}/activate")
def activate_preset(name: str):
    _ensure_dir()
    src = _dir / f"{name}.json"
    if not src.exists():
        raise HTTPException(404, "Preset not found")
    shutil.copy2(src, _dir / "active.json")
    return {"active": name}


@router.delete("/{name}")
def delete_preset(name: str):
    _ensure_dir()
    src = _dir / f"{name}.json"
    if not src.exists():
        raise HTTPException(404, "Preset not found")
    active = _dir / "active.json"
    if active.exists() and active.read_bytes() == src.read_bytes():
        active.unlink()
    src.unlink()
    return {"deleted": name}

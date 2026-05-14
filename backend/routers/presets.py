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
    active_path = _dir / "active.json"
    active = active_path.resolve()
    presets = []
    for f in sorted(_dir.glob("*.json")):
        if f.name == "active.json":
            continue
        presets.append({"name": f.stem, "active": f.resolve() == active})
    # detect active by content comparison
    active_name = None
    if active_path.exists():
        active_data = active_path.read_text(encoding="utf-8")
        for f in _dir.glob("*.json"):
            if f.name != "active.json" and f.read_text(encoding="utf-8") == active_data:
                active_name = f.stem
                break
        if active_name is None:
            active_name = "active"
    return {"presets": [p["name"] for p in presets], "active": active_name}


@router.post("")
async def upload_preset(name: str, file: UploadFile = File(...)):
    _ensure_dir()
    dest = _dir / f"{name}.json"
    content = await file.read()
    try:
        wf = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(400, "유효한 JSON 파일이 아닙니다.")
    # ComfyUI API 형식 검증: 최상위 키가 숫자이고 값이 dict여야 함
    if not isinstance(wf, dict) or not wf:
        raise HTTPException(400, "ComfyUI API 형식의 workflow.json이 아닙니다. ComfyUI에서 'Save (API Format)'으로 내보낸 파일을 사용하세요.")
    first_val = next(iter(wf.values()))
    if not isinstance(first_val, dict) or "class_type" not in first_val:
        raise HTTPException(400, "ComfyUI API 형식이 아닙니다. ComfyUI 우상단 설정에서 'Enable Dev Mode'를 켠 후 'Save (API Format)'으로 내보낸 파일을 사용하세요.")
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

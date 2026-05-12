import re
import time
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from backend.config import WATCH_FOLDER

router = APIRouter()
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _sanitize(filename: str) -> str:
    """타임스탬프 prefix + 특수문자 제거"""
    p = Path(filename)
    stem = re.sub(r"[^\w\-]", "_", p.stem)
    ext = p.suffix.lower()
    return f"{int(time.time()*1000)}_{stem}{ext}"


@router.get("/api/images")
def list_images():
    """현재 input 폴더의 이미지 목록 반환 (최신순)"""
    from backend.session import session
    d = Path(WATCH_FOLDER)
    d.mkdir(parents=True, exist_ok=True)
    files = sorted(
        [f.name for f in d.iterdir() if f.suffix.lower() in IMAGE_EXTS],
        key=lambda n: (d / n).stat().st_mtime,
        reverse=True,
    )
    # 세션 동기화
    session.images = list(reversed(files))  # 오래된 것부터
    return {"images": files}


@router.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    if Path(file.filename).suffix.lower() not in IMAGE_EXTS:
        raise HTTPException(400, "이미지 파일만 업로드 가능합니다.")
    dest_dir = Path(WATCH_FOLDER)
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _sanitize(file.filename)
    (dest_dir / safe_name).write_bytes(await file.read())
    return {"filename": safe_name}


@router.get("/api/input/{filename}")
def serve_input(filename: str):
    path = Path(WATCH_FOLDER) / filename
    if not path.exists():
        raise HTTPException(404, "이미지를 찾을 수 없습니다.")
    return FileResponse(str(path))

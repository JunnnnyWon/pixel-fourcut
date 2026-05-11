from pathlib import Path
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import FileResponse
from backend.config import WATCH_FOLDER

router = APIRouter()


@router.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    dest_dir = Path(WATCH_FOLDER)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / file.filename
    dest.write_bytes(await file.read())
    return {"filename": file.filename}


@router.get("/api/input/{filename}")
def serve_input(filename: str):
    path = Path(WATCH_FOLDER) / filename
    return FileResponse(path)

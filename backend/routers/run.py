from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend import runner
from backend.session import session
from backend.watcher import manager

router = APIRouter()


class RunRequest(BaseModel):
    filename: str


class SelectRequest(BaseModel):
    filename: str


@router.get("/api/status")
def get_status():
    return session.to_dict()


@router.post("/api/select")
async def select_image(req: SelectRequest):
    session.selected = req.filename
    await manager.broadcast({"event": "selected", "filename": req.filename})
    return {"selected": req.filename}


@router.post("/api/run")
async def run_job(req: RunRequest):
    if session.status == "processing":
        raise HTTPException(409, "이미 처리 중입니다. 완료 후 다시 시도하세요.")
    try:
        prompt_id = await runner.enqueue(req.filename)
        return {"prompt_id": prompt_id}
    except FileNotFoundError:
        raise HTTPException(400, "활성화된 워크플로우 프리셋이 없습니다. 관리자 패널에서 프리셋을 활성화해주세요.")
    except Exception as e:
        raise HTTPException(500, f"처리 중 오류: {str(e)}")


@router.post("/api/reset")
async def reset_session():
    """새 손님 — 세션 초기화 + input 폴더 비우기"""
    import shutil
    from pathlib import Path
    from backend.config import WATCH_FOLDER
    folder = Path(WATCH_FOLDER)
    if folder.exists():
        shutil.rmtree(folder)
        folder.mkdir(parents=True)
    session.reset()
    await manager.broadcast({"event": "reset"})
    return {"ok": True}

import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend import runner
from backend.config import WATCH_FOLDER
from backend.session import session
from backend.watcher import manager

router = APIRouter()


class RunRequest(BaseModel):
    filename: str


class SelectRequest(BaseModel):
    filename: str


class SelectShotRequest(BaseModel):
    shot_id: str


def _clear_watch_folder():
    folder = Path(WATCH_FOLDER)
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True, exist_ok=True)


@router.get("/api/status")
def get_status():
    return session.to_dict()


@router.get("/api/session")
def get_session():
    return session.to_dict()


@router.post("/api/session/start")
async def start_session():
    _clear_watch_folder()
    snapshot = session.start_session()
    await manager.broadcast_session()
    return snapshot


@router.post("/api/session/finish-capture")
async def finish_capture():
    if not session.session_id:
        raise HTTPException(409, "진행 중인 세션이 없습니다.")
    snapshot = session.finish_capture()
    await manager.broadcast_session()
    return snapshot


@router.post("/api/session/select-shot")
async def select_shot(req: SelectShotRequest):
    if not session.session_id:
        raise HTTPException(409, "진행 중인 세션이 없습니다.")
    try:
        snapshot = session.select_shot(req.shot_id)
    except KeyError:
        raise HTTPException(404, "선택한 컷을 찾을 수 없습니다.")
    await manager.broadcast_session()
    return snapshot


@router.post("/api/session/run-selected")
async def run_selected():
    if session.phase == "processing":
        raise HTTPException(409, "이미 처리 중입니다. 완료 후 다시 시도하세요.")
    if not session.selected_shot_id:
        raise HTTPException(409, "선택된 컷이 없습니다.")
    try:
        prompt_id = await runner.enqueue_selected()
        await manager.broadcast_session()
        return {"prompt_id": prompt_id, "session": session.to_dict()}
    except FileNotFoundError:
        raise HTTPException(400, "활성화된 워크플로우 프리셋이 없습니다. 관리자 패널에서 프리셋을 활성화해주세요.")
    except Exception as exc:
        raise HTTPException(500, f"처리 중 오류: {str(exc)}")


@router.post("/api/session/complete")
async def complete_session():
    if not session.session_id:
        raise HTTPException(409, "진행 중인 세션이 없습니다.")
    snapshot = session.mark_completed()
    await manager.broadcast_session()
    return snapshot


@router.post("/api/session/reset")
async def reset_session():
    _clear_watch_folder()
    session.reset()
    await manager.broadcast_session()
    return {"ok": True, "session": session.to_dict()}


# Legacy compatibility endpoints
@router.post("/api/select")
async def select_image(req: SelectRequest):
    shot = next((item for item in session.shots if item["filename"] == req.filename), None)
    if not shot:
        raise HTTPException(404, "이미지를 찾을 수 없습니다.")
    snapshot = session.select_shot(shot["shot_id"])
    await manager.broadcast_session()
    return {"selected": snapshot.get("selected")}


@router.post("/api/run")
async def run_job(req: RunRequest):
    shot = next((item for item in session.shots if item["filename"] == req.filename), None)
    if not shot:
        raise HTTPException(404, "이미지를 찾을 수 없습니다.")
    session.select_shot(shot["shot_id"])
    return await run_selected()


@router.post("/api/reset")
async def reset_session_legacy():
    return await reset_session()

import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path as FilePath
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


class SessionActionRequest(BaseModel):
    session_id: Optional[str] = None


def _clear_watch_folder():
    folder = Path(WATCH_FOLDER)
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True, exist_ok=True)


def _get_active_capture_session_id() -> str:
    if not session.active_capture_session_id:
        raise HTTPException(409, "현재 촬영/선택 중인 세션이 없습니다.")
    return session.active_capture_session_id


@router.get("/api/status")
def get_status():
    return session.to_dict()


@router.get("/api/session")
def get_session():
    return session.to_dict()


@router.get("/api/sessions")
def list_sessions():
    return {"sessions": session.all_sessions}


@router.get("/api/sessions/{session_id}")
def get_session_detail(session_id: str):
    detail = session.get_session(session_id)
    if not detail:
        raise HTTPException(404, "세션을 찾을 수 없습니다.")
    return detail


@router.get("/api/sessions/{session_id}/results/{result_id}")
def get_session_result_detail(session_id: str, result_id: str):
    detail = session.get_session(session_id)
    if not detail:
        raise HTTPException(404, "세션을 찾을 수 없습니다.")
    result = next((item for item in detail.get("generated_results", []) if item["result_id"] == result_id), None)
    if not result:
        raise HTTPException(404, "결과 이미지를 찾을 수 없습니다.")
    path = FilePath(result["local_path"])
    if not path.exists():
        raise HTTPException(404, "결과 파일이 없습니다.")
    return FileResponse(str(path), media_type=result.get("media_type") or None)


@router.post("/api/session/start")
async def start_session():
    try:
        _clear_watch_folder()
        snapshot = session.start_session()
    except RuntimeError:
        raise HTTPException(409, "이미 촬영/선택 중인 세션이 있습니다.")
    await manager.broadcast_session()
    return snapshot


@router.post("/api/session/finish-capture")
async def finish_capture():
    try:
        session_id = _get_active_capture_session_id()
        snapshot = session.finish_capture(session_id=session_id)
    except RuntimeError as exc:
        if str(exc) == "empty_capture_session":
            raise HTTPException(409, "사진이 아직 없습니다. 다시 찍거나 팀을 파기하세요.")
        raise HTTPException(409, "진행 중인 촬영 세션이 없습니다.")
    await manager.broadcast_session()
    return snapshot


@router.post("/api/session/retry-capture")
async def retry_capture():
    try:
        session_id = _get_active_capture_session_id()
        snapshot = session.retry_capture(session_id=session_id)
    except RuntimeError:
        raise HTTPException(409, "다시 촬영할 세션이 없습니다.")
    await manager.broadcast_session()
    return snapshot


@router.post("/api/session/select-shot")
async def select_shot(req: SelectShotRequest):
    try:
        session_id = _get_active_capture_session_id()
        snapshot = session.select_shot(req.shot_id, session_id=session_id)
    except RuntimeError:
        raise HTTPException(409, "진행 중인 세션이 없습니다.")
    except KeyError:
        raise HTTPException(404, "선택한 컷을 찾을 수 없습니다.")
    await manager.broadcast_session()
    return snapshot


@router.post("/api/session/run-selected")
async def run_selected():
    session_id = _get_active_capture_session_id()
    target_session = session.get_session(session_id)
    if not target_session:
        raise HTTPException(404, "세션을 찾을 수 없습니다.")
    if target_session["phase"] != "reviewing":
        raise HTTPException(409, "선택 가능한 review 상태의 세션이 아닙니다.")
    if not target_session["selected_shot_id"]:
        raise HTTPException(409, "선택된 컷이 없습니다.")
    try:
        prompt_id = await runner.enqueue_selected(session_id=session_id)
        await manager.broadcast_session()
        return {"prompt_id": prompt_id, "session": session.to_dict()}
    except FileNotFoundError:
        raise HTTPException(400, "활성화된 워크플로우 프리셋이 없습니다. 관리자 패널에서 프리셋을 활성화해주세요.")
    except Exception as exc:
        raise HTTPException(500, f"처리 중 오류: {str(exc)}")


@router.post("/api/session/complete")
async def complete_session(req: SessionActionRequest):
    session_id = req.session_id
    if not session_id:
        ready = session.print_ready_sessions
        if not ready:
            raise HTTPException(409, "완료 처리할 result_ready 세션이 없습니다.")
        session_id = ready[0]["session_id"]
    try:
        snapshot = session.mark_completed(session_id=session_id)
    except KeyError:
        raise HTTPException(404, "세션을 찾을 수 없습니다.")
    await manager.broadcast_session()
    return snapshot


@router.post("/api/session/discard")
async def discard_session(req: SessionActionRequest):
    session_id = req.session_id or session.active_capture_session_id
    if not session_id:
        raise HTTPException(409, "파기할 세션이 없습니다.")
    try:
        result = session.discard_session(session_id)
    except KeyError:
        raise HTTPException(404, "세션을 찾을 수 없습니다.")
    await manager.broadcast_session()
    return result


@router.post("/api/session/rerun")
async def rerun_session(req: SessionActionRequest):
    session_id = req.session_id
    if not session_id:
        raise HTTPException(409, "다시 생성할 세션이 없습니다.")
    target_session = session.get_session(session_id)
    if not target_session:
        raise HTTPException(404, "세션을 찾을 수 없습니다.")
    if not target_session.get("selected_shot_id"):
        raise HTTPException(409, "선택된 컷이 없습니다.")
    if target_session["phase"] in {"queued", "processing"}:
        raise HTTPException(409, "이미 AI 처리 중인 세션입니다.")
    try:
        prompt_id = await runner.enqueue_selected(session_id=session_id)
        await manager.broadcast_session()
        return {"prompt_id": prompt_id, "session": session.to_dict()}
    except FileNotFoundError:
        raise HTTPException(400, "활성화된 워크플로우 프리셋이 없습니다.")
    except Exception as exc:
        raise HTTPException(500, f"재생성 중 오류: {str(exc)}")


@router.post("/api/session/reset")
async def reset_session():
    _clear_watch_folder()
    session.reset()
    await manager.broadcast_session()
    return {"ok": True, "session": session.to_dict()}


# Legacy compatibility endpoints
@router.post("/api/select")
async def select_image(req: SelectRequest):
    session_id = _get_active_capture_session_id()
    active_session = session.get_session(session_id)
    shot = next((item for item in active_session["shots"] if item["filename"] == req.filename), None) if active_session else None
    if not shot:
        raise HTTPException(404, "이미지를 찾을 수 없습니다.")
    snapshot = session.select_shot(shot["shot_id"], session_id=session_id)
    await manager.broadcast_session()
    return {"selected": snapshot.get("selected")}


@router.post("/api/run")
async def run_job(req: RunRequest):
    session_id = _get_active_capture_session_id()
    active_session = session.get_session(session_id)
    shot = next((item for item in active_session["shots"] if item["filename"] == req.filename), None) if active_session else None
    if not shot:
        raise HTTPException(404, "이미지를 찾을 수 없습니다.")
    session.select_shot(shot["shot_id"], session_id=session_id)
    return await run_selected()


@router.post("/api/reset")
async def reset_session_legacy():
    return await reset_session()

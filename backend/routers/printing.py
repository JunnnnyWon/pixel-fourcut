from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.print_service import compose_print as build_print_composite
from backend.print_service import get_frame_path, list_frames as get_frame_catalog
from backend.session import session
from backend.watcher import manager

router = APIRouter()


class SlotLayoutRequest(BaseModel):
    scale: float = 1.0
    offset_x: int = 0
    offset_y: int = 0


class ComposePrintLayoutRequest(BaseModel):
    original: SlotLayoutRequest = SlotLayoutRequest()
    ai: SlotLayoutRequest = SlotLayoutRequest()


class ComposePrintRequest(BaseModel):
    session_id: str
    frame_id: str
    result_id: Optional[str] = None
    layout: ComposePrintLayoutRequest = ComposePrintLayoutRequest()


@router.get("/api/frames")
def list_frames():
    return {"frames": get_frame_catalog()}


@router.get("/api/frames/{frame_id}")
def get_frame(frame_id: str):
    frame_path = get_frame_path(frame_id)
    if not frame_path or not frame_path.exists():
        raise HTTPException(404, "프레임을 찾을 수 없습니다.")
    return FileResponse(str(frame_path), media_type="image/png")


@router.get("/api/sessions/{session_id}/prints/{print_id}")
def get_session_print(session_id: str, print_id: str):
    print_output = session.get_print_output(session_id, print_id)
    if not print_output:
        raise HTTPException(404, "인화본을 찾을 수 없습니다.")
    path = Path(print_output["local_path"])
    if not path.exists():
        raise HTTPException(404, "인화본 파일이 없습니다.")
    return FileResponse(str(path), media_type=print_output.get("media_type") or None)


@router.post("/api/session/compose-print")
async def compose_print(req: ComposePrintRequest):
    target_session = session.get_session(req.session_id)
    if not target_session:
        raise HTTPException(404, "세션을 찾을 수 없습니다.")
    if not target_session.get("selected_shot"):
        raise HTTPException(409, "선택된 원본 컷이 없습니다.")
    if not target_session.get("generated_results"):
        raise HTTPException(409, "AI 결과가 없습니다.")

    frame_path = get_frame_path(req.frame_id)
    if not frame_path or not frame_path.exists():
        raise HTTPException(404, "선택한 프레임을 찾을 수 없습니다.")

    result_entry = None
    if req.result_id:
        result_entry = session.get_generated_result(req.session_id, req.result_id)
        if not result_entry:
            raise HTTPException(404, "선택한 AI 결과를 찾을 수 없습니다.")
    else:
        result_entry = target_session["generated_results"][-1]

    selected_shot_path = session.get_shot_path(target_session["selected_shot_id"], session_id=req.session_id)
    if not selected_shot_path or not selected_shot_path.exists():
        raise HTTPException(404, "선택된 원본 컷 파일이 없습니다.")

    result_path = Path(result_entry["local_path"])
    if not result_path.exists():
        raise HTTPException(404, "선택한 AI 결과 파일이 없습니다.")

    with TemporaryDirectory() as tmpdir:
        temp_output = Path(tmpdir) / "print-output.png"
        layout_payload = req.layout.model_dump() if hasattr(req.layout, "model_dump") else req.layout.dict()

        build_print_composite(
            original_path=selected_shot_path,
            ai_path=result_path,
            frame_path=frame_path,
            output_path=temp_output,
            layout=layout_payload,
        )
        print_output = session.cache_print_file(
            req.session_id,
            frame_id=req.frame_id,
            result_id=result_entry["result_id"],
            content=temp_output.read_bytes(),
            media_type="image/png",
            layout=layout_payload,
        )

    await manager.broadcast_session()
    return {
        "print_output": print_output,
        "session": session.to_dict(),
    }

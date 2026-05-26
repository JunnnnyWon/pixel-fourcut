import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pathlib import Path
from backend.config import COMFYUI_URL, get_comfyui_headers
from backend.comfy_client import download_output_image, get_output_image_info
from backend.session import session

router = APIRouter()


@router.get("/api/comfyui/status")
async def comfyui_status():
    try:
        async with httpx.AsyncClient(timeout=3, headers=get_comfyui_headers()) as client:
            r = await client.get(f"{COMFYUI_URL}/system_stats")
            return {"online": r.status_code == 200}
    except Exception:
        return {"online": False}


@router.get("/api/result/{prompt_id}")
async def result(prompt_id: str):
    result_session = session.get_session_by_prompt_id(prompt_id)
    local_path = result_session.get("result_local_path") if result_session else None
    local_type = result_session.get("result_media_type") if result_session else None
    if local_path and Path(local_path).exists():
        return FileResponse(str(local_path), media_type=local_type or None)

    image_info = await get_output_image_info(prompt_id)
    if not image_info:
        raise HTTPException(404, "결과 이미지가 아직 준비되지 않았습니다.")
    content, media_type = await download_output_image(image_info)
    return StreamingResponse(iter([content]), media_type=media_type)

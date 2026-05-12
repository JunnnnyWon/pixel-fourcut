import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from backend.config import COMFYUI_URL
from backend.comfy_client import get_output_image

router = APIRouter()


@router.get("/api/comfyui/status")
async def comfyui_status():
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{COMFYUI_URL}/system_stats")
            return {"online": r.status_code == 200}
    except Exception:
        return {"online": False}


@router.get("/api/result/{prompt_id}")
async def result(prompt_id: str):
    filename = await get_output_image(prompt_id)
    if not filename:
        raise HTTPException(404, "결과 이미지가 아직 준비되지 않았습니다.")
    url = f"{COMFYUI_URL}/view?filename={filename}&type=output"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        if r.status_code != 200:
            raise HTTPException(502, "ComfyUI에서 이미지를 가져오지 못했습니다.")
        return StreamingResponse(
            iter([r.content]),
            media_type=r.headers.get("content-type", "image/png"),
        )

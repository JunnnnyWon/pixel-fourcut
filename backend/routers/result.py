import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from backend.config import COMFYUI_URL
from backend.comfy_client import get_output_image

router = APIRouter()


@router.get("/api/result/{prompt_id}")
async def result(prompt_id: str):
    filename = await get_output_image(prompt_id)
    if not filename:
        raise HTTPException(404, "Output not ready")
    url = f"{COMFYUI_URL}/view?filename={filename}&type=output"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        if r.status_code != 200:
            raise HTTPException(502, "Failed to fetch from ComfyUI")
        return StreamingResponse(
            iter([r.content]),
            media_type=r.headers.get("content-type", "image/png"),
        )

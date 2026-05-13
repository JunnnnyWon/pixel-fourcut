import uuid
import httpx
from pathlib import Path
from typing import Optional
from backend.config import COMFYUI_URL, get_comfyui_headers


async def upload_image(filepath: str) -> str:
    """Upload image to ComfyUI, return filename as stored by ComfyUI."""
    path = Path(filepath)
    async with httpx.AsyncClient(headers=get_comfyui_headers()) as client:
        with open(path, "rb") as f:
            r = await client.post(
                f"{COMFYUI_URL}/upload/image",
                files={"image": (path.name, f, "image/jpeg")},
                data={"overwrite": "true"},
            )
        r.raise_for_status()
        return r.json()["name"]


def patch_workflow(workflow: dict, filename: str, seed_override: Optional[int] = None) -> dict:
    """Replace LoadImage node input and optionally override workflow seeds."""
    import copy
    wf = copy.deepcopy(workflow)
    for node in wf.values():
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs", {})
        if node.get("class_type") == "LoadImage":
            inputs["image"] = filename
        if seed_override is not None:
            for key in ("seed", "noise_seed"):
                if key in inputs:
                    inputs[key] = seed_override
    return wf


async def queue_prompt(workflow: dict, client_id: str = None) -> str:
    """Submit workflow to ComfyUI queue, return prompt_id."""
    import uuid
    if client_id is None:
        client_id = str(uuid.uuid4())
    async with httpx.AsyncClient(headers=get_comfyui_headers()) as client:
        r = await client.post(
            f"{COMFYUI_URL}/prompt",
            json={"prompt": workflow, "client_id": client_id},
        )
        r.raise_for_status()
        return r.json()["prompt_id"]


async def get_output_image_info(prompt_id: str) -> Optional[dict]:
    """Poll history and return the first output image metadata, or None."""
    async with httpx.AsyncClient(headers=get_comfyui_headers()) as client:
        r = await client.get(f"{COMFYUI_URL}/history/{prompt_id}")
        r.raise_for_status()
        data = r.json().get(prompt_id, {})
        for node_output in data.get("outputs", {}).values():
            images = node_output.get("images", [])
            if images:
                return images[0]
    return None


async def get_output_image(prompt_id: str) -> Optional[str]:
    """Poll history and return the first output image filename, or None."""
    image = await get_output_image_info(prompt_id)
    return image["filename"] if image else None


async def download_output_image(image_info: dict) -> tuple[bytes, str]:
    async with httpx.AsyncClient(headers=get_comfyui_headers()) as client:
        r = await client.get(
            f"{COMFYUI_URL}/view",
            params={
                "filename": image_info["filename"],
                "subfolder": image_info.get("subfolder", ""),
                "type": image_info.get("type", "output"),
            },
        )
        r.raise_for_status()
        return r.content, r.headers.get("content-type", "image/png")

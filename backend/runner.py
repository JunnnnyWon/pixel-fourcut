import asyncio
import json
from pathlib import Path
import httpx
import websockets
from backend.config import COMFYUI_URL, PRESETS_FOLDER
from backend import comfy_client
from backend.watcher import manager

_queue: asyncio.Queue = asyncio.Queue()


async def enqueue(filename: str) -> str:
    """Add a job to the processing queue, return prompt_id."""
    from backend.config import WATCH_FOLDER
    filepath = str(Path(WATCH_FOLDER) / filename)

    comfy_filename = await comfy_client.upload_image(filepath)

    active = Path(PRESETS_FOLDER) / "active.json"
    if not active.exists():
        raise FileNotFoundError("No active preset. Please activate a workflow preset first.")
    workflow = json.loads(active.read_text())
    patched = comfy_client.patch_workflow(workflow, comfy_filename)
    prompt_id = await comfy_client.queue_prompt(patched)
    await _queue.put(prompt_id)
    return prompt_id


async def run_worker():
    """Background worker: subscribe to ComfyUI WS and relay events."""
    ws_url = COMFYUI_URL.replace("http://", "ws://").replace("https://", "wss://")
    while True:
        prompt_id = await _queue.get()
        try:
            async with websockets.connect(f"{ws_url}/ws") as ws:
                async for raw in ws:
                    msg = json.loads(raw)
                    mtype = msg.get("type")
                    data = msg.get("data", {})

                    if mtype == "progress":
                        await manager.broadcast({
                            "event": "progress",
                            "value": data.get("value"),
                            "max": data.get("max"),
                        })
                    elif mtype == "executed" and data.get("prompt_id") == prompt_id:
                        output_filename = await comfy_client.get_output_image(prompt_id)
                        await manager.broadcast({
                            "event": "done",
                            "prompt_id": prompt_id,
                            "output_filename": output_filename,
                        })
                        break
                    elif mtype == "execution_error" and data.get("prompt_id") == prompt_id:
                        await manager.broadcast({
                            "event": "error",
                            "message": data.get("exception_message", "Unknown error"),
                        })
                        break
        except Exception as e:
            await manager.broadcast({"event": "error", "message": str(e)})
        finally:
            _queue.task_done()

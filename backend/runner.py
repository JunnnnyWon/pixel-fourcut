import asyncio
import json
from pathlib import Path
import websockets
from backend.config import COMFYUI_URL, PRESETS_FOLDER
from backend import comfy_client
from backend.watcher import manager

_queue: asyncio.Queue = asyncio.Queue()


async def enqueue(filename: str) -> str:
    from backend.config import WATCH_FOLDER
    from backend.session import session

    filepath = str(Path(WATCH_FOLDER) / filename)
    active = Path(PRESETS_FOLDER) / "active.json"
    if not active.exists():
        raise FileNotFoundError("active_preset_missing")

    comfy_filename = await comfy_client.upload_image(filepath)
    workflow = json.loads(active.read_text(encoding="utf-8"))
    patched = comfy_client.patch_workflow(workflow, comfy_filename)
    prompt_id = await comfy_client.queue_prompt(patched)

    session.status = "processing"
    session.prompt_id = prompt_id
    session.result_filename = None
    session.error = None
    await _queue.put(prompt_id)
    return prompt_id


async def run_worker():
    from backend.session import session
    ws_url = COMFYUI_URL.replace("http://", "ws://").replace("https://", "wss://")

    while True:
        prompt_id = await _queue.get()
        retries = 0
        success = False

        while retries < 5 and not success:
            try:
                async with websockets.connect(f"{ws_url}/ws", ping_interval=20) as ws:
                    async for raw in ws:
                        if isinstance(raw, bytes):
                            continue
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
                            session.status = "done"
                            session.result_filename = output_filename
                            await manager.broadcast({
                                "event": "done",
                                "prompt_id": prompt_id,
                                "output_filename": output_filename,
                            })
                            success = True
                            break

                        elif mtype == "execution_error" and data.get("prompt_id") == prompt_id:
                            err = data.get("exception_message", "Unknown error")
                            session.status = "error"
                            session.error = err
                            await manager.broadcast({"event": "error", "message": err})
                            success = True
                            break

            except Exception as e:
                retries += 1
                if retries >= 5:
                    session.status = "error"
                    session.error = f"ComfyUI 연결 실패: {e}"
                    await manager.broadcast({"event": "error", "message": session.error})
                else:
                    await asyncio.sleep(3)

        _queue.task_done()

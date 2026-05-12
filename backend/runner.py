import asyncio
import json
import uuid
from pathlib import Path

import websockets

from backend import comfy_client
from backend.config import COMFYUI_URL, PRESETS_FOLDER
from backend.session import session
from backend.watcher import manager

_queue: asyncio.Queue = asyncio.Queue()


async def enqueue_selected() -> str:
    if not session.selected_shot_id:
        raise RuntimeError("selected_shot_missing")

    shot_path = session.get_shot_path(session.selected_shot_id)
    if not shot_path or not Path(shot_path).exists():
        raise FileNotFoundError("selected_shot_not_found")

    active = Path(PRESETS_FOLDER) / "active.json"
    if not active.exists():
        raise FileNotFoundError("active_preset_missing")

    comfy_filename = await comfy_client.upload_image(str(shot_path))
    workflow = json.loads(active.read_text(encoding="utf-8"))
    patched = comfy_client.patch_workflow(workflow, comfy_filename)

    client_id = str(uuid.uuid4())
    prompt_id = await comfy_client.queue_prompt(patched, client_id)

    session.mark_processing(prompt_id)
    await _queue.put((prompt_id, client_id))
    return prompt_id


async def run_worker():
    ws_url = COMFYUI_URL.replace("http://", "ws://").replace("https://", "wss://")

    while True:
        prompt_id, client_id = await _queue.get()
        retries = 0
        success = False

        while retries < 5 and not success:
            try:
                async with websockets.connect(
                    f"{ws_url}/ws?clientId={client_id}", ping_interval=20
                ) as ws:
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
                                "session": session.to_dict(),
                            })

                        elif mtype == "executed" and data.get("prompt_id") == prompt_id:
                            output_filename = await comfy_client.get_output_image(prompt_id)
                            session.mark_result_ready(output_filename)
                            await manager.broadcast_session()
                            success = True
                            break

                        elif mtype == "execution_error" and data.get("prompt_id") == prompt_id:
                            err = data.get("exception_message", "Unknown error")
                            session.mark_error(err)
                            await manager.broadcast({
                                "event": "session_error",
                                "message": err,
                                "session": session.to_dict(),
                            })
                            success = True
                            break

            except Exception as exc:
                retries += 1
                if retries >= 5:
                    try:
                        output_filename = await comfy_client.get_output_image(prompt_id)
                        if output_filename:
                            session.mark_result_ready(output_filename)
                            await manager.broadcast_session()
                            success = True
                        else:
                            session.mark_error(f"ComfyUI 연결 실패: {exc}")
                            await manager.broadcast({
                                "event": "session_error",
                                "message": session.error,
                                "session": session.to_dict(),
                            })
                    except Exception:
                        session.mark_error(f"ComfyUI 연결 실패: {exc}")
                        await manager.broadcast({
                            "event": "session_error",
                            "message": session.error,
                            "session": session.to_dict(),
                        })
                else:
                    await asyncio.sleep(3)

        _queue.task_done()

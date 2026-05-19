import asyncio
import json
import random
import uuid
from pathlib import Path
from typing import Optional

import websockets

from backend import comfy_client
from backend.config import COMFYUI_URL, PRESETS_FOLDER, get_comfyui_headers
from backend.session import session
from backend.watcher import manager

_queue: asyncio.Queue = asyncio.Queue()
WS_IDLE_HISTORY_POLL_SECONDS = 5


async def _finalize_prompt_result(session_id: str, prompt_id: str, source_shot_id: Optional[str]) -> bool:
    output_image = await comfy_client.get_output_image_info(prompt_id)
    if not output_image:
        session.mark_error(session_id, "ComfyUI 결과 파일을 찾지 못했습니다.")
        await manager.broadcast_session()
        return False

    content, media_type = await comfy_client.download_output_image(output_image)
    session.cache_result_file(
        session_id,
        source_filename=output_image["filename"],
        content=content,
        media_type=media_type,
        source_shot_id=source_shot_id,
    )
    session.mark_result_ready(session_id, result_filename=output_image["filename"])
    await manager.broadcast_session()
    return True


async def enqueue_selected(session_id: str, randomize_seed: bool = False) -> str:
    target_session = session.get_session(session_id)
    if not target_session:
        raise RuntimeError("session_not_found")
    if not target_session.get("selected_shot_id"):
        raise RuntimeError("selected_shot_missing")

    shot_path = session.get_shot_path(target_session["selected_shot_id"], session_id=session_id)
    if not shot_path or not Path(shot_path).exists():
        raise FileNotFoundError("selected_shot_not_found")

    active = Path(PRESETS_FOLDER) / "active.json"
    if not active.exists():
        raise FileNotFoundError("active_preset_missing")

    source_shot_id = target_session["selected_shot_id"]
    comfy_filename = await comfy_client.upload_image(str(shot_path))
    workflow = json.loads(active.read_text(encoding="utf-8"))
    seed_override = random.randint(1, 2**31 - 1) if randomize_seed else None
    patched = comfy_client.patch_workflow(workflow, comfy_filename, seed_override=seed_override)

    client_id = str(uuid.uuid4())
    prompt_id = await comfy_client.queue_prompt(patched, client_id)

    session.mark_queued(prompt_id, session_id=session_id)
    await _queue.put((session_id, prompt_id, client_id, source_shot_id))
    return prompt_id


async def run_worker():
    ws_url = COMFYUI_URL.replace("http://", "ws://").replace("https://", "wss://")

    while True:
        session_id, prompt_id, client_id, source_shot_id = await _queue.get()
        session.start_processing_session(session_id)
        await manager.broadcast_session()

        retries = 0
        success = False

        while retries < 5 and not success:
            try:
                async with websockets.connect(
                    f"{ws_url}/ws?clientId={client_id}",
                    ping_interval=20,
                    additional_headers=get_comfyui_headers() or None,
                ) as ws:
                    while True:
                        try:
                            raw = await asyncio.wait_for(ws.recv(), timeout=WS_IDLE_HISTORY_POLL_SECONDS)
                        except asyncio.TimeoutError:
                            if await comfy_client.get_output_image_info(prompt_id):
                                success = await _finalize_prompt_result(session_id, prompt_id, source_shot_id)
                                break
                            continue

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
                            success = await _finalize_prompt_result(session_id, prompt_id, source_shot_id)
                            break

                        elif mtype == "execution_success" and data.get("prompt_id") == prompt_id:
                            success = await _finalize_prompt_result(session_id, prompt_id, source_shot_id)
                            break

                        elif mtype == "execution_error" and data.get("prompt_id") == prompt_id:
                            err = data.get("exception_message", "Unknown error")
                            session.mark_error(session_id, err)
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
                        if await _finalize_prompt_result(session_id, prompt_id, source_shot_id):
                            success = True
                        else:
                            session.mark_error(session_id, f"ComfyUI 연결 실패: {exc}")
                            await manager.broadcast({
                                "event": "session_error",
                                "message": session.get_session(session_id)["error"],
                                "session": session.to_dict(),
                            })
                    except Exception:
                        session.mark_error(session_id, f"ComfyUI 연결 실패: {exc}")
                        await manager.broadcast({
                            "event": "session_error",
                            "message": session.get_session(session_id)["error"],
                            "session": session.to_dict(),
                        })
                else:
                    await asyncio.sleep(3)

        _queue.task_done()

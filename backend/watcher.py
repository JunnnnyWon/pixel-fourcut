import asyncio
import json
from pathlib import Path

from fastapi import WebSocket

from backend.session import session

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
POLL_INTERVAL_SECONDS = 0.5


class ConnectionManager:
    def __init__(self):
        self._clients: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._clients.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self._clients:
            self._clients.remove(ws)

    async def broadcast(self, data: dict):
        msg = json.dumps(data, ensure_ascii=False)
        for ws in list(self._clients):
            try:
                await ws.send_text(msg)
            except Exception:
                if ws in self._clients:
                    self._clients.remove(ws)

    async def broadcast_session(self, event: str = "session_updated"):
        await self.broadcast({
            "event": event,
            "session": session.to_dict(),
        })


manager = ConnectionManager()


async def watch_folder(folder: str):
    folder_path = Path(folder)
    folder_path.mkdir(parents=True, exist_ok=True)

    while True:
        try:
            await _ingest_available_files(folder_path)
        except Exception as exc:
            if session.active_capture_session_id:
                session.mark_error(session.active_capture_session_id, f"이미지 수집 실패: {exc}")
                await manager.broadcast({
                    "event": "session_error",
                    "message": str(exc),
                    "session": session.to_dict(),
                })
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _ingest_available_files(folder_path: Path):
    if session.phase != "capturing" or not session.active_capture_session_id:
        return

    for path in sorted(folder_path.iterdir(), key=lambda item: item.stat().st_mtime):
        if path.suffix.lower() not in IMAGE_EXTS:
            continue
        if session.has_source_filename(path.name, session_id=session.active_capture_session_id):
            continue
        await _wait_until_file_stable(path)
        if not session.has_source_filename(path.name, session_id=session.active_capture_session_id):
            session.add_shot_from_file(path, source_name=path.name, source_type="watcher")
            await manager.broadcast_session()


async def _wait_until_file_stable(path: Path, retries: int = 8, delay: float = 0.2):
    previous_size = -1
    for _ in range(retries):
        if not path.exists():
            await asyncio.sleep(delay)
            continue
        current_size = path.stat().st_size
        if current_size > 0 and current_size == previous_size:
            return
        previous_size = current_size
        await asyncio.sleep(delay)

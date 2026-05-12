import json
from pathlib import Path

from fastapi import WebSocket
from watchfiles import Change, awatch

from backend.session import session

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


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

    async for changes in awatch(folder):
        for change_type, path in changes:
            p = Path(path)
            if p.suffix.lower() not in IMAGE_EXTS or change_type != Change.added:
                continue

            if session.phase != "capturing":
                if session.active_capture_session_id:
                    session.log_event(
                        "ignored_inbox_file",
                        f"{p.name} 무시됨 (phase={session.phase})",
                        session_id=session.active_capture_session_id,
                    )
                    await manager.broadcast_session()
                continue

            try:
                session.add_shot_from_file(p, source_name=p.name, source_type="watcher")
                await manager.broadcast_session()
            except Exception as exc:
                if session.active_capture_session_id:
                    session.mark_error(session.active_capture_session_id, f"이미지 수집 실패: {exc}")
                await manager.broadcast({
                    "event": "session_error",
                    "message": str(exc),
                    "session": session.to_dict(),
                })

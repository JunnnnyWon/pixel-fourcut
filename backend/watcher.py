import json
from pathlib import Path
from fastapi import WebSocket
from watchfiles import awatch, Change

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
                self._clients.discard(ws) if hasattr(self._clients, 'discard') else None
                if ws in self._clients:
                    self._clients.remove(ws)


manager = ConnectionManager()


async def watch_folder(folder: str):
    from backend.session import session
    Path(folder).mkdir(parents=True, exist_ok=True)
    async for changes in awatch(folder):
        for change_type, path in changes:
            p = Path(path)
            if p.suffix.lower() not in IMAGE_EXTS:
                continue
            filename = p.name
            if change_type == Change.added:
                if filename not in session.images:
                    session.images.append(filename)
                await manager.broadcast({
                    "event": "new_image",
                    "filename": filename,
                    "url": f"/api/input/{filename}",
                    "images": session.images,
                })
            elif change_type == Change.deleted:
                if filename in session.images:
                    session.images.remove(filename)
                if session.selected == filename:
                    session.selected = None
                await manager.broadcast({
                    "event": "image_removed",
                    "filename": filename,
                    "images": session.images,
                })

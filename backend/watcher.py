import asyncio
import json
from pathlib import Path
from fastapi import WebSocket
from watchfiles import awatch, Change


class ConnectionManager:
    def __init__(self):
        self._clients: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._clients.append(ws)

    def disconnect(self, ws: WebSocket):
        self._clients.remove(ws)

    async def broadcast(self, data: dict):
        msg = json.dumps(data)
        for ws in list(self._clients):
            try:
                await ws.send_text(msg)
            except Exception:
                self._clients.remove(ws)


manager = ConnectionManager()

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


async def watch_folder(folder: str):
    Path(folder).mkdir(parents=True, exist_ok=True)
    async for changes in awatch(folder):
        for change_type, path in changes:
            if change_type == Change.added and Path(path).suffix.lower() in IMAGE_EXTS:
                filename = Path(path).name
                await manager.broadcast({
                    "event": "new_image",
                    "filename": filename,
                    "url": f"/api/input/{filename}",
                })

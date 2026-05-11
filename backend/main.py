import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import WATCH_FOLDER
from backend.watcher import manager, watch_folder
from backend.runner import run_worker
from backend.routers import presets, upload, run, result


@asynccontextmanager
async def lifespan(app: FastAPI):
    t1 = asyncio.create_task(watch_folder(WATCH_FOLDER))
    t2 = asyncio.create_task(run_worker())
    yield
    t1.cancel()
    t2.cancel()


app = FastAPI(lifespan=lifespan)

# API routers
app.include_router(presets.router)
app.include_router(upload.router)
app.include_router(run.router)
app.include_router(result.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.websocket("/ws/watch")
async def ws_watch(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Serve React frontend (built to frontend/dist/)
_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/assets", StaticFiles(directory=str(_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        return FileResponse(str(_dist / "index.html"))

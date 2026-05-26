import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import PRESETS_FOLDER, SESSIONS_FOLDER, WATCH_FOLDER
from backend.watcher import manager, watch_folder
from backend.runner import run_worker
from backend.routers import presets, upload, run, result, printing


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(WATCH_FOLDER).mkdir(parents=True, exist_ok=True)
    Path(PRESETS_FOLDER).mkdir(parents=True, exist_ok=True)
    Path(SESSIONS_FOLDER).mkdir(parents=True, exist_ok=True)
    from backend.session import session
    session.load_from_disk()
    t1 = asyncio.create_task(watch_folder(WATCH_FOLDER))
    t2 = asyncio.create_task(run_worker())
    yield
    t1.cancel()
    t2.cancel()


app = FastAPI(lifespan=lifespan)

app.include_router(presets.router)
app.include_router(upload.router)
app.include_router(run.router)
app.include_router(result.router)
app.include_router(printing.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.websocket("/ws/watch")
async def ws_watch(websocket: WebSocket):
    from backend.session import session
    await manager.connect(websocket)
    # 연결 즉시 현재 상태 전송
    try:
        await websocket.send_text(__import__('json').dumps({
            "event": "session_init",
            "session": session.to_dict(),
        }, ensure_ascii=False))
    except Exception:
        pass
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/assets", StaticFiles(directory=str(_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        return FileResponse(str(_dist / "index.html"))

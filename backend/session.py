from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


class SessionState:
    def __init__(self, sessions_root: Optional[Path] = None):
        if sessions_root is None:
            from backend.config import SESSIONS_FOLDER

            sessions_root = Path(SESSIONS_FOLDER)
        self.sessions_root = Path(sessions_root)
        self.sessions_root.mkdir(parents=True, exist_ok=True)
        self.reset()

    def reset(self):
        self.session_id: Optional[str] = None
        self.phase: str = "idle"
        self.shots: list[dict] = []
        self.selected_shot_id: Optional[str] = None
        self.preview_shot_id: Optional[str] = None
        self.preview_until: Optional[str] = None
        self.prompt_id: Optional[str] = None
        self.result_filename: Optional[str] = None
        self.error: Optional[str] = None
        self.logs: list[dict] = []
        self.created_at: Optional[str] = None
        self.updated_at: Optional[str] = None
        self._session_dir: Optional[Path] = None

    @property
    def session_dir(self) -> Optional[Path]:
        return self._session_dir

    @property
    def selected_shot(self) -> Optional[dict]:
        if not self.selected_shot_id:
            return None
        return next((shot for shot in self.shots if shot["shot_id"] == self.selected_shot_id), None)

    @property
    def preview_shot(self) -> Optional[dict]:
        if not self.preview_shot_id:
            return None
        return next((shot for shot in self.shots if shot["shot_id"] == self.preview_shot_id), None)

    @property
    def selected(self) -> Optional[str]:
        shot = self.selected_shot
        return shot["filename"] if shot else None

    @property
    def images(self) -> list[str]:
        return [shot["filename"] for shot in self.shots]

    @property
    def status(self) -> str:
        mapping = {
            "idle": "idle",
            "capturing": "idle",
            "reviewing": "idle",
            "processing": "processing",
            "result_ready": "done",
            "completed": "done",
            "error": "error",
        }
        return mapping.get(self.phase, "idle")

    def start_session(self, session_id: Optional[str] = None):
        self.reset()
        if not session_id:
            session_id = f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.session_id = session_id
        self.phase = "capturing"
        self.created_at = self._now()
        self.updated_at = self.created_at
        self._session_dir = self.sessions_root / session_id
        (self._session_dir / "shots").mkdir(parents=True, exist_ok=True)
        self._log("session_started", f"세션 {session_id} 시작")
        self._write_meta()
        return self.to_dict()

    def finish_capture(self):
        if self.phase == "capturing":
            self.phase = "reviewing"
            self._touch()
            self._log("capture_finished", "촬영 종료")
            self._write_meta()
        return self.to_dict()

    def add_shot_from_file(self, source_path: Path, source_name: Optional[str] = None, source_type: str = "watcher"):
        if self.phase != "capturing" or not self._session_dir:
            raise RuntimeError("session_not_capturing")

        source_path = Path(source_path)
        original_name = source_name or source_path.name
        ext = Path(original_name).suffix.lower() or source_path.suffix.lower() or ".jpg"
        shot_index = len(self.shots) + 1
        shot_id = f"shot-{shot_index:03d}"
        dest_name = f"{shot_id}{ext}"
        dest_path = self._session_dir / "shots" / dest_name
        shutil.copy2(source_path, dest_path)

        shot = {
            "shot_id": shot_id,
            "filename": dest_name,
            "source_filename": original_name,
            "source": source_type,
            "captured_at": self._now(),
            "path": str(dest_path),
            "url": f"/api/session/shots/{shot_id}",
        }
        self.shots.append(shot)
        self.preview_shot_id = shot_id
        self.preview_until = self._preview_deadline()
        self._touch()
        self._log("shot_added", f"{dest_name} 추가")
        self._write_meta()
        return shot

    def select_shot(self, shot_id: str):
        shot = next((item for item in self.shots if item["shot_id"] == shot_id), None)
        if not shot:
            raise KeyError("shot_not_found")
        self.selected_shot_id = shot_id
        self._touch()
        self._log("shot_selected", f"{shot['filename']} 선택")
        self._write_meta()
        return self.to_dict()

    def mark_processing(self, prompt_id: str):
        self.phase = "processing"
        self.prompt_id = prompt_id
        self.result_filename = None
        self.error = None
        self._touch()
        self._log("processing_started", "AI 처리 시작")
        self._write_meta()
        return self.to_dict()

    def mark_result_ready(self, result_filename: str):
        self.phase = "result_ready"
        self.result_filename = result_filename
        self.error = None
        self._touch()
        self._log("result_ready", f"결과 준비 완료: {result_filename}")
        self._write_meta()
        return self.to_dict()

    def mark_completed(self):
        self.phase = "completed"
        self._touch()
        self._log("session_completed", "세션 완료")
        self._write_meta()
        return self.to_dict()

    def mark_error(self, message: str):
        self.phase = "error"
        self.error = message
        self._touch()
        self._log("error", message)
        self._write_meta()
        return self.to_dict()

    def log_event(self, event: str, message: str):
        self._touch()
        self._log(event, message)
        self._write_meta()
        return self.to_dict()

    def get_shot(self, shot_id: str) -> Optional[dict]:
        return next((shot for shot in self.shots if shot["shot_id"] == shot_id), None)

    def get_shot_path(self, shot_id: str) -> Optional[Path]:
        shot = self.get_shot(shot_id)
        return Path(shot["path"]) if shot else None

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "phase": self.phase,
            "shots": self.shots,
            "selected_shot_id": self.selected_shot_id,
            "selected_shot": self.selected_shot,
            "preview_shot_id": self.preview_shot_id,
            "preview_shot": self.preview_shot,
            "preview_until": self.preview_until,
            "prompt_id": self.prompt_id,
            "result_filename": self.result_filename,
            "result_url": f"/api/result/{self.prompt_id}" if self.prompt_id and self.result_filename else None,
            "error": self.error,
            "logs": self.logs,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            # compatibility for the current frontend/backend contract
            "images": self.images,
            "selected": self.selected,
            "status": self.status,
        }

    def _log(self, event: str, message: str):
        self.logs.append({
            "event": event,
            "message": message,
            "at": self._now(),
        })

    def _touch(self):
        self.updated_at = self._now()

    @staticmethod
    def _preview_deadline() -> str:
        return (datetime.now() + timedelta(seconds=3)).isoformat(timespec="seconds")

    def _write_meta(self):
        if not self._session_dir:
            return
        self._session_dir.mkdir(parents=True, exist_ok=True)
        (self._session_dir / "meta.json").write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")


session = SessionState()

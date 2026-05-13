from __future__ import annotations

import json
import mimetypes
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
        self.active_capture_session_id: Optional[str] = None
        self._sessions: dict[str, dict] = {}
        self.updated_at: Optional[str] = None

    def load_from_disk(self):
        self.reset()
        if not self.sessions_root.exists():
            return self.to_dict()

        for meta_path in sorted(self.sessions_root.glob("*/meta.json")):
            session_data = json.loads(meta_path.read_text(encoding="utf-8"))
            raw_session = {
                "session_id": session_data["session_id"],
                "phase": session_data["phase"],
                "shots": session_data.get("shots", []),
                "selected_shot_id": session_data.get("selected_shot_id"),
                "preview_shot_id": session_data.get("preview_shot_id"),
                "preview_until": session_data.get("preview_until"),
                "prompt_id": session_data.get("prompt_id"),
                "result_filename": session_data.get("result_filename"),
                "result_local_path": session_data.get("result_local_path"),
                "result_media_type": session_data.get("result_media_type"),
                "error": session_data.get("error"),
                "logs": session_data.get("logs", []),
                "created_at": session_data.get("created_at"),
                "updated_at": session_data.get("updated_at"),
            }
            self._sessions[raw_session["session_id"]] = raw_session
            if raw_session["phase"] in {"capturing", "reviewing"}:
                self.active_capture_session_id = raw_session["session_id"]

        latest = self._get_latest_session()
        if latest:
            self.updated_at = latest["updated_at"]
        return self.to_dict()

    @property
    def current_session(self) -> Optional[dict]:
        if not self.active_capture_session_id:
            return None
        session = self._sessions.get(self.active_capture_session_id)
        return self._serialize_session(session) if session else None

    @property
    def processing_sessions(self) -> list[dict]:
        return self._serialize_sessions(("queued", "processing"))

    @property
    def print_ready_sessions(self) -> list[dict]:
        return self._serialize_sessions(("result_ready",))

    @property
    def completed_sessions(self) -> list[dict]:
        return self._serialize_sessions(("completed",))

    @property
    def errored_sessions(self) -> list[dict]:
        return self._serialize_sessions(("error",))

    @property
    def all_sessions(self) -> list[dict]:
        return self._serialize_sessions()

    @property
    def session_id(self) -> Optional[str]:
        return self.current_session["session_id"] if self.current_session else None

    @property
    def phase(self) -> str:
        return self.current_session["phase"] if self.current_session else "idle"

    @property
    def shots(self) -> list[dict]:
        return self.current_session["shots"] if self.current_session else []

    @property
    def selected_shot_id(self) -> Optional[str]:
        return self.current_session["selected_shot_id"] if self.current_session else None

    @property
    def preview_shot_id(self) -> Optional[str]:
        return self.current_session["preview_shot_id"] if self.current_session else None

    @property
    def preview_shot(self) -> Optional[dict]:
        return self.current_session["preview_shot"] if self.current_session else None

    @property
    def preview_until(self) -> Optional[str]:
        return self.current_session["preview_until"] if self.current_session else None

    @property
    def selected_shot(self) -> Optional[dict]:
        return self.current_session["selected_shot"] if self.current_session else None

    @property
    def prompt_id(self) -> Optional[str]:
        return self.current_session["prompt_id"] if self.current_session else None

    @property
    def result_filename(self) -> Optional[str]:
        return self.current_session["result_filename"] if self.current_session else None

    @property
    def error(self) -> Optional[str]:
        return self.current_session["error"] if self.current_session else None

    @property
    def logs(self) -> list[dict]:
        return self.current_session["logs"] if self.current_session else []

    @property
    def selected(self) -> Optional[str]:
        shot = self.selected_shot
        return shot["filename"] if shot else None

    @property
    def images(self) -> list[str]:
        return [shot["filename"] for shot in self.shots]

    @property
    def status(self) -> str:
        if self.current_session:
            phase = self.current_session["phase"]
            if phase in {"capturing", "reviewing", "idle"}:
                return "idle"
            if phase in {"queued", "processing"}:
                return "processing"
            if phase in {"result_ready", "completed"}:
                return "done"
            if phase == "error":
                return "error"
        if self.processing_sessions:
            return "processing"
        if self.print_ready_sessions or self.completed_sessions:
            return "done"
        if self.errored_sessions:
            return "error"
        return "idle"

    def start_session(self, session_id: Optional[str] = None):
        if self.active_capture_session_id:
            raise RuntimeError("capture_session_already_active")
        if not session_id:
            session_id = f"session-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"
        while session_id in self._sessions:
            session_id = f"{session_id}-next"

        session = self._new_session(session_id)
        self._sessions[session_id] = session
        self.active_capture_session_id = session_id
        self._log(session, "session_started", f"세션 {session_id} 시작")
        self._touch(session)
        self._write_meta(session)
        return self.to_dict()

    def finish_capture(self, session_id: Optional[str] = None):
        session = self._get_session_for_capture(session_id)
        if session["phase"] == "capturing":
            session["phase"] = "reviewing"
            self._log(session, "capture_finished", "촬영 종료")
            self._touch(session)
            self._write_meta(session)
        return self.to_dict()

    def add_shot_from_file(
        self,
        source_path: Path,
        source_name: Optional[str] = None,
        source_type: str = "watcher",
        session_id: Optional[str] = None,
    ):
        session = self._get_session_for_capture(session_id)
        if session["phase"] != "capturing":
            raise RuntimeError("session_not_capturing")

        source_path = Path(source_path)
        original_name = source_name or source_path.name
        ext = Path(original_name).suffix.lower() or source_path.suffix.lower() or ".jpg"
        shot_index = len(session["shots"]) + 1
        shot_id = f"shot-{shot_index:03d}"
        dest_name = f"{shot_id}{ext}"
        dest_path = self._session_dir(session) / "shots" / dest_name
        shutil.copy2(source_path, dest_path)

        shot = {
            "shot_id": shot_id,
            "filename": dest_name,
            "source_filename": original_name,
            "source": source_type,
            "captured_at": self._now(),
            "path": str(dest_path),
            "url": f"/api/session/shots/{session['session_id']}/{shot_id}",
        }
        session["shots"].append(shot)
        session["preview_shot_id"] = shot_id
        session["preview_until"] = self._preview_deadline()
        self._log(session, "shot_added", f"{dest_name} 추가")
        self._touch(session)
        self._write_meta(session)
        return shot

    def select_shot(self, shot_id: str, session_id: Optional[str] = None):
        session = self._get_session_for_capture(session_id)
        shot = self._get_shot(session, shot_id)
        if not shot:
            raise KeyError("shot_not_found")
        session["selected_shot_id"] = shot_id
        self._log(session, "shot_selected", f"{shot['filename']} 선택")
        self._touch(session)
        self._write_meta(session)
        return self.to_dict()

    def mark_queued(self, prompt_id: str, session_id: Optional[str] = None):
        session = self._get_session_for_capture(session_id)
        session["phase"] = "queued"
        session["prompt_id"] = prompt_id
        session["result_filename"] = None
        session["error"] = None
        self._log(session, "processing_queued", "AI 처리 대기열 추가")
        self._touch(session)
        self._write_meta(session)
        if self.active_capture_session_id == session["session_id"]:
            self.active_capture_session_id = None
        return self.to_dict()

    def start_processing_session(self, session_id: str):
        session = self._get_session(session_id)
        session["phase"] = "processing"
        self._log(session, "processing_started", "AI 처리 시작")
        self._touch(session)
        self._write_meta(session)
        return self.to_dict()

    def mark_processing(self, prompt_id: str, session_id: Optional[str] = None):
        session = self._get_session_for_capture(session_id)
        session_id = session["session_id"]
        self.mark_queued(prompt_id, session_id=session_id)
        return self.start_processing_session(session_id)

    def mark_result_ready(self, session_id: Optional[str] = None, result_filename: str = ""):
        if session_id is None:
            session_id = self.active_capture_session_id
            if not session_id:
                processing = self.processing_sessions
                if not processing:
                    raise RuntimeError("processing_session_missing")
                session_id = processing[0]["session_id"]
        session = self._get_session(session_id)
        session["phase"] = "result_ready"
        session["result_filename"] = result_filename
        session["error"] = None
        self._log(session, "result_ready", f"결과 준비 완료: {result_filename}")
        self._touch(session)
        self._write_meta(session)
        return self.to_dict()

    def cache_result_file(self, session_id: str, source_filename: str, content: bytes, media_type: str) -> str:
        session = self._get_session(session_id)
        suffix = Path(source_filename).suffix
        if not suffix:
            suffix = mimetypes.guess_extension(media_type or "") or ".png"
        local_name = f"result{suffix}"
        local_path = self._session_dir(session) / local_name
        local_path.write_bytes(content)
        session["result_filename"] = source_filename
        session["result_local_path"] = str(local_path)
        session["result_media_type"] = media_type
        self._touch(session)
        self._write_meta(session)
        return str(local_path)

    def mark_completed(self, session_id: Optional[str] = None):
        if session_id is None:
            ready = self.print_ready_sessions
            if not ready:
                raise RuntimeError("print_ready_session_missing")
            session_id = ready[0]["session_id"]
        session = self._get_session(session_id)
        session["phase"] = "completed"
        self._log(session, "session_completed", "세션 완료")
        self._touch(session)
        self._write_meta(session)
        return self.to_dict()

    def mark_error(self, session_id: Optional[str] = None, message: str = ""):
        if session_id is None:
            session_id = self.active_capture_session_id
            if not session_id:
                processing = self.processing_sessions
                if not processing:
                    raise RuntimeError("session_missing")
                session_id = processing[0]["session_id"]
        session = self._get_session(session_id)
        session["phase"] = "error"
        session["error"] = message
        self._log(session, "error", message)
        self._touch(session)
        self._write_meta(session)
        return self.to_dict()

    def log_event(self, event: str, message: str, session_id: Optional[str] = None):
        session = self._get_session(session_id) if session_id else self._get_latest_session()
        if not session:
            return self.to_dict()
        self._log(session, event, message)
        self._touch(session)
        self._write_meta(session)
        return self.to_dict()

    def get_session(self, session_id: str) -> Optional[dict]:
        session = self._sessions.get(session_id)
        return self._serialize_session(session) if session else None

    def get_shot(self, shot_id: str, session_id: Optional[str] = None) -> Optional[dict]:
        session = self._get_session(session_id) if session_id else self._get_session_for_lookup(shot_id)
        if not session:
            return None
        return self._get_shot(session, shot_id)

    def has_source_filename(self, source_filename: str, session_id: Optional[str] = None) -> bool:
        if session_id:
            session = self._get_session(session_id)
        elif self.active_capture_session_id:
            session = self._get_session(self.active_capture_session_id)
        else:
            return False
        if not session:
            return False
        return any(shot["source_filename"] == source_filename for shot in session["shots"])

    def get_shot_path(self, shot_id: str, session_id: Optional[str] = None) -> Optional[Path]:
        shot = self.get_shot(shot_id, session_id=session_id)
        return Path(shot["path"]) if shot else None

    def get_session_by_prompt_id(self, prompt_id: str) -> Optional[dict]:
        for item in self._sessions.values():
            if item["prompt_id"] == prompt_id:
                return self._serialize_session(item)
        return None

    def to_dict(self):
        current_session = self.current_session
        return {
            "active_capture_session_id": self.active_capture_session_id,
            "current_session": current_session,
            "processing_sessions": self.processing_sessions,
            "print_ready_sessions": self.print_ready_sessions,
            "completed_sessions": self.completed_sessions,
            "errored_sessions": self.errored_sessions,
            "all_sessions": self.all_sessions,
            # compatibility for earlier frontend/backend contract
            "session_id": current_session["session_id"] if current_session else None,
            "phase": current_session["phase"] if current_session else "idle",
            "shots": current_session["shots"] if current_session else [],
            "selected_shot_id": current_session["selected_shot_id"] if current_session else None,
            "selected_shot": current_session["selected_shot"] if current_session else None,
            "preview_shot_id": current_session["preview_shot_id"] if current_session else None,
            "preview_shot": current_session["preview_shot"] if current_session else None,
            "preview_until": current_session["preview_until"] if current_session else None,
            "prompt_id": current_session["prompt_id"] if current_session else None,
            "result_filename": current_session["result_filename"] if current_session else None,
            "result_url": current_session["result_url"] if current_session else None,
            "result_local_path": current_session["result_local_path"] if current_session else None,
            "result_media_type": current_session["result_media_type"] if current_session else None,
            "error": current_session["error"] if current_session else None,
            "logs": current_session["logs"] if current_session else [],
            "created_at": current_session["created_at"] if current_session else None,
            "updated_at": current_session["updated_at"] if current_session else self.updated_at,
            "images": [shot["filename"] for shot in current_session["shots"]] if current_session else [],
            "selected": current_session["selected_shot"]["filename"] if current_session and current_session["selected_shot"] else None,
            "status": self.status,
        }

    def _new_session(self, session_id: str) -> dict:
        created_at = self._now()
        session = {
            "session_id": session_id,
            "phase": "capturing",
            "shots": [],
            "selected_shot_id": None,
            "preview_shot_id": None,
            "preview_until": None,
            "prompt_id": None,
            "result_filename": None,
            "result_local_path": None,
            "result_media_type": None,
            "error": None,
            "logs": [],
            "created_at": created_at,
            "updated_at": created_at,
        }
        (self._session_dir(session) / "shots").mkdir(parents=True, exist_ok=True)
        return session

    def _get_session(self, session_id: str) -> dict:
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError("session_not_found")
        return session

    def _get_latest_session(self) -> Optional[dict]:
        if not self._sessions:
            return None
        return sorted(self._sessions.values(), key=lambda item: item["created_at"])[-1]

    def _get_session_for_capture(self, session_id: Optional[str]) -> dict:
        target_id = session_id or self.active_capture_session_id
        if not target_id:
            raise RuntimeError("capture_session_missing")
        return self._get_session(target_id)

    def _get_session_for_lookup(self, shot_id: str) -> Optional[dict]:
        for session in self._sessions.values():
            if self._get_shot(session, shot_id):
                return session
        return None

    def _get_shot(self, session: dict, shot_id: str) -> Optional[dict]:
        return next((shot for shot in session["shots"] if shot["shot_id"] == shot_id), None)

    def _serialize_sessions(self, phases: Optional[tuple[str, ...]] = None) -> list[dict]:
        items = []
        for session in self._sessions.values():
            if phases and session["phase"] not in phases:
                continue
            items.append(self._serialize_session(session))
        return sorted(items, key=lambda item: item["created_at"], reverse=True)

    def _serialize_session(self, session: Optional[dict]) -> Optional[dict]:
        if not session:
            return None
        selected_shot = self._get_shot(session, session["selected_shot_id"]) if session["selected_shot_id"] else None
        preview_shot = self._get_shot(session, session["preview_shot_id"]) if session["preview_shot_id"] else None
        return {
            "session_id": session["session_id"],
            "phase": session["phase"],
            "shots": list(session["shots"]),
            "selected_shot_id": session["selected_shot_id"],
            "selected_shot": selected_shot,
            "preview_shot_id": session["preview_shot_id"],
            "preview_shot": preview_shot,
            "preview_until": session["preview_until"],
            "prompt_id": session["prompt_id"],
            "result_filename": session["result_filename"],
            "result_url": f"/api/result/{session['prompt_id']}" if session["prompt_id"] and session["result_filename"] else None,
            "result_local_path": session["result_local_path"],
            "result_media_type": session["result_media_type"],
            "error": session["error"],
            "logs": list(session["logs"]),
            "created_at": session["created_at"],
            "updated_at": session["updated_at"],
        }

    def _session_dir(self, session: dict) -> Path:
        return self.sessions_root / session["session_id"]

    def _write_meta(self, session: dict):
        session_dir = self._session_dir(session)
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "meta.json").write_text(
            json.dumps(self._serialize_session(session), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _log(self, session: dict, event: str, message: str):
        session["logs"].append({
            "event": event,
            "message": message,
            "at": self._now(),
        })

    def _touch(self, session: dict):
        session["updated_at"] = self._now()
        self.updated_at = session["updated_at"]

    @staticmethod
    def _preview_deadline() -> str:
        return (datetime.now() + timedelta(seconds=3)).isoformat(timespec="seconds")

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")


session = SessionState()

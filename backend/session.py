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

        active_candidates: list[dict] = []
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
                "generated_results": session_data.get("generated_results", []),
                "selected_frame_id": session_data.get("selected_frame_id"),
                "selected_generated_result_id": session_data.get("selected_generated_result_id"),
                "print_outputs": session_data.get("print_outputs", []),
                "printer_jobs": session_data.get("printer_jobs", []),
                "error": session_data.get("error"),
                "logs": session_data.get("logs", []),
                "created_at": session_data.get("created_at"),
                "updated_at": session_data.get("updated_at"),
                "_meta_mtime_ns": meta_path.stat().st_mtime_ns,
            }
            self._sessions[raw_session["session_id"]] = raw_session
            if raw_session["phase"] in {"capturing", "reviewing"}:
                active_candidates.append(raw_session)

        if active_candidates:
            latest_active = sorted(
                active_candidates,
                key=lambda item: (
                    item.get("updated_at") or "",
                    item.get("created_at") or "",
                    item.get("_meta_mtime_ns") or 0,
                    item["session_id"],
                ),
            )[-1]
            self.active_capture_session_id = latest_active["session_id"]

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
            session_id = self._generate_session_id()
        while session_id in self._sessions:
            session_id = self._next_session_id(session_id)

        session = self._new_session(session_id)
        self._sessions[session_id] = session
        self.active_capture_session_id = session_id
        self._log(session, "session_started", f"세션 {session_id} 시작")
        self._touch(session)
        self._write_meta(session)
        return self.to_dict()

    def finish_capture(self, session_id: Optional[str] = None):
        session = self._get_session_for_capture(session_id)
        if not session["shots"]:
            raise RuntimeError("empty_capture_session")
        if session["phase"] == "capturing":
            session["phase"] = "reviewing"
            self._log(session, "capture_finished", "촬영 종료")
            self._touch(session)
            self._write_meta(session)
        return self.to_dict()

    def retry_capture(self, session_id: Optional[str] = None):
        session = self._get_session_for_capture(session_id)
        session["phase"] = "capturing"
        session["selected_shot_id"] = None
        self.active_capture_session_id = session["session_id"]
        self._log(session, "capture_retried", "다시 촬영 단계로 돌아감")
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

    def cache_result_file(
        self,
        session_id: str,
        source_filename: str,
        content: bytes,
        media_type: str,
        source_shot_id: Optional[str] = None,
    ) -> str:
        session = self._get_session(session_id)
        source_shot = self._get_shot(session, source_shot_id) if source_shot_id else None
        suffix = Path(source_filename).suffix
        if not suffix:
            suffix = mimetypes.guess_extension(media_type or "") or ".png"
        result_index = len(session["generated_results"]) + 1
        local_name = f"result-{result_index:03d}{suffix}"
        local_path = self._session_dir(session) / local_name
        local_path.write_bytes(content)
        session["result_filename"] = source_filename
        session["result_local_path"] = str(local_path)
        session["result_media_type"] = media_type
        result_id = f"result-{result_index:03d}"
        session["selected_generated_result_id"] = result_id
        session["generated_results"].append({
            "result_id": result_id,
            "filename": local_name,
            "source_filename": source_filename,
            "source_shot_id": source_shot_id,
            "source_shot_filename": source_shot["source_filename"] if source_shot else None,
            "local_path": str(local_path),
            "media_type": media_type,
            "url": f"/api/sessions/{session_id}/results/result-{result_index:03d}",
            "created_at": self._now(),
        })
        self._touch(session)
        self._write_meta(session)
        return str(local_path)

    def cache_print_file(
        self,
        session_id: str,
        frame_id: str,
        result_id: str,
        content: bytes,
        media_type: str,
        layout: Optional[dict] = None,
    ) -> dict:
        session = self._get_session(session_id)
        suffix = mimetypes.guess_extension(media_type or "") or ".png"
        print_index = len(session["print_outputs"]) + 1
        local_name = f"print-{print_index:03d}{suffix}"
        prints_dir = self._session_dir(session) / "prints"
        prints_dir.mkdir(parents=True, exist_ok=True)
        local_path = prints_dir / local_name
        local_path.write_bytes(content)
        print_output = {
            "print_id": f"print-{print_index:03d}",
            "filename": local_name,
            "frame_id": frame_id,
            "result_id": result_id,
            "layout": layout or {},
            "local_path": str(local_path),
            "media_type": media_type,
            "url": f"/api/sessions/{session_id}/prints/print-{print_index:03d}",
            "created_at": self._now(),
        }
        session["selected_frame_id"] = frame_id
        session["selected_generated_result_id"] = result_id
        session["print_outputs"].append(print_output)
        self._log(session, "print_composed", f"{local_name} 생성")
        self._touch(session)
        self._write_meta(session)
        return print_output

    def record_printer_job(
        self,
        session_id: str,
        print_id: str,
        printer_name: str,
        copies: int = 1,
        status: str = "sent",
        windows_job_id: Optional[int] = None,
        job_status: Optional[str] = None,
        document_name: Optional[str] = None,
        submitted_time: Optional[str] = None,
        paper_name: Optional[str] = None,
        paper_width: Optional[int] = None,
        paper_height: Optional[int] = None,
    ) -> dict:
        session = self._get_session(session_id)
        print_output = self.get_print_output(session_id, print_id)
        if not print_output:
            raise KeyError("print_output_not_found")

        printer_job = {
            "printer_job_id": f"printer-job-{len(session.get('printer_jobs', [])) + 1:03d}",
            "print_id": print_id,
            "printer_name": printer_name,
            "copies": max(1, int(copies)),
            "status": status,
            "windows_job_id": windows_job_id,
            "job_status": job_status,
            "document_name": document_name,
            "submitted_time": submitted_time,
            "paper_name": paper_name,
            "paper_width": paper_width,
            "paper_height": paper_height,
            "created_at": self._now(),
        }
        session["printer_jobs"].append(printer_job)
        print_output["last_printer_name"] = printer_name
        print_output["last_printed_at"] = printer_job["created_at"]
        print_output["copies"] = printer_job["copies"]
        print_output["status"] = status
        print_output["windows_job_id"] = windows_job_id
        print_output["job_status"] = job_status
        print_output["document_name"] = document_name
        print_output["submitted_time"] = submitted_time
        print_output["paper_name"] = paper_name
        print_output["paper_width"] = paper_width
        print_output["paper_height"] = paper_height
        self._log(session, "printer_job_sent", f"{print_id} -> {printer_name} ({copies}장)")
        self._touch(session)
        self._write_meta(session)
        return printer_job

    def update_printer_job(
        self,
        session_id: str,
        printer_job_id: str,
        *,
        status: Optional[str] = None,
        job_status: Optional[str] = None,
        document_name: Optional[str] = None,
        submitted_time: Optional[str] = None,
        paper_name: Optional[str] = None,
        paper_width: Optional[int] = None,
        paper_height: Optional[int] = None,
    ) -> dict:
        session = self._get_session(session_id)
        printer_job = next((job for job in session.get("printer_jobs", []) if job["printer_job_id"] == printer_job_id), None)
        if not printer_job:
            raise KeyError("printer_job_not_found")

        if status is not None:
            printer_job["status"] = status
        if job_status is not None:
            printer_job["job_status"] = job_status
        if document_name is not None:
            printer_job["document_name"] = document_name
        if submitted_time is not None:
            printer_job["submitted_time"] = submitted_time
        if paper_name is not None:
            printer_job["paper_name"] = paper_name
        if paper_width is not None:
            printer_job["paper_width"] = paper_width
        if paper_height is not None:
            printer_job["paper_height"] = paper_height

        print_output = self.get_print_output(session_id, printer_job["print_id"])
        if print_output:
            if status is not None:
                print_output["status"] = status
            if job_status is not None:
                print_output["job_status"] = job_status
            if document_name is not None:
                print_output["document_name"] = document_name
            if submitted_time is not None:
                print_output["submitted_time"] = submitted_time
            if paper_name is not None:
                print_output["paper_name"] = paper_name
            if paper_width is not None:
                print_output["paper_width"] = paper_width
            if paper_height is not None:
                print_output["paper_height"] = paper_height
            if printer_job.get("windows_job_id") is not None:
                print_output["windows_job_id"] = printer_job["windows_job_id"]

        self._touch(session)
        self._write_meta(session)
        return printer_job

    def discard_session(self, session_id: str):
        session = self._get_session(session_id)
        if self.active_capture_session_id == session_id:
            self.active_capture_session_id = None
        session_dir = self._session_dir(session)
        if session_dir.exists():
            shutil.rmtree(session_dir)
        del self._sessions[session_id]
        latest = self._get_latest_session()
        self.updated_at = latest["updated_at"] if latest else None
        return {"discarded": session_id}

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

    def get_generated_result(self, session_id: str, result_id: str) -> Optional[dict]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        return next((item for item in session.get("generated_results", []) if item["result_id"] == result_id), None)

    def get_print_output(self, session_id: str, print_id: str) -> Optional[dict]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        return next((item for item in session.get("print_outputs", []) if item["print_id"] == print_id), None)

    def has_printer_job(self, session_id: str, print_id: Optional[str] = None) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        jobs = session.get("printer_jobs", [])
        if print_id is None:
            return bool(jobs)
        return any(job.get("print_id") == print_id for job in jobs)

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
            "selected_frame_id": current_session["selected_frame_id"] if current_session else None,
            "selected_generated_result_id": current_session["selected_generated_result_id"] if current_session else None,
            "selected_generated_result": current_session["selected_generated_result"] if current_session else None,
            "print_outputs": current_session["print_outputs"] if current_session else [],
            "latest_print_output": current_session["latest_print_output"] if current_session else None,
            "printer_jobs": current_session["printer_jobs"] if current_session else [],
            "latest_printer_job": current_session["latest_printer_job"] if current_session else None,
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
            "generated_results": [],
            "selected_frame_id": None,
            "selected_generated_result_id": None,
            "print_outputs": [],
            "printer_jobs": [],
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
        selected_generated_result = None
        if session.get("selected_generated_result_id"):
            selected_generated_result = next(
                (item for item in session.get("generated_results", []) if item["result_id"] == session["selected_generated_result_id"]),
                None,
            )
        latest_print_output = session.get("print_outputs", [])[-1] if session.get("print_outputs") else None
        latest_printer_job = session.get("printer_jobs", [])[-1] if session.get("printer_jobs") else None
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
            "generated_results": list(session.get("generated_results", [])),
            "selected_frame_id": session.get("selected_frame_id"),
            "selected_generated_result_id": session.get("selected_generated_result_id"),
            "selected_generated_result": selected_generated_result,
            "print_outputs": list(session.get("print_outputs", [])),
            "latest_print_output": latest_print_output,
            "printer_jobs": list(session.get("printer_jobs", [])),
            "latest_printer_job": latest_printer_job,
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

    @staticmethod
    def _generate_session_id() -> str:
        return datetime.now().strftime("%Y%m%d_%H_%M")

    @staticmethod
    def _next_session_id(session_id: str) -> str:
        prefix, separator, suffix = session_id.rpartition("_")
        if separator and suffix.isdigit() and len(suffix) == 2 and prefix.count("_") >= 2:
            return f"{prefix}_{int(suffix) + 1:02d}"
        return f"{session_id}_01"


session = SessionState()

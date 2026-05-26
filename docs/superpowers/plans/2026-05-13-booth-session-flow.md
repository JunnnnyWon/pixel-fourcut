# Booth Session Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `pixel_AI` into a session-based booth workflow that collects EOS Utility captures per guest session, supports operator-driven best-shot selection, runs ComfyUI on the selected shot, and exposes synchronized state to both admin and public screens.

**Architecture:** Keep EOS Utility as the booth capture/live-view tool. The FastAPI backend becomes the session orchestrator: it watches the inbox folder, copies captured files into session-scoped storage, exposes explicit session lifecycle endpoints, and emits session snapshots over WebSocket. The React frontend consumes the new session model and separates operator workflow from public status display.

**Tech Stack:** FastAPI, watchfiles, websockets, React, Vite, ComfyUI HTTP/WS API

---

### Task 1: Add a real session domain model

**Files:**
- Modify: `backend/session.py`
- Test: manual API verification via `GET /api/session`

- [ ] Define a session-centric state model with `session_id`, `phase`, `shots`, `selected_shot_id`, `prompt_id`, `result_filename`, `error`, and `logs`.
- [ ] Add helper methods for `start_session`, `finish_capture`, `add_shot`, `select_shot`, `mark_processing`, `mark_result_ready`, `mark_error`, `complete_session`, and `reset`.
- [ ] Preserve a `to_dict()` serializer that returns the full session snapshot used by API and WebSocket responses.

### Task 2: Add session storage paths and metadata helpers

**Files:**
- Modify: `backend/config.py`
- Modify: `backend/session.py`

- [ ] Add a `SESSIONS_FOLDER` config path under `workspace/sessions`.
- [ ] Ensure session start creates `sessions/<session_id>/shots/`.
- [ ] Add helpers to copy new inbox files into the session shot folder and build deterministic shot ids.

### Task 3: Refactor watcher from global gallery mode to capture-session mode

**Files:**
- Modify: `backend/watcher.py`
- Modify: `backend/main.py`

- [ ] Replace the old global `images` list synchronization with session-aware ingestion.
- [ ] When a new image appears in `WATCH_FOLDER`, only ingest it if the active session phase is `capturing`.
- [ ] Broadcast the updated full session snapshot after each accepted shot.
- [ ] Ignore or log files that arrive while no session is capturing.

### Task 4: Replace old selection/run/reset endpoints with session lifecycle endpoints

**Files:**
- Modify: `backend/routers/run.py`
- Modify: `backend/main.py`

- [ ] Add `GET /api/session`.
- [ ] Add `POST /api/session/start`.
- [ ] Add `POST /api/session/finish-capture`.
- [ ] Add `POST /api/session/select-shot`.
- [ ] Add `POST /api/session/run-selected`.
- [ ] Add `POST /api/session/complete`.
- [ ] Keep `POST /api/session/reset` for hard reset.
- [ ] Remove or stop depending on the old `images/selected/status` contract.

### Task 5: Make ComfyUI execution operate on the selected shot

**Files:**
- Modify: `backend/runner.py`
- Modify: `backend/comfy_client.py`
- Modify: `backend/routers/result.py`

- [ ] Resolve the selected shot path from session storage instead of the old inbox filename field.
- [ ] Mark session phase as `processing` before enqueue.
- [ ] On success, store `result_filename` and transition to `result_ready`.
- [ ] On failure, store `error` and transition to `error`.
- [ ] Continue using history fallback if websocket progress is unavailable.

### Task 6: Simplify WebSocket payloads around session snapshots

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/watcher.py`
- Modify: `frontend/src/useSession.js`

- [ ] Replace event-specific frontend patching with full session snapshot updates.
- [ ] Emit `session_init`, `session_updated`, and `session_error`.
- [ ] Update the React hook to store a single session object and derive UI fields from it.

### Task 7: Rebuild the admin UI around the booth workflow

**Files:**
- Modify: `frontend/src/AdminScreen.jsx`
- Modify: `frontend/src/App.css`

- [ ] Add explicit controls for `새 세션 시작`, `촬영 종료`, `베스트컷 선택`, `AI 처리 시작`, `세션 완료`, `강제 초기화`.
- [ ] Show session phase, shot count, selected shot, ComfyUI status, and result preview.
- [ ] Add a lightweight session log panel.
- [ ] Keep preset management and manual image upload, but clearly separate them from the live booth workflow.

### Task 8: Reframe the public/user UI as a status board

**Files:**
- Modify: `frontend/src/UserScreen.jsx`
- Modify: `frontend/src/App.css`

- [ ] Stop treating the public screen as a free-form gallery.
- [ ] Show current booth state: waiting, capturing, reviewing, processing, result ready, error.
- [ ] Display the selected shot during review and the generated result when ready.
- [ ] Keep the layout readable on a shared monitor.

### Task 9: Update startup and env documentation

**Files:**
- Modify: `.env.example`
- Modify: `start.bat`
- Modify: `start.sh`
- Modify or create: `README.md`

- [ ] Document `WATCH_FOLDER` as the EOS Utility inbox folder.
- [ ] Add `SESSIONS_FOLDER` if needed.
- [ ] Document the real booth operating flow: EOS Utility for booth capture, web admin for session control, ComfyUI for selected-shot processing.

### Task 10: Verify the full MVP flow manually

**Files:**
- Evidence only

- [ ] Start backend and frontend build successfully.
- [ ] Start a session from `/admin`.
- [ ] Drop or upload multiple images and confirm they attach to the active session.
- [ ] Finish capture and select one shot.
- [ ] Run AI processing with an active preset.
- [ ] Confirm the user screen and admin screen both reflect state transitions.
- [ ] Confirm reset/complete prepares the system for the next guest.

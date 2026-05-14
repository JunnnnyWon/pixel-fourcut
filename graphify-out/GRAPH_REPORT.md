# Graph Report - pixel_AI  (2026-05-14)

## Corpus Check
- 33 files · ~1,752,585 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 262 nodes · 417 edges · 19 communities detected
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 27 edges (avg confidence: 0.79)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `51aaab1c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]

## God Nodes (most connected - your core abstractions)
1. `SessionState` - 48 edges
2. `SessionStateTests` - 12 edges
3. `SessionApiTests` - 11 edges
4. `PrintPreview()` - 8 edges
5. `_now()` - 8 edges
6. `useSession()` - 7 edges
7. `get_comfyui_headers()` - 7 edges
8. `BaseModel` - 7 edges
9. `_get_active_capture_session_id()` - 7 edges
10. `get_session()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `SessionStateTests` --uses--> `SessionState`  [INFERRED]
  tests/test_session_state.py → backend/session.py
- `PrintScreen()` --calls--> `useSession()`  [INFERRED]
  frontend/src/PrintScreen.jsx → frontend/src/useSession.js
- `run_worker()` --calls--> `get_comfyui_headers()`  [INFERRED]
  backend/runner.py → backend/config.py
- `comfyui_status()` --calls--> `get_comfyui_headers()`  [INFERRED]
  backend/routers/result.py → backend/config.py
- `AdminScreen()` --calls--> `useSession()`  [INFERRED]
  frontend/src/AdminScreen.jsx → frontend/src/useSession.js

## Communities (25 total, 9 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.13
Nodes (3): _now(), SessionState, SessionStateTests

### Community 1 - "Community 1"
Cohesion: 0.08
Nodes (7): all_sessions(), completed_sessions(), current_session(), errored_sessions(), _preview_deadline(), print_ready_sessions(), processing_sessions()

### Community 2 - "Community 2"
Cohesion: 0.15
Nodes (20): BaseModel, _clear_watch_folder(), finish_capture(), _get_active_capture_session_id(), get_session(), get_session_detail(), get_session_result_detail(), rerun_session() (+12 more)

### Community 3 - "Community 3"
Cohesion: 0.16
Nodes (17): bbox_to_slot(), compose_print(), _cover_size(), _default_slots(), get_frame_path(), get_frame_slots(), _get_frame_slots_cached(), list_frames() (+9 more)

### Community 4 - "Community 4"
Cohesion: 0.14
Nodes (17): download_output_image(), get_output_image(), get_output_image_info(), patch_workflow(), queue_prompt(), Replace LoadImage node input and optionally override workflow seeds., Submit workflow to ComfyUI queue, return prompt_id., Submit workflow to ComfyUI queue, return prompt_id. (+9 more)

### Community 5 - "Community 5"
Cohesion: 0.15
Nodes (6): lifespan(), run_worker(), ConnectionManager, _ingest_available_files(), _wait_until_file_stable(), watch_folder()

### Community 6 - "Community 6"
Cohesion: 0.22
Nodes (8): AdminScreen(), QueueCard(), sessionHeroImage(), pickDisplayImage(), resolveHeroImage(), resolveMainImage(), UserScreen(), useSession()

### Community 7 - "Community 7"
Cohesion: 0.26
Nodes (9): getCoverSize(), normalizeLayout(), normalizeSlots(), PrintPreview(), PrintScreen(), scaledPreviewStyle(), scaleLayoutForPreview(), slotStyleFromPixels() (+1 more)

### Community 10 - "Community 10"
Cohesion: 0.25
Nodes (5): list_images(), 타임스탬프 prefix + 특수문자 제거, 현재 세션 기준 이미지/shot 목록 반환, _sanitize(), upload_image()

### Community 13 - "Community 13"
Cohesion: 0.6
Nodes (5): activate_preset(), delete_preset(), _ensure_dir(), list_presets(), upload_preset()

## Knowledge Gaps
- **9 isolated node(s):** `Upload image to ComfyUI, return filename as stored by ComfyUI.`, `Replace LoadImage node input and optionally override workflow seeds.`, `Submit workflow to ComfyUI queue, return prompt_id.`, `Poll history and return the first output image metadata, or None.`, `Poll history and return the first output image filename, or None.` (+4 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SessionState` connect `Community 0` to `Community 1`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Why does `BaseModel` connect `Community 2` to `Community 3`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `SessionState` (e.g. with `.test_start_session_creates_session_and_shots_directory()` and `.test_add_shot_copies_file_into_active_session()`) actually correct?**
  _`SessionState` has 11 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Upload image to ComfyUI, return filename as stored by ComfyUI.`, `Replace LoadImage node input and optionally override workflow seeds.`, `Submit workflow to ComfyUI queue, return prompt_id.` to the rest of the system?**
  _9 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.13 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.08 - nodes in this community are weakly interconnected._
- **Should `Community 4` be split into smaller, more focused modules?**
  _Cohesion score 0.14 - nodes in this community are weakly interconnected._
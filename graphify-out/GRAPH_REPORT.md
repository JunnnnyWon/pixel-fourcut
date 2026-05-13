# Graph Report - pixel_AI  (2026-05-13)

## Corpus Check
- 25 files · ~13,223 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 183 nodes · 292 edges · 14 communities detected
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 20 edges (avg confidence: 0.79)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `13bdc39f`
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

## God Nodes (most connected - your core abstractions)
1. `SessionState` - 38 edges
2. `SessionStateTests` - 8 edges
3. `SessionApiTests` - 7 edges
4. `get_comfyui_headers()` - 7 edges
5. `_FakeWebSocket` - 6 edges
6. `_now()` - 6 edges
7. `ConnectionManager` - 6 edges
8. `_get_active_capture_session_id()` - 6 edges
9. `useSession()` - 5 edges
10. `RunnerEnqueueTests` - 5 edges

## Surprising Connections (you probably didn't know these)
- `SessionStateTests` --uses--> `SessionState`  [INFERRED]
  tests/test_session_state.py → backend/session.py
- `AdminScreen()` --calls--> `useSession()`  [INFERRED]
  frontend/src/AdminScreen.jsx → frontend/src/useSession.js
- `run_worker()` --calls--> `get_comfyui_headers()`  [INFERRED]
  backend/runner.py → backend/config.py
- `comfyui_status()` --calls--> `get_comfyui_headers()`  [INFERRED]
  backend/routers/result.py → backend/config.py
- `UserScreen()` --calls--> `useSession()`  [INFERRED]
  frontend/src/UserScreen.jsx → frontend/src/useSession.js

## Communities (19 total, 7 thin omitted)

### Community 1 - "Community 1"
Cohesion: 0.08
Nodes (7): all_sessions(), completed_sessions(), current_session(), errored_sessions(), _preview_deadline(), print_ready_sessions(), processing_sessions()

### Community 2 - "Community 2"
Cohesion: 0.2
Nodes (16): BaseModel, _clear_watch_folder(), finish_capture(), _get_active_capture_session_id(), get_session(), reset_session(), reset_session_legacy(), run_job() (+8 more)

### Community 3 - "Community 3"
Cohesion: 0.15
Nodes (6): lifespan(), run_worker(), ConnectionManager, _ingest_available_files(), _wait_until_file_stable(), watch_folder()

### Community 4 - "Community 4"
Cohesion: 0.18
Nodes (14): download_output_image(), get_output_image(), get_output_image_info(), patch_workflow(), queue_prompt(), Replace LoadImage node input with the given filename., Submit workflow to ComfyUI queue, return prompt_id., Poll history and return the first output image metadata, or None. (+6 more)

### Community 6 - "Community 6"
Cohesion: 0.29
Nodes (5): AdminScreen(), resolveHeroImage(), resolveMainImage(), UserScreen(), useSession()

### Community 7 - "Community 7"
Cohesion: 0.25
Nodes (5): list_images(), 타임스탬프 prefix + 특수문자 제거, 현재 세션 기준 이미지/shot 목록 반환, _sanitize(), upload_image()

### Community 11 - "Community 11"
Cohesion: 0.6
Nodes (5): activate_preset(), delete_preset(), _ensure_dir(), list_presets(), upload_preset()

## Knowledge Gaps
- **6 isolated node(s):** `Upload image to ComfyUI, return filename as stored by ComfyUI.`, `Replace LoadImage node input with the given filename.`, `Submit workflow to ComfyUI queue, return prompt_id.`, `Poll history and return the first output image filename, or None.`, `타임스탬프 prefix + 특수문자 제거` (+1 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SessionState` connect `Community 0` to `Community 8`, `Community 1`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **Why does `get_comfyui_headers()` connect `Community 4` to `Community 3`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `SessionState` (e.g. with `.test_start_session_creates_session_and_shots_directory()` and `.test_add_shot_copies_file_into_active_session()`) actually correct?**
  _`SessionState` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `get_comfyui_headers()` (e.g. with `run_worker()` and `upload_image()`) actually correct?**
  _`get_comfyui_headers()` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Upload image to ComfyUI, return filename as stored by ComfyUI.`, `Replace LoadImage node input with the given filename.`, `Submit workflow to ComfyUI queue, return prompt_id.` to the rest of the system?**
  _6 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.08 - nodes in this community are weakly interconnected._
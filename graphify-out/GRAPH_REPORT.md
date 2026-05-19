# Graph Report - pixel_AI  (2026-05-19)

## Corpus Check
- 51 files · ~1,760,840 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 391 nodes · 625 edges · 25 communities detected
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 53 edges (avg confidence: 0.79)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `17f31357`
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
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]

## God Nodes (most connected - your core abstractions)
1. `SessionState` - 54 edges
2. `SessionStateTests` - 15 edges
3. `SessionApiTests` - 15 edges
4. `PrinterServiceTests` - 14 edges
5. `PrintApiTests` - 12 edges
6. `useSession()` - 9 edges
7. `PrintPreview()` - 9 edges
8. `_FakeWebSocket` - 9 edges
9. `_now()` - 9 edges
10. `BaseModel` - 9 edges

## Surprising Connections (you probably didn't know these)
- `SessionStateTests` --uses--> `SessionState`  [INFERRED]
  tests/test_session_state.py → backend/session.py
- `PrintScreen()` --calls--> `useSession()`  [INFERRED]
  frontend/src/PrintScreen.jsx → frontend/src/useSession.js
- `run_worker()` --calls--> `get_comfyui_headers()`  [INFERRED]
  backend/runner.py → backend/config.py
- `comfyui_status()` --calls--> `get_comfyui_headers()`  [INFERRED]
  backend/routers/result.py → backend/config.py
- `printer_diagnostics()` --calls--> `get_printer_diagnostics()`  [INFERRED]
  backend/routers/printing.py → backend/printer_service.py

## Communities (37 total, 11 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.12
Nodes (3): _now(), SessionState, SessionStateTests

### Community 1 - "Community 1"
Cohesion: 0.11
Nodes (28): create_test_page(), get_print_job(), get_printer_capabilities(), get_printer_diagnostics(), _is_preferred_paper(), _is_virtual_printer(), list_all_printers(), list_print_drivers() (+20 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (9): all_sessions(), completed_sessions(), current_session(), errored_sessions(), _generate_session_id(), _next_session_id(), _preview_deadline(), print_ready_sessions() (+1 more)

### Community 3 - "Community 3"
Cohesion: 0.15
Nodes (19): applyDragDelta(), applyResizeDelta(), clampScale(), getCoverSize(), getScalePercent(), scaleFromPercent(), buildPrintSessionPool(), nextPrintSessionIdAfterComplete() (+11 more)

### Community 4 - "Community 4"
Cohesion: 0.15
Nodes (12): getAdminHeroState(), AdminScreen(), QueueCard(), sessionHeroImage(), HistoryScreen(), sessionHeroImage(), sessionSummaryText(), pickDisplayImage() (+4 more)

### Community 5 - "Community 5"
Cohesion: 0.19
Nodes (17): _clear_watch_folder(), complete_session(), finish_capture(), _get_active_capture_session_id(), get_session(), get_session_detail(), get_session_result_detail(), rerun_session() (+9 more)

### Community 6 - "Community 6"
Cohesion: 0.14
Nodes (17): download_output_image(), get_output_image(), get_output_image_info(), patch_workflow(), queue_prompt(), Replace LoadImage node input and optionally override workflow seeds., Submit workflow to ComfyUI queue, return prompt_id., Submit workflow to ComfyUI queue, return prompt_id. (+9 more)

### Community 7 - "Community 7"
Cohesion: 0.15
Nodes (7): lifespan(), _finalize_prompt_result(), run_worker(), ConnectionManager, _ingest_available_files(), _wait_until_file_stable(), watch_folder()

### Community 8 - "Community 8"
Cohesion: 0.2
Nodes (12): build_ssh_command(), build_tunnel_config(), _default_ssh_exe(), ensure_tunnel(), is_local_port_open(), main(), parse_env_file(), parse_env_file_content() (+4 more)

### Community 9 - "Community 9"
Cohesion: 0.12
Nodes (4): _FakeIdleWebSocket, _FakeSuccessWebSocket, _FakeWebSocket, RunnerWorkerTests

### Community 12 - "Community 12"
Cohesion: 0.25
Nodes (14): bbox_to_slot(), compose_print(), _cover_size(), _default_slots(), get_frame_path(), get_frame_slots(), _get_frame_slots_cached(), list_frames() (+6 more)

### Community 14 - "Community 14"
Cohesion: 0.33
Nodes (6): default_model_specs(), download_models(), main(), missing_model_specs(), ModelSpec, BootstrapModelsTests

### Community 15 - "Community 15"
Cohesion: 0.25
Nodes (5): list_images(), 타임스탬프 prefix + 특수문자 제거, 현재 세션 기준 이미지/shot 목록 반환, _sanitize(), upload_image()

### Community 17 - "Community 17"
Cohesion: 0.6
Nodes (5): activate_preset(), delete_preset(), _ensure_dir(), list_presets(), upload_preset()

## Knowledge Gaps
- **11 isolated node(s):** `Setup helpers for remote ComfyUI environments.`, `Upload image to ComfyUI, return filename as stored by ComfyUI.`, `Replace LoadImage node input and optionally override workflow seeds.`, `Submit workflow to ComfyUI queue, return prompt_id.`, `Poll history and return the first output image metadata, or None.` (+6 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SessionState` connect `Community 0` to `Community 2`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Why does `useSession()` connect `Community 4` to `Community 3`?**
  _High betweenness centrality (0.010) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `SessionState` (e.g. with `.test_start_session_creates_session_and_shots_directory()` and `.test_start_session_generates_datetime_session_id_with_suffix_on_collision()`) actually correct?**
  _`SessionState` has 14 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Setup helpers for remote ComfyUI environments.`, `Upload image to ComfyUI, return filename as stored by ComfyUI.`, `Replace LoadImage node input and optionally override workflow seeds.` to the rest of the system?**
  _11 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.12 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.11 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.08 - nodes in this community are weakly interconnected._
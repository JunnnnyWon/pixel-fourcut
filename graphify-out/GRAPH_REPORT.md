# Graph Report - pixel_AI  (2026-05-13)

## Corpus Check
- 22 files · ~11,230 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 118 nodes · 169 edges · 11 communities detected
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 10 edges (avg confidence: 0.77)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `15373956`
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

## God Nodes (most connected - your core abstractions)
1. `SessionState` - 23 edges
2. `SessionStateTests` - 6 edges
3. `SessionApiTests` - 6 edges
4. `ConnectionManager` - 6 edges
5. `useSession()` - 5 edges
6. `_now()` - 5 edges
7. `_ensure_dir()` - 5 edges
8. `RunnerEnqueueTests` - 4 edges
9. `watch_folder()` - 4 edges
10. `UserScreen()` - 3 edges

## Surprising Connections (you probably didn't know these)
- `SessionStateTests` --uses--> `SessionState`  [INFERRED]
  tests/test_session_state.py → backend/session.py
- `AdminScreen()` --calls--> `useSession()`  [INFERRED]
  frontend/src/AdminScreen.jsx → frontend/src/useSession.js
- `UserScreen()` --calls--> `useSession()`  [INFERRED]
  frontend/src/UserScreen.jsx → frontend/src/useSession.js
- `lifespan()` --calls--> `run_worker()`  [INFERRED]
  backend/main.py → backend/runner.py
- `lifespan()` --calls--> `watch_folder()`  [INFERRED]
  backend/main.py → backend/watcher.py

## Communities (17 total, 5 thin omitted)

### Community 1 - "Community 1"
Cohesion: 0.18
Nodes (12): BaseModel, _clear_watch_folder(), reset_session(), reset_session_legacy(), run_job(), run_selected(), RunRequest, select_image() (+4 more)

### Community 2 - "Community 2"
Cohesion: 0.15
Nodes (4): lifespan(), run_worker(), ConnectionManager, watch_folder()

### Community 3 - "Community 3"
Cohesion: 0.17
Nodes (9): get_output_image(), patch_workflow(), queue_prompt(), Replace LoadImage node input with the given filename., Submit workflow to ComfyUI queue, return prompt_id., Poll history and return the first output image filename, or None., Upload image to ComfyUI, return filename as stored by ComfyUI., upload_image() (+1 more)

### Community 5 - "Community 5"
Cohesion: 0.29
Nodes (5): list_images(), 타임스탬프 prefix + 특수문자 제거, 현재 세션 기준 이미지/shot 목록 반환, _sanitize(), upload_image()

### Community 6 - "Community 6"
Cohesion: 0.43
Nodes (4): AdminScreen(), resolveMainImage(), UserScreen(), useSession()

### Community 9 - "Community 9"
Cohesion: 0.6
Nodes (5): activate_preset(), delete_preset(), _ensure_dir(), list_presets(), upload_preset()

## Knowledge Gaps
- **6 isolated node(s):** `Upload image to ComfyUI, return filename as stored by ComfyUI.`, `Replace LoadImage node input with the given filename.`, `Submit workflow to ComfyUI queue, return prompt_id.`, `Poll history and return the first output image filename, or None.`, `타임스탬프 prefix + 특수문자 제거` (+1 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SessionState` connect `Community 0` to `Community 8`, `Community 4`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `SessionState` (e.g. with `SessionStateTests` and `.test_start_session_creates_session_and_shots_directory()`) actually correct?**
  _`SessionState` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `useSession()` (e.g. with `AdminScreen()` and `UserScreen()`) actually correct?**
  _`useSession()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Upload image to ComfyUI, return filename as stored by ComfyUI.`, `Replace LoadImage node input with the given filename.`, `Submit workflow to ComfyUI queue, return prompt_id.` to the rest of the system?**
  _6 weakly-connected nodes found - possible documentation gaps or missing edges._
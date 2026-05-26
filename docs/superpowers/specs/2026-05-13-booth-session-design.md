# Booth Session Flow Design

**Date:** 2026-05-13  
**Project:** `/Users/junnnny/Desktop/pixel_AI`

## Goal

현재 `pixel_AI`를 단순 업로드/선택/AI 처리 도구에서, 실제 축제 부스 운영 방식에 맞는 세션 기반 사진 부스 시스템으로 확장한다.

이번 설계의 MVP 범위는 아래를 만족하는 것이다.

- 부스 안에서는 `Canon EOS Utility`가 Live View 및 촬영 직후 프리뷰를 담당한다.
- 웹앱은 부스 밖 운영자 화면과 상태 공유 레이어를 담당한다.
- 촬영된 사진은 세션 단위로 수집된다.
- 운영자는 촬영 종료 후 베스트컷을 선택한다.
- 선택한 사진은 ComfyUI로 처리된다.
- 결과는 저장되고, 출력 직전 상태까지 관리된다.

## Assumption

이 설계는 아래 운영 가정을 전제로 한다.

1. **부스 안 참가자 화면은 웹앱이 아니라 EOS Utility 전체화면을 사용한다.**
2. **촬영 후 3초 프리뷰는 EOS Utility가 이미 제공하는 동작을 그대로 사용한다.**
3. **웹앱은 Live View를 직접 렌더링하지 않는다.**
4. **EOS Utility 또는 운영자가 지정한 폴더에 JPG가 떨어지면, 서버가 이를 현재 세션의 shot으로 편입한다.**
5. **프린터 제어는 이번 변경의 핵심 구현 범위에서 제외하고, print-ready 상태와 결과 파일 경로까지를 다룬다.**

## Current State

현재 코드베이스는 다음 구조다.

- 백엔드: FastAPI
- 프론트엔드: React + Vite
- 입력: `WATCH_FOLDER` 폴더 감시 + 수동 업로드
- 상태: 단일 전역 세션 (`images`, `selected`, `status`, `prompt_id`, `result_filename`, `error`)
- 화면: `/` 사용자 화면, `/admin` 관리자 화면

현재 한계는 다음과 같다.

- 손님 단위의 **세션 경계**가 없다.
- 촬영본이 모두 같은 전역 리스트에 누적된다.
- 촬영 중 / 선택 중 / 처리 중 / 출력 준비 완료 같은 **운영 단계**가 모델링되어 있지 않다.
- EOS Utility에서 생성되는 촬영본을 “현재 손님 세션”으로 묶는 규칙이 없다.
- Shot 메타데이터가 없어서 “몇 장 찍었는지 / 언제 찍었는지 / 어떤 컷을 골랐는지”를 기록할 수 없다.

## Recommended Approach

### Approach A: EOS Utility 유지 + 웹앱은 세션 운영 전용

**권장안.**

- 부스 안 Live View와 3초 프리뷰는 EOS Utility에 맡긴다.
- 웹앱은 세션 시작, 촬영본 수집, 베스트컷 선택, AI 처리, 결과 저장을 담당한다.
- 구현 리스크가 가장 낮고, EOS 60D/Windows/USB 테더링의 불안정성을 최소화한다.

장점:

- 기존 촬영 동선을 거의 건드리지 않는다.
- Live View/프리뷰를 웹으로 재구현하지 않아도 된다.
- 현재 코드베이스의 `WATCH_FOLDER` 기반 구조를 살릴 수 있다.

단점:

- 부스 안 화면과 웹앱 화면이 완전히 통합되지는 않는다.
- 촬영 프리뷰 3초는 웹앱 상태가 아니라 외부 앱 동작에 의존한다.

### Approach B: 웹앱이 부스 안 화면까지 제어

- Live View 대체, 프리뷰, 카운트다운까지 웹앱이 담당한다.
- 장기적으로는 좋지만 EOS 60D + EOS Utility 조합에서는 구현 난이도가 높다.

이번 범위에서는 채택하지 않는다.

## Target User Flow

1. 관리자가 **새 세션 시작** 버튼을 누른다.
2. 세션 상태가 `capturing`으로 전환된다.
3. 참가자가 부스 안에서 EOS Utility Live View를 보며 릴리즈 버튼으로 여러 장 촬영한다.
4. 새 사진이 `WATCH_FOLDER`에 생성될 때마다, 서버가 이를 현재 세션의 `shots`에 추가한다.
5. 관리자가 촬영 종료를 누르면 세션 상태가 `reviewing`으로 전환된다.
6. 관리자는 썸네일 목록에서 베스트컷 하나를 선택한다.
7. 선택 컷으로 AI 처리를 시작하면 상태가 `processing`으로 전환된다.
8. ComfyUI 처리가 끝나면 상태가 `result_ready`로 전환되고 결과 파일이 세션에 연결된다.
9. 운영자는 결과를 확인한 뒤 출력한다.
10. 출력이 끝나면 `completed`로 마감하거나, 즉시 새 세션을 시작한다.

## State Model

전역 단일 상태를 아래 세션 중심 구조로 교체한다.

### Session Phase

- `idle`: 진행 중 세션 없음
- `capturing`: 촬영 중
- `reviewing`: 촬영 완료, 베스트컷 선택 대기
- `processing`: AI 처리 중
- `result_ready`: 결과 확인 및 출력 대기
- `completed`: 출력 후 종료
- `error`: 세션 처리 중 오류

### Session Data

- `session_id`
- `phase`
- `shots[]`
- `selected_shot_id`
- `prompt_id`
- `result_filename`
- `result_url`
- `error`
- `log[]`
- `created_at`
- `updated_at`

### Shot Data

- `shot_id`
- `filename`
- `url`
- `captured_at`
- `source` (`watcher` | `upload`)

## Storage Layout

현재 `WATCH_FOLDER`는 inbox로 유지하되, 세션별 저장 구조를 추가한다.

```text
workspace/
  input/                # EOS Utility 또는 수동 업로드가 떨어지는 inbox
  sessions/
    session-20260513-001/
      shots/
        shot-001.jpg
        shot-002.jpg
      selected.jpg
      result.png
      meta.json
  presets/
```

운영 규칙:

- `input/`은 감시용 inbox다.
- 세션에 편입된 이미지는 `sessions/<session_id>/shots/`로 복사한다.
- 이후 UI는 inbox가 아니라 세션 데이터를 기준으로 렌더링한다.

## Backend Changes

### 1. Session Model Refactor

`backend/session.py`

- 현재 전역 필드를 `active_session` 중심 구조로 바꾼다.
- helper를 추가한다:
  - `start_session()`
  - `finish_capture()`
  - `add_shot_from_file()`
  - `select_shot()`
  - `mark_processing()`
  - `mark_result_ready()`
  - `mark_completed()`
  - `reset_all()`

### 2. Watcher Behavior Change

`backend/watcher.py`

- 새 이미지가 inbox에 생기면:
  - 현재 세션이 `capturing`인지 확인
  - 맞으면 세션 shot으로 편입
  - 세션 상태 전체를 WebSocket으로 브로드캐스트
- 세션이 없거나 `capturing`이 아니면 무시하거나 로그만 남긴다.

### 3. Run Flow Change

`backend/runner.py`, `backend/routers/run.py`

- `selected filename`이 아니라 `selected shot` 기준으로 처리한다.
- 처리 성공 시 세션의 `result_filename`, `result_url`, `phase=result_ready`를 갱신한다.

### 4. New Session Endpoints

`backend/routers/run.py` 또는 별도 router

- `POST /api/session/start`
- `POST /api/session/finish-capture`
- `POST /api/session/select-shot`
- `POST /api/session/run-selected`
- `POST /api/session/complete`
- `POST /api/session/reset`
- `GET /api/session`

## Frontend Changes

### Admin Screen

`frontend/src/AdminScreen.jsx`

운영자 화면은 아래 중심으로 바뀐다.

- 현재 세션 상태 배지
- 새 세션 시작 버튼
- 촬영 종료 버튼
- 현재 세션 shots 썸네일 목록
- 선택 컷 강조
- AI 처리 시작 버튼
- 결과 미리보기
- 새 손님으로 넘기기 버튼
- 운영 로그

### User Screen

`frontend/src/UserScreen.jsx`

이번 범위에서는 “부스 안 Live View”를 대체하지 않는다. 대신 웹 사용자 화면은 아래 목적만 가진다.

- 현재 세션 진행 상태
- 촬영 대기 / 선택 중 / AI 처리 중 / 결과 준비 완료 안내
- 선택된 원본 또는 최종 결과 표시

즉, 웹 사용자 화면은 **공용 상태 보드** 역할이고, 실제 촬영 화면은 EOS Utility가 담당한다.

## WebSocket Contract

현재의 `new_image`, `selected`, `done` 수준 이벤트를 세션 스냅샷 중심으로 단순화한다.

권장 이벤트:

- `session_init`
- `session_updated`
- `session_error`

각 이벤트는 가능한 한 세션 전체 스냅샷을 포함한다.

이유:

- 프론트가 이벤트 순서에 덜 민감해진다.
- 리로드/재연결 시 복구가 쉬워진다.

## Error Handling

- 세션 없이 촬영본이 들어오면 무시하고 로그에 남긴다.
- `capturing`이 아닌 상태에서 새 이미지를 받으면 무시한다.
- 선택 컷 없이 AI 실행하면 409를 반환한다.
- 활성 프리셋이 없으면 400을 반환한다.
- ComfyUI 실패 시 세션을 `error`로 전환하고 로그와 오류 메시지를 보존한다.

## Success Criteria

이번 변경이 완료되었다고 보려면 아래가 동작해야 한다.

1. 운영자가 새 세션을 시작할 수 있다.
2. 촬영 중 생성된 파일이 현재 세션의 shot 목록으로 누적된다.
3. 촬영 종료 후 운영자가 shot 중 하나를 선택할 수 있다.
4. 선택 컷으로 AI 처리를 시작할 수 있다.
5. 결과가 세션에 연결되고 `result_ready` 상태가 된다.
6. 사용자/관리자 화면이 둘 다 같은 세션 상태를 반영한다.
7. 세션 종료 후 다음 손님을 위해 초기화할 수 있다.

## Out of Scope

- EOS Utility 자체 제어
- 웹 기반 Live View
- 자동 프린터 송신
- 다중 동시 세션
- 사용자 셀프 선택 UI


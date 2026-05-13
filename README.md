# Pixel AI Booth MVP

`/Users/junnnny/Desktop/pixel_AI`

## What This Version Does

이 버전은 실제 부스 운영 흐름을 기준으로 구성되어 있다.

1. 부스 안에서는 `Canon EOS Utility`가 Live View와 촬영 직후 프리뷰를 담당한다.
2. EOS Utility가 저장한 사진이 `WATCH_FOLDER`로 들어오면, 백엔드가 현재 세션의 shot으로 수집한다.
3. 운영자는 `/admin`에서 세션 시작, 촬영 종료, 베스트컷 선택, AI 처리, 세션 완료를 진행한다.
4. 공용 화면(`/`)은 현재 세션 상태와 로그를 보여준다.
5. 선택된 컷은 활성 ComfyUI 프리셋으로 처리된다.

## Required Setup

- Python 3.9+
- Node.js + npm
- ComfyUI running at `COMFYUI_URL`
- EOS Utility save target pointed at `WATCH_FOLDER`

## Environment

Copy `.env.example` to `.env` and edit as needed.

Important paths:

- `WATCH_FOLDER`: EOS Utility 또는 수동 업로드 이미지가 들어오는 inbox
- `PRESETS_FOLDER`: ComfyUI API workflow preset 보관 위치
- `SESSIONS_FOLDER`: 세션별 shot / result / meta 저장 위치
- `COMFYUI_HEADERS_JSON`: Runyour 프록시/게이트웨이가 요구하는 추가 헤더(JSON 문자열)
- `COMFYUI_BEARER_TOKEN`: Runyour 프록시가 Bearer 토큰을 요구할 때 사용

Recommended env profiles:

- `.env.local.example`: 로컬 ComfyUI 테스트용
- `.env.runyour.example`: Runyour 원격 ComfyUI 연결용

## Run

### Windows

```bat
start.bat
```

### macOS / Linux

```bash
./start.sh
```

## Booth Workflow

1. `/admin`에서 **새 세션 시작**
2. 참가자가 부스 안에서 EOS Utility Live View를 보며 촬영
3. 촬영된 파일이 세션 shot 목록에 자동 누적
4. 운영자가 **촬영 종료**
5. 운영자가 베스트컷 선택
6. **AI 처리 시작**
7. 결과 확인 후 출력
8. **세션 완료** 또는 **강제 초기화** 후 다음 손님 진행

## Local vs Runyour

### Local Windows test

- `COMFYUI_URL=http://localhost:8188`
- `workspace/presets/active.json`에 로컬 workflow 사용
- 테스트 이미지는 `WATCH_FOLDER`에 직접 넣어서 촬영을 시뮬레이션

### Runyour remote GPU

- Runyour AI Cloud에서 GPU 머신을 띄우고 ComfyUI template 사용
- 필요한 모델 / custom node / workflow 의존성 설치
- 부스 PC의 `.env`를 `.env.runyour.example` 기준으로 교체
- `COMFYUI_URL`을 Runyour ComfyUI endpoint로 변경
- 필요 시 `COMFYUI_HEADERS_JSON` 또는 `COMFYUI_BEARER_TOKEN` 설정
- 결과 이미지는 원격 ComfyUI만 보지 않고 `workspace/sessions/<session_id>/result.*`로 로컬 캐시됨
- 따라서 행사 중 원격 GPU 세션이 재시작되더라도 이미 생성된 결과 재확인은 로컬에서 가능

## Routes

- `/` 공용 상태 화면
- `/admin` 운영자 화면
- `/api/session/*` 세션 제어 API
- `/api/presets/*` ComfyUI workflow preset 관리

@echo off
setlocal
set SCRIPT_DIR=%~dp0

:: .env 없으면 .env.example 복사
if not exist "%SCRIPT_DIR%.env" copy "%SCRIPT_DIR%.env.example" "%SCRIPT_DIR%.env"

:: workspace 폴더 생성
if not exist "%SCRIPT_DIR%workspace\input"   mkdir "%SCRIPT_DIR%workspace\input"
if not exist "%SCRIPT_DIR%workspace\presets" mkdir "%SCRIPT_DIR%workspace\presets"

:: Python 의존성 설치
pip install -q -r "%SCRIPT_DIR%requirements.txt"

:: 프론트엔드 빌드
cd /d "%SCRIPT_DIR%frontend"
call npm install --silent
call npm run build
cd /d "%SCRIPT_DIR%"

echo.
echo [start.bat] ComfyUI가 포트 8188에서 실행 중인지 확인하세요.
echo [start.bat] FastAPI 시작 중 (http://localhost:8000)
echo.

uvicorn backend.main:app --host 0.0.0.0 --port 8000

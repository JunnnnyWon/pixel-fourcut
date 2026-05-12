@echo off
setlocal
set SCRIPT_DIR=%~dp0

if not exist "%SCRIPT_DIR%.env" copy "%SCRIPT_DIR%.env.example" "%SCRIPT_DIR%.env"

if not exist "%SCRIPT_DIR%workspace\input"   mkdir "%SCRIPT_DIR%workspace\input"
if not exist "%SCRIPT_DIR%workspace\presets" mkdir "%SCRIPT_DIR%workspace\presets"
if not exist "%SCRIPT_DIR%workspace\sessions" mkdir "%SCRIPT_DIR%workspace\sessions"

if not exist "%SCRIPT_DIR%.venv" (
    echo [start.bat] Creating virtualenv with Python 3.13...
    py -3.13 -m venv "%SCRIPT_DIR%.venv"
)

call "%SCRIPT_DIR%.venv\Scripts\activate.bat"
pip install -q -r "%SCRIPT_DIR%requirements.txt"

cd /d "%SCRIPT_DIR%frontend"
call npm install --silent
call npm run build
cd /d "%SCRIPT_DIR%"

echo.
echo [start.bat] Make sure ComfyUI is running on port 8188.
echo [start.bat] Starting FastAPI at http://localhost:8000
echo.

uvicorn backend.main:app --host 0.0.0.0 --port 8000

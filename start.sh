#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Load env
[ -f .env ] || cp .env.example .env
source .env

# Create required folders
mkdir -p "${WATCH_FOLDER:-/workspace/input}"
mkdir -p "${PRESETS_FOLDER:-/workspace/presets}"
mkdir -p "${SESSIONS_FOLDER:-/workspace/sessions}"

# Start ComfyUI in background (if not already running)
if ! pgrep -f "comfyui" > /dev/null 2>&1; then
  echo "[start.sh] Starting ComfyUI..."
  COMFYUI_DIR="${COMFYUI_DIR:-/workspace/ComfyUI}"
  nohup python "$COMFYUI_DIR/main.py" \
    --listen 0.0.0.0 \
    --port 8188 \
    --output-directory "${WATCH_FOLDER:-/workspace/input}/../output" \
    > /tmp/comfyui.log 2>&1 &
  echo "[start.sh] Waiting for ComfyUI to start..."
  sleep 10
fi

# Install Python deps
pip install -q -r requirements.txt

# Build frontend
echo "[start.sh] Building frontend..."
cd frontend
npm install --silent
npm run build
cd ..

# Start FastAPI
echo "[start.sh] Starting FastAPI on :8000"
uvicorn backend.main:app --host 0.0.0.0 --port 8000

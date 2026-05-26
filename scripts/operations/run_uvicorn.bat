@echo off
cd /d %~dp0
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 1>server.out.log 2>server.err.log

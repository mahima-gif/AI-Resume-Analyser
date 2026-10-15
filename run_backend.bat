@echo off
echo ====================================================
echo Starting AI Resume Analyzer Backend (FastAPI)...
echo ====================================================
cd /d "%~dp0backend"
"..\venv\Scripts\python.exe" -m uvicorn main:app --reload --port 8000
pause

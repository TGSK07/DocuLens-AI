@echo off
REM Windows quick-start.
if exist ".venv\Scripts\activate.bat" call .venv\Scripts\activate.bat
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

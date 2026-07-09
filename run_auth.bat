@echo off
REM One-time (and every ~60 days) LinkedIn re-authorization.
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" src\pipeline.py auth
) else (
    python src\pipeline.py auth
)
pause

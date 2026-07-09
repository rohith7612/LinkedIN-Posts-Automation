@echo off
REM Daily automated step: collect -> preprocess -> verify -> prep NotebookLM handoff.
REM Point Windows Task Scheduler at this file.
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" src\pipeline.py phase1
) else (
    python src\pipeline.py phase1
)

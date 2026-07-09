@echo off
REM Manual step: run this AFTER you've saved NotebookLM infographic exports into
REM data\<today>\infographics\. Generates the caption and posts to LinkedIn.
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" src\pipeline.py phase2
) else (
    python src\pipeline.py phase2
)
pause

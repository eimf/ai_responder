@echo off
REM ============================================================
REM  AI Responder — Launch script
REM  Run this after setup.bat has been executed once.
REM ============================================================

REM Activate the virtual environment
call venv\Scripts\activate.bat

REM Launch the application (pythonw suppresses the console window)
start "" pythonw main.py

REM If pythonw fails (e.g. not found), fall back to python
IF ERRORLEVEL 1 (
    python main.py
)

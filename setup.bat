@echo off
REM ============================================================
REM  AI Responder — First-time setup script for Windows
REM  Run this once to create a virtual environment and install
REM  all required dependencies.
REM ============================================================

echo.
echo  AI Responder — Setup
echo  =====================
echo.

REM Check Python is available
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo  [ERROR] Python is not installed or not on PATH.
    echo  Please install Python 3.11+ from https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo  [1/3] Creating virtual environment...
python -m venv venv
IF ERRORLEVEL 1 (
    echo  [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

echo  [2/3] Activating virtual environment...
call venv\Scripts\activate.bat

echo  [3/3] Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo  ============================================================
echo   Setup complete!
echo  ============================================================
echo.
echo   To run the application:
echo     1. Double-click  run.bat
echo     OR
echo     1. Open a terminal in this folder
echo     2. Run:  venv\Scripts\activate
echo     3. Run:  python main.py
echo.
pause

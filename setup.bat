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

echo  [1/4] Creating virtual environment...
python -m venv venv
IF ERRORLEVEL 1 (
    echo  [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

echo  [2/4] Activating virtual environment...
call venv\Scripts\activate.bat

echo  [3/4] Installing Python dependencies...
pip install --upgrade pip
pip install -r requirements.txt

echo  [4/4] Checking for Tesseract OCR (optional fallback)...
tesseract --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo.
    echo  [INFO] Tesseract OCR is not installed.
    echo  Tesseract is used as a last-resort OCR fallback.
    echo  UIAutomation will be used as the primary extraction method.
    echo  To install Tesseract (optional):
    echo    https://github.com/UB-Mannheim/tesseract/wiki
    echo    Install to: C:\Program Files\Tesseract-OCR\
    echo.
) ELSE (
    echo  [OK] Tesseract OCR found.
)

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

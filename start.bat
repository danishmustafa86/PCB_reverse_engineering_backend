@echo off
REM Start script for PCB Reverse Engineering System (Windows)

echo ============================================================
echo PCB Reverse Engineering System - Starting Server
echo ============================================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Start the server
python run.py

pause


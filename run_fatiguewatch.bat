@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo Project environment not found. Create it with Python 3.12, then install requirements.txt.
    echo %PYTHON%
    pause
    exit /b 1
)

"%PYTHON%" app.py

if errorlevel 1 (
    echo.
    echo FatigueWatch stopped with an error.
    pause
)

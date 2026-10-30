@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
	echo ERROR: Setup not completed.
	echo Double-click setup.bat first.
	pause
	exit /b 1
)

echo Starting FatigueWatch backend...
start "FatigueWatch Backend" /D "%~dp0" cmd /k ""%~dp0.venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"

timeout /t 2 /nobreak >nul

echo Starting FatigueWatch frontend...
start "FatigueWatch Frontend" /D "%~dp0frontend" cmd /k "npm run dev"

timeout /t 4 /nobreak >nul
start "" http://localhost:5173

echo.
echo FatigueWatch started.
echo Frontend: http://localhost:5173
echo Backend:  http://localhost:8000/health

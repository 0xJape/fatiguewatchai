@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo FatigueWatch AI - Setup
echo ========================================
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python launcher not found.
  echo Install Python 3.12 from https://www.python.org/downloads/
  pause
  exit /b 1
)

py -3.12 --version >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python 3.12 not found.
  echo Install Python 3.12 from https://www.python.org/downloads/
  pause
  exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
  echo ERROR: Node.js not found.
  echo Install Node.js LTS from https://nodejs.org/
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo ERROR: npm not found. Reinstall Node.js LTS.
  pause
  exit /b 1
)

echo Creating Python virtual environment...
if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv
  if errorlevel 1 goto :failed
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto :failed

 echo Installing Python dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 goto :failed

echo Installing frontend dependencies...
cd frontend
call npm install
if errorlevel 1 goto :failed
cd ..

echo Downloading MediaPipe face landmark model...
if not exist "models" mkdir "models"
if not exist "models\face_landmarker.task" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task' -OutFile 'models\face_landmarker.task'"
  if errorlevel 1 goto :failed
)

if not exist "models\face_landmarker.task" goto :failed

echo.
echo Setup complete.
echo Start application with: run_all.bat
echo Open: http://localhost:5173
pause
exit /b 0

:failed
echo.
echo Setup failed. Read error above, then rerun setup.bat.
pause
exit /b 1

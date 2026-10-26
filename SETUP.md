# FatigueWatch AI Setup Guide

Complete local setup for Windows.

## Fast setup

Install Python 3.12 and Node.js LTS first, then double-click `setup.bat`. It creates the virtual environment, installs Python and frontend dependencies, and downloads `models/face_landmarker.task`.

After setup finishes, double-click `run_all.bat`.

## 1. Install prerequisites

Install:

- Python 3.12
- Node.js 18 or newer
- npm
- A modern browser
- Webcam

Verify installations in PowerShell:

```powershell
py -3.12 --version
node --version
npm --version
```

## 2. Clone project

```powershell
git clone https://github.com/0xJape/fatiguewatchai.git
cd fatiguewatchai
```

## 3. Create Python environment

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, run this once in the current PowerShell window:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

Then activate again:

```powershell
.\.venv\Scripts\Activate.ps1
```

## 4. Install frontend dependencies

```powershell
Push-Location frontend
npm install
Pop-Location
```

## 5. Install required MediaPipe model

`face_landmarker.task` is required by backend face and eye tracking.

Git excludes this file because it is a binary model asset. Download it manually into this exact location:

```text
models/face_landmarker.task
```

PowerShell download command:

```powershell
New-Item -ItemType Directory -Force models | Out-Null
Invoke-WebRequest `
  -Uri "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task" `
  -OutFile "models/face_landmarker.task"
```

Verify the file exists:

```powershell
Get-Item models\face_landmarker.task
```

Expected file size is approximately 3.7 MB. Do not rename it. Do not place it inside `frontend`.

## 6. Start application

Recommended:

```powershell
run_all.bat
```

This starts:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- Health check: `http://localhost:8000/health`

Or start services manually.

Terminal 1 — backend:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Terminal 2 — frontend:

```powershell
Push-Location frontend
npm run dev
```

Open:

```text
http://localhost:5173
```

Allow browser camera access when prompted.

## 7. Validate setup

Run backend checks:

```powershell
.\.venv\Scripts\python.exe -m py_compile backend\main.py
.\.venv\Scripts\python.exe -m pytest tests -q
```

Build frontend:

```powershell
Push-Location frontend
npm run build
Pop-Location
```

## Troubleshooting

### `models/face_landmarker.task` missing

Download the model again and verify this exact path:

```text
<project-root>\models\face_landmarker.task
```

### Camera does not start

- Use `http://localhost:5173`.
- Allow camera access in browser settings.
- Close other applications using the webcam.
- Restart the frontend and backend.

### Backend health check fails

Confirm backend is running on port `8000`:

```powershell
Invoke-WebRequest http://localhost:8000/health
```

### PowerShell script execution error

Run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

This changes policy only for the current PowerShell session.

## Why model is not in Git

The model is excluded by `.gitignore`:

```text
models/*.task
```

This keeps the repository smaller and avoids committing binary model assets. Every client must download the model once during setup. The backend expects the model at `models/face_landmarker.task`.

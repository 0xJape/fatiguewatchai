# FatigueWatch AI

> Real-time driver fatigue monitoring for controlled, simulated-driving research.

FatigueWatch AI uses a browser webcam and MediaPipe facial landmarks to monitor eye openness, prolonged eye closure, blink activity, gaze direction, yawning, and PERCLOS. A FastAPI backend analyzes frames while a React cockpit dashboard displays live telemetry and alerts.

**Prototype warning:** this is not a certified vehicle-safety, medical, or emergency system. Test only in controlled conditions. Never use it as a replacement for safe driving.

## Features

- Real-time webcam monitoring through browser permissions
- MediaPipe face and eye landmark tracking
- Six-point Eye Aspect Ratio (EAR) calculation
- Five-second eye calibration and smoothed measurements
- Blink-rate and prolonged eye-closure tracking
- Rolling 30-second PERCLOS calculation
- Heuristic gaze direction: left, center, right
- Heuristic yawn detection and visible `YAWN DETECTED` warning
- Rule-based states: alert, possible drowsiness, high risk, tracking unavailable
- Visual warnings, generated tones, and voice alerts
- Low-light enhancement and optional night vision
- Fullscreen camera view with telemetry overlay
- Session analytics page with gaze, blink, PERCLOS, and event statistics
- Print-friendly report export through browser `Save as PDF`
- Backend debug window showing face and eye tracking lines

## Technology

| Layer | Technology |
|---|---|
| Frontend | React, Vite, JSX, CSS |
| Backend | Python, FastAPI, Uvicorn, WebSocket |
| Computer vision | OpenCV, NumPy, MediaPipe Tasks |
| Face model | MediaPipe Face Landmarker (`models/face_landmarker.task`) |
| Browser APIs | WebRTC camera, Web Audio, Fullscreen, Print |
| Testing | Pytest, Python compile check, Vite production build |

## Requirements

- Windows 10/11
- Python 3.12
- Node.js 18+ and npm
- Webcam and browser camera permission
- Modern Chromium, Edge, or Firefox browser

For complete Windows installation steps, see [`SETUP.md`](SETUP.md).

## Setup

Open PowerShell in project root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Push-Location frontend
npm install
Pop-Location
```

Required model file:

```text
models/face_landmarker.task
```

The model is intentionally excluded from Git because it is a binary asset. Place it at that path before running the backend.

## Start web application

Recommended one-click Windows launcher:

```powershell
run_all.bat
```

Or use two terminals:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

```powershell
Push-Location frontend
npm run dev
```

Open `http://localhost:5173`. Allow camera access. Backend health check: `http://localhost:8000/health`.

## Test and build

```powershell
.\.venv\Scripts\python.exe -m py_compile backend\main.py
.\.venv\Scripts\python.exe -m pytest tests -q
Push-Location frontend
npm run build
Pop-Location
```

## Repository layout

```text
backend/              FastAPI WebSocket server and detector
fatiguewatch/         Shared eye-metric functions
frontend/             React/Vite dashboard
models/               Local MediaPipe model file
tests/                Automated tests
FEatures.md           Feature inventory
PROJECT_OVERVIEW.md   Project scope and safety context
run_all.bat           Windows launcher
```

## Known limits

- Fatigue classification is rule-based, not trained ML classification.
- Gaze and yawn detection use landmark heuristics and need calibration across users and cameras.
- Data annotation and accuracy/precision/recall/F1 evaluation are not included yet.
- Reports currently use browser print-to-PDF, not server-generated PDF files.
- The current setup is local-only: frontend connects to `localhost:8000`.

## Privacy

Camera frames are sent from browser to the local backend over WebSocket for analysis. No cloud upload is configured. Keep `.env` private and never commit credentials.

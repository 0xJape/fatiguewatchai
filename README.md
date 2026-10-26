# FatigueWatch AI

Functionality-first desktop MVP for controlled simulated-driving research.

## Run

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py app.py
```

## Test

```powershell
pytest
```

Optional font files can be added later under `assets/fonts/`. The app uses system fallbacks when they are absent.

## Web dashboard

Backend:

```powershell
run_backend.bat
```

Frontend, in a second terminal:

```powershell
run_frontend.bat
```

Open `http://localhost:5173`.

Current web scaffold streams browser camera frames through WebSocket and displays live dashboard placeholders. Face-landmark inference remains next step.

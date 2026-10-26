@echo off
cd /d "%~dp0"
C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
pause

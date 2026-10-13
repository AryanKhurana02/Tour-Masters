@echo off
title PahadPath
echo Starting PahadPath...
echo.
echo Backend:  http://127.0.0.1:8000/api/health
echo Frontend: http://localhost:5173
echo.

start "PahadPath Backend" cmd /k "cd backend && py -3.12 -m uvicorn app.main:app --reload"
timeout /t 2 >nul
start "PahadPath Frontend" cmd /k "cd frontend && npm run dev"

timeout /t 4 >nul
start http://localhost:5173

echo Both servers are running. Close the terminal windows to stop them.
timeout /t 3 >nul
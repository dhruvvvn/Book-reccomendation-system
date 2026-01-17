@echo off
echo ==========================================
echo       Starting BookAI System v2.0 🚀
echo ==========================================

:: 1. Start Backend (FastAPI)
echo Starting Backend Server...
start "BookAI Backend" cmd /k "cd backend && python -m uvicorn app.main:app --reload --port 8000"

:: 2. Start Frontend (React + Vite)
echo Starting React Frontend...
:: We adhere to your custom Node.js path
start "BookAI Frontend" cmd /k "cd frontend-react && set PATH=D:\softwares;%PATH% && npm run dev"

echo.
echo ==========================================
echo  🎉 Servers are running!
echo  👉 Frontend: http://localhost:3000
echo  👉 Backend:  http://localhost:8000
echo ==========================================
echo.
pause

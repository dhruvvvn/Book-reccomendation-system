@echo off
echo Starting Book Recommendation API...
echo.

if not exist "venv" (
    echo Error: Virtual environment not found. Please run setup.bat first.
    pause
    exit /b
)

call venv\Scripts\activate
uvicorn app.main:app --reload

pause

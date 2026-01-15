@echo off
echo ==========================================
echo Setting up Book Recommendation Backend
echo ==========================================

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    pause
    exit /b
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
) else (
    echo Virtual environment already exists.
)

REM Activate virtual environment
call venv\Scripts\activate

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Create .env from example if it doesn't exist
if not exist ".env" (
    echo Creating .env file from .env.example...
    copy .env.example .env
    echo.
    echo [IMPORTANT] Please edit the .env file and add your GEMINI_API_KEY!
) else (
    echo .env file already exists.
)

echo.
echo ==========================================
echo Setup Complete!
echo ==========================================
echo 1. Edit .env and add your GEMINI_API_KEY
echo 2. Run 'ingest.bat' to load sample data
echo 3. Run 'run.bat' to start the server
echo.
pause

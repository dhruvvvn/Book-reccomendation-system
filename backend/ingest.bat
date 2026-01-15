@echo off
echo Ingesting Book Data...
echo.

if not exist "venv" (
    echo Error: Virtual environment not found. Please run setup.bat first.
    pause
    exit /b
)

call venv\Scripts\activate
python -m scripts.ingest_data

echo.
pause

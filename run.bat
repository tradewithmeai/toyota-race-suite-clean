@echo off
cd /d "%~dp0"

REM Check if venv exists
if not exist "venv\Scripts\python.exe" (
    echo Virtual environment not found. Running setup first...
    echo.

    REM Create virtual environment
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        echo Please install Python 3.10+ from https://python.org
        pause
        exit /b 1
    )

    REM Install dependencies
    call venv\Scripts\activate.bat
    pip install --upgrade pip
    pip install -r requirements.txt

    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
    echo.
    echo Setup complete! Starting application...
    echo.
)

REM Run the application
venv\Scripts\python.exe -m src.app.main

@echo off
cd /d "%~dp0"

REM Check if venv exists
if not exist "venv\Scripts\python.exe" (
    echo ============================================
    echo  First-time setup - Creating environment
    echo ============================================
    echo.

    REM Create virtual environment
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to create virtual environment
        echo Please install Python 3.10+ from https://python.org
        echo.
        pause
        exit /b 1
    )

    REM Activate and install dependencies
    echo Installing dependencies (this may take a minute)...
    call venv\Scripts\activate.bat
    pip install --upgrade pip >nul 2>&1
    pip install -r requirements.txt

    if errorlevel 1 (
        echo.
        echo ERROR: Failed to install dependencies
        echo.
        pause
        exit /b 1
    )

    echo.
    echo ============================================
    echo  Setup complete! Starting application...
    echo ============================================
    echo.
)

REM Run the application
echo Starting Race Replay...
venv\Scripts\python.exe -m src.app.main

REM If app exits with error, pause so user can see
if errorlevel 1 (
    echo.
    echo Application exited with error code %errorlevel%
    pause
)

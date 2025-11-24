@echo off
REM Toyota Race Suite - Windows Build Script
REM Builds standalone executable using PyInstaller

echo ============================================
echo  Toyota Race Suite - Windows Build
echo ============================================
echo.

cd /d "%~dp0"

REM Check if venv exists
if not exist "venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Check if PyInstaller is installed
venv\Scripts\pip.exe show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    venv\Scripts\pip.exe install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller
        pause
        exit /b 1
    )
)

REM Clean previous builds
echo Cleaning previous builds...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "ToyotaRaceSuite.exe" del /q "ToyotaRaceSuite.exe"

echo.
echo Building executable (this may take 2-5 minutes)...
echo.

REM Run PyInstaller
venv\Scripts\pyinstaller.exe --clean --noconfirm ToyotaRaceSuite.spec

if errorlevel 1 (
    echo.
    echo ============================================
    echo  BUILD FAILED!
    echo ============================================
    echo.
    pause
    exit /b 1
)

REM Check if executable was created
if not exist "dist\ToyotaRaceSuite.exe" (
    echo.
    echo ERROR: Executable not found in dist folder
    pause
    exit /b 1
)

echo.
echo ============================================
echo  BUILD SUCCESSFUL!
echo ============================================
echo.
echo Executable created: dist\ToyotaRaceSuite.exe
echo Size:
dir "dist\ToyotaRaceSuite.exe" | find "ToyotaRaceSuite.exe"
echo.
echo You can now:
echo   1. Test: Run dist\ToyotaRaceSuite.exe
echo   2. Distribute: Copy dist\ToyotaRaceSuite.exe to release folder
echo.
pause

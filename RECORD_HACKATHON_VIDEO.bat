@echo off
echo ============================================================
echo   HACKATHON VIDEO RECORDER - TRD 2024
echo ============================================================
echo.
echo This will run a 2.5-minute AUTOMATED demo
echo.
echo BEFORE YOU CLICK, MAKE SURE:
echo   [X] Screen recording software is READY (OBS or Windows Game Bar)
echo   [X] Window is positioned for recording
echo   [X] Audio is MUTED (demo has text only)
echo   [X] You're ready to START RECORDING
echo.
echo ============================================================
echo.
pause
echo.
echo ============================================================
echo   Starting demo in 5 seconds...
echo   START YOUR SCREEN RECORDING NOW!
echo ============================================================
timeout /t 5
echo.

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Run the hackathon demo
python run_hackathon_demo.py

echo.
echo ============================================================
echo   Demo complete! STOP YOUR RECORDING NOW!
echo ============================================================
echo.
echo Next steps:
echo   1. Stop your screen recording
echo   2. Upload video to YouTube (public or unlisted)
echo   3. Copy the YouTube link
echo   4. Submit to hackathon at https://trddev.com/hackathon-2025/
echo.
echo Category: Post-event Analysis + Driver Training/Insights
echo Dataset: R2_barber_telemetry_data.csv
echo.
pause

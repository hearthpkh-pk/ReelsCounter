@echo off
title Page Monitor Dev Mode
echo Starting Page Monitor...
python main_monitor.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Program crashed. Please check the logs above.
    pause
)

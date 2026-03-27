@echo off
echo Installing dependencies for Page Monitor...
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Installation failed.
    pause
) else (
    echo.
    echo [SUCCESS] Dependencies installed! You can now run run_dev.bat
    pause
)

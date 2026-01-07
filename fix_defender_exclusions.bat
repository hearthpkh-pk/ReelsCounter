@echo off
echo ========================================
echo   เพิ่ม Windows Defender Exclusion
echo   สำหรับแก้ปัญหาเบราว์เซอร์ไม่เด้ง
echo ========================================
echo.
echo กำลังเพิ่มโฟลเดอร์และไฟล์ที่จำเป็นเข้า Exclusion List...
echo.

REM ตรวจสอบสิทธิ์ Administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ต้องรันในโหมด Administrator!
    echo กรุณาคลิกขวาที่ไฟล์นี้แล้วเลือก "Run as administrator"
    pause
    exit /b 1
)

REM เพิ่ม Chrome paths
echo [1/4] เพิ่ม Chrome Exclusions...
powershell -Command "Add-MpPreference -ExclusionPath 'C:\Program Files\Google\Chrome\Application\chrome.exe'" 2>nul
powershell -Command "Add-MpPreference -ExclusionPath 'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'" 2>nul
powershell -Command "Add-MpPreference -ExclusionPath '%LOCALAPPDATA%\Google\Chrome'" 2>nul

REM เพิ่ม Python/PyInstaller temp paths
echo [2/4] เพิ่ม Python Temp Exclusions...
powershell -Command "Add-MpPreference -ExclusionPath '%TEMP%'" 2>nul
powershell -Command "Add-MpPreference -ExclusionPath '%LOCALAPPDATA%\Temp'" 2>nul

REM เพิ่ม current directory
echo [3/4] เพิ่ม Current Directory...
powershell -Command "Add-MpPreference -ExclusionPath '%CD%'" 2>nul

REM เพิ่ม Chrome processes
echo [4/4] เพิ่ม Process Exclusions...
powershell -Command "Add-MpPreference -ExclusionProcess 'chrome.exe'" 2>nul
powershell -Command "Add-MpPreference -ExclusionProcess 'chromedriver.exe'" 2>nul

echo.
echo ========================================
echo   เพิ่ม Exclusions เสร็จสิ้น!
echo ========================================
echo.
echo หมายเหตุ: การเปลี่ยนแปลงจะมีผลทันที
echo ลองรันโปรแกรมใหม่อีกครั้ง
echo.
pause
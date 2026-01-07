@echo off
echo ========================================
echo   Reels Counter Pro - Browser Fix
echo ========================================
echo.
echo กำลังแก้ไขปัญหาเบราว์เซอร์ไม่เด้งใน exe...
echo.

REM ตรวจสอบและสร้าง registry entry สำหรับ Chrome
echo [1/3] ตรวจสอบ Chrome Registry...
reg query "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" >nul 2>&1
if %errorlevel% neq 0 (
    echo Chrome registry ไม่พบ - กำลังสร้าง...
    reg add "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" /ve /d "C:\Program Files\Google\Chrome\Application\chrome.exe" /f >nul 2>&1
    if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
        reg add "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" /ve /d "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" /f >nul 2>&1
    )
) else (
    echo Chrome registry พบแล้ว ✓
)

REM ตั้งค่า environment variables
echo [2/3] ตั้งค่า Environment Variables...
setx CHROME_LOG_FILE "NUL" >nul 2>&1
setx CHROME_DEVEL_SANDBOX "0" >nul 2>&1

REM ล้าง Chrome cache และ temp files
echo [3/3] ล้าง Chrome Cache...
taskkill /f /im chrome.exe >nul 2>&1
timeout /t 2 >nul
if exist "%LOCALAPPDATA%\Google\Chrome\User Data\Default\GPUCache" (
    rmdir /s /q "%LOCALAPPDATA%\Google\Chrome\User Data\Default\GPUCache" >nul 2>&1
)
if exist "%TEMP%\chrome_*" (
    del /q "%TEMP%\chrome_*" >nul 2>&1
)

echo.
echo ========================================
echo   แก้ไขเสร็จสิ้น!
echo ========================================
echo.
echo หากยังมีปัญหา ให้ลองวิธีนี้:
echo 1. รันโปรแกรมในโหมด Administrator
echo 2. ปิด Antivirus ชั่วคราว
echo 3. เพิ่ม Chrome และโปรแกรมใน Windows Defender Exclusion
echo.
pause
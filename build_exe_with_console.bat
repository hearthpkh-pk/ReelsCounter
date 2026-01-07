@echo off
set PYTHONUTF8=1

echo ======== 🔧 Starting ReelsCounterPro Build (WITH CONSOLE) ========

REM ล้างโฟลเดอร์เก่า
rd /s /q build 2>nul
rd /s /q dist 2>nul

echo 🔁 Compiling Python files to .pyd...
cythonize -i fb_engine.py ig_engine.py constants_fb.py constants_ig.py fb_video_engine.py browser_engine.py

echo 🚀 Building EXE with PyInstaller (WITH CONSOLE)...
pyinstaller --clean --onedir --console ^
--add-data "index.html;." ^
--add-data "script.js;." ^
--add-data "style.css;." ^
--add-data "Reels_Counter_Pro_LOGO_transparent.png;." ^
--icon=Reels_Counter_Pro_LOGO.ico ^
--name=ReelsCounterPro-Console ^
--hidden-import=fb_engine ^
--hidden-import=ig_engine ^
--hidden-import=browser_engine ^
--hidden-import=fb_video_engine ^
--hidden-import=constants_fb ^
--hidden-import=constants_ig ^
--hidden-import=webview ^
--hidden-import=selenium ^
--hidden-import=selenium.webdriver ^
--hidden-import=selenium.webdriver.chrome ^
--hidden-import=selenium.webdriver.chrome.service ^
--hidden-import=selenium.webdriver.common.by ^
--hidden-import=selenium.webdriver.support.ui ^
--hidden-import=selenium.webdriver.support.expected_conditions ^
--hidden-import=webdriver_manager ^
--hidden-import=webdriver_manager.chrome ^
--collect-submodules=selenium ^
--collect-submodules=webdriver_manager ^
main.py

echo 📁 Copying additional files to exe folder...
copy "fix_browser_issue.bat" "dist\ReelsCounterPro-Console\"
copy "fix_defender_exclusions.bat" "dist\ReelsCounterPro-Console\"
copy "add_defender_exclusion.bat" "dist\ReelsCounterPro-Console\"
copy "clear_cache.bat" "dist\ReelsCounterPro-Console\" 2>nul
copy "BROWSER_ISSUE_FIX.md" "dist\ReelsCounterPro-Console\"

REM Copy docs folder
xcopy "docs" "dist\ReelsCounterPro-Console\docs\" /E /I /Y 2>nul

echo ✅ DONE! Build finished.
echo 📦 EXE location: dist\ReelsCounterPro-Console\ReelsCounterPro-Console.exe
echo 💡 This version shows console for debugging
echo 📋 Files copied to exe folder:
echo   - fix_browser_issue.bat
echo   - fix_defender_exclusions.bat  
echo   - add_defender_exclusion.bat
echo   - BROWSER_ISSUE_FIX.md
echo   - docs\ folder
pause
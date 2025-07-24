@echo off
setlocal
set TARGET=%1
powershell -ExecutionPolicy Bypass -Command "Add-MpPreference -ExclusionPath '%TARGET%'"

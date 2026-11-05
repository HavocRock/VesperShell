@echo off
setlocal
cd /d "%~dp0"
echo VesperShell v0.3.5 private test - dummy notes only.
echo Test storage: %TEMP%\VesperShell-QA-v034
"%~dp0VesperShell.exe" --qa-mode --data-dir "%TEMP%\VesperShell-QA-v034"
if errorlevel 1 pause

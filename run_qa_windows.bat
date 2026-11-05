@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Please run install_windows.bat first.
  pause
  exit /b 1
)
echo QA mode: separate test storage in %%TEMP%%\VesperShell-QA-v034
".venv\Scripts\python.exe" main.py --qa-mode --data-dir "%TEMP%\VesperShell-QA-v034"
if errorlevel 1 pause

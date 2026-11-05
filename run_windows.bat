@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" main.py
) else (
  echo No local environment found. Run install_windows.bat first.
  pause
  exit /b 1
)
if errorlevel 1 (
  echo VesperShell could not start. Check the error above.
  pause
  exit /b 1
)

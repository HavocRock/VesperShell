@echo off
setlocal
cd /d "%~dp0"
echo =============================================
echo VesperShell v0.3.5 - Windows setup
echo =============================================
if not exist ".venv\Scripts\python.exe" (
  echo Creating private Python environment...
  py -3.13 -m venv ".venv" 2>nul
  if errorlevel 1 (
    echo Python 3.13 unavailable. Trying default Python 3...
    py -3 -m venv ".venv"
    if errorlevel 1 goto failed
  )
)
echo Installing PySide6 into the private environment...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo.
echo Setup complete. First use run_qa_windows.bat to test dummy notes.
echo Start normal mode separately only when ready to test Windows startup.
exit /b 0
:failed
echo.
echo Setup failed. Please check Python and your internet connection.
pause
exit /b 1

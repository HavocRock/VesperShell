@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run install_windows.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 goto failed
set "QT_QPA_PLATFORM=windows"
".venv\Scripts\python.exe" -m unittest discover -s tests -v
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean VesperShell.spec
if errorlevel 1 goto failed
copy /y "packaging\Start-QA.bat" "dist\VesperShell\Start-QA.bat" >nul
copy /y "WINDOWS_QA.md" "dist\VesperShell\WINDOWS_QA.md" >nul
copy /y "BUILD_WINDOWS.md" "dist\VesperShell\BUILD_WINDOWS.md" >nul
if not exist "dist\VesperShell\docs" mkdir "dist\VesperShell\docs"
copy /y "docs\VesperShell-Help.html" "dist\VesperShell\docs\VesperShell-Help.html" >nul || goto failed
copy /y "LICENSE" "dist\VesperShell\LICENSE" >nul || goto failed
copy /y "THIRD_PARTY_NOTICES.md" "dist\VesperShell\THIRD_PARTY_NOTICES.md" >nul || goto failed
copy /y "VesperShell-v0.3.5-QA-Offline.html" "dist\VesperShell\VesperShell-v0.3.5-QA-Offline.html" >nul
echo.
echo Windows app created: dist\VesperShell\VesperShell.exe
 echo Copy the ENTIRE dist\VesperShell folder to another computer.
pause
exit /b 0
:failed
echo Build failed. Check the error messages above.
pause
exit /b 1

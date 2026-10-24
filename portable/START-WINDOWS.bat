@echo off
title LabelVoice - Portable Label Reader (Windows)
cd /d "%~dp0"
echo ============================================
echo   LabelVoice - Smart Label Reader (Portable)
echo   Mobile version - no Python, no PyQt needed
echo ============================================
echo.
if not exist "server-windows.ps1" (
  echo [ERROR] server-windows.ps1 was not found next to this .bat file.
  echo         Please extract the ZIP completely and try again.
  pause
  exit /b 1
)
echo Starting the local server...
echo Your browser will open automatically.
echo Keep this window open while using the app.
echo.
where pwsh >nul 2>nul
if %errorlevel%==0 (
  pwsh -NoProfile -ExecutionPolicy Bypass -File "server-windows.ps1"
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "server-windows.ps1"
)
echo.
echo ============================================
echo  Server stopped.
echo  Alternative without a server (needs internet):
echo    double-click "index.html" (or "webapp\index.html" in the portable ZIP)
echo    or "label-reader-singlefile.html"
echo ============================================
pause


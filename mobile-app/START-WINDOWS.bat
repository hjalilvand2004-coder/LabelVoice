@echo off
title LabelVoice - Portable Label Reader (Windows)
cd /d "%~dp0"
echo ============================================
echo   LabelVoice - Smart Label Reader (Portable)
echo   Mobile version - no Python, no PyQt needed
echo.
set APPVER=
if exist VERSION.txt set /p APPVER=<VERSION.txt
if "%APPVER%"=="" set APPVER=unknown
echo   Folder version : v%APPVER%
echo   Latest release : github.com/hjalilvand2004-coder/LabelVoice/releases/latest
echo.
echo   If these do NOT match, this folder is an OLD
echo   copy (features like the OpenCV steps viewer
echo   will be missing). Download the new ZIP and
echo   extract it to a NEW folder, then start there.
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
echo  Alternative WITHOUT a server (fully offline):
echo    double-click "label-reader-singlefile.html"
echo    (single file, includes the local audio engine)
echo  NOTE: "index.html" opened directly from Explorer
echo  (file://) cannot load the local voice and camera
echo  models - use THIS server for them.
echo ============================================
pause


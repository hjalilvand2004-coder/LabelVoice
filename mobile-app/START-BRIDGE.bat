@echo off
chcp 65001 >nul
title LabelVoice - OCR Bridge (Desktop Engine Server) v2.5.0
cd /d "%~dp0.."
echo ============================================
echo   LabelVoice - OCR Bridge (v2.5.0)
echo   Read heavy engines on THIS computer for
echo   the web / mobile app (same Wi-Fi):
echo     EasyOCR - Surya - Qwen3-VL-2B-Instruct
echo ============================================
echo.

where python >nul 2>nul
if not %errorlevel%==0 (
  echo [ERROR] Python was not found in PATH.
  echo         Install Python 3.9+ from python.org and run again.
  pause
  exit /b 1
)

echo Starting the OCR bridge on port 8770 ...
echo - On this PC:      http://127.0.0.1:8770/ping
echo - From your phone: http://YOUR-PC-IP:8770/ping   (shown below)
echo.
echo Then in the web/mobile app: Engine selector -
echo pick "EasyOCR / Surya / Qwen3-VL (desktop bridge)",
echo enter this address, press "Check connection".
echo Keep this window open while using the app.
echo.
python -m label_reader.bridge --port 8770
echo.
echo Bridge stopped.
pause

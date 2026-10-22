@echo off
chcp 65001 >nul
title بُرچسب‌خوان هوشمند - نسخه موبایل
cd /d "%~dp0"
echo ============================================
echo   برچسب‌خوان هوشمند دارو و محصولات
echo   راه‌انداز بدون پایتون (ویندوز)
echo ============================================
where pwsh >nul 2>nul
if %errorlevel%==0 (
  pwsh -NoProfile -ExecutionPolicy Bypass -File "server-windows.ps1"
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "server-windows.ps1"
)
pause

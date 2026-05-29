@echo off
setlocal EnableExtensions

REM Software render launch. Only D:\ Weixin path.

set "EXE=D:\Program Files\Tencent\Weixin\Weixin.exe"

if not exist "%EXE%" (
  echo [ERROR] Not found: %EXE%
  pause
  exit /b 1
)

echo [1/2] Stopping Weixin...
taskkill /IM Weixin.exe /F >nul 2>&1
taskkill /IM WeChat.exe /F >nul 2>&1
timeout /t 2 /nobreak >nul

set "QT_OPENGL=software"
set "QT_ANGLE_PLATFORM=software"
set "QT_QUICK_BACKEND=software"

echo [2/2] Starting: %EXE%
echo   QT_OPENGL=%QT_OPENGL%
echo   QT_ANGLE_PLATFORM=%QT_ANGLE_PLATFORM%

start "" "%EXE%"

echo Done. After login run: python diagnose_wechat_ui.py
timeout /t 3 >nul
exit /b 0

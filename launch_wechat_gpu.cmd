@echo off
setlocal EnableExtensions

REM GPU/ANGLE launch. Only D:\ Weixin path.
REM Fully exit WeChat from tray before run (script also taskkills).

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

set "QT_OPENGL=angle"
set "QT_ANGLE_PLATFORM=d3d11"
set "QT_QUICK_BACKEND=opengl"
set "QSG_RHI_BACKEND=d3d11"

echo [2/2] Starting: %EXE%
echo   QT_OPENGL=%QT_OPENGL%
echo   QT_ANGLE_PLATFORM=%QT_ANGLE_PLATFORM%

REM Child process inherits env vars from this cmd session
start "" "%EXE%"

echo Done. After login run: python diagnose_wechat_ui.py
timeout /t 3 >nul
exit /b 0

@echo off
REM 倾向恢复 mmui::MainWindow + 完整 UIA 树（软件渲染）
REM 用法：先完全退出微信，再双击本脚本

set QT_OPENGL=software
set QT_ANGLE_PLATFORM=software
set QT_QUICK_BACKEND=software

set WECHAT1=C:\Program Files\Tencent\WeChat\WeChat.exe
set WECHAT2=C:\Program Files (x86)\Tencent\WeChat\WeChat.exe

if exist "%WECHAT1%" (
  start "" "%WECHAT1%"
  goto :done
)
if exist "%WECHAT2%" (
  start "" "%WECHAT2%"
  goto :done
)

echo 未找到 WeChat.exe，请修改本 bat 中的路径
pause
exit /b 1

:done
echo 已用软件渲染环境变量启动微信。请登录后运行: python diagnose_wechat_ui.py
timeout /t 3

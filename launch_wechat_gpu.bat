@echo off
REM 倾向 Qt51514QWindowIcon 画布模式（GPU/ANGLE，用于在公司机复现家里现象）
REM 用法：先完全退出微信，再双击本脚本

set QT_OPENGL=angle
set QT_ANGLE_PLATFORM=d3d11

REM 清掉可能存在的软件渲染变量（若你在系统环境变量里设过）
set QT_QUICK_BACKEND=

set WECHAT1=D:\Program Files\Tencent\Weixin\Weixin.exe
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
echo 已用 ANGLE/D3D11 环境变量启动微信。请登录后运行: python diagnose_wechat_ui.py
timeout /t 3

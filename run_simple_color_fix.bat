@echo off
echo === 简单彩色修复 ===
echo 直接修复摄像头彩色问题，不搞复杂测试
echo.

cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    echo 激活Python 3.11环境...
    call camer311\Scripts\activate.bat
) else (
    echo 使用系统Python环境...
)

echo 启动简单彩色修复...
python simple_color_fix.py

pause
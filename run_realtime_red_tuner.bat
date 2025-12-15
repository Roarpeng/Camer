@echo off
echo === 实时红色检测调参工具 ===
echo 可以动态调整HSV参数来找到最佳的红色检测范围
echo.

cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    echo 激活Python 3.11环境...
    call camer311\Scripts\activate.bat
) else (
    echo 使用系统Python环境...
)

echo 启动实时红色检测调参工具...
python realtime_red_tuner.py

pause
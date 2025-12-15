@echo off
echo === 强制彩色摄像头工具 ===
echo 尝试各种方法强制摄像头输出真正的彩色图像
echo.

cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    echo 激活Python 3.11环境...
    call camer311\Scripts\activate.bat
) else (
    echo 使用系统Python环境...
)

echo 启动强制彩色摄像头工具...
python force_color_camera.py

pause
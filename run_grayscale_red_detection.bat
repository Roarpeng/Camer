@echo off
echo === 灰度摄像头红色检测工具 ===
echo 专门针对只能输出灰度图像的摄像头进行红色光点检测
echo.

cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    echo 激活Python 3.11环境...
    call camer311\Scripts\activate.bat
) else (
    echo 使用系统Python环境...
)

echo 启动灰度摄像头红色检测工具...
python grayscale_red_detection.py

pause
@echo off
echo === 高亮度摄像头测试 ===
echo 专门用于解决摄像头图像过暗的问题
echo.

cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    echo 激活Python 3.11环境...
    call camer311\Scripts\activate.bat
) else (
    echo 使用系统Python环境...
)

echo 启动高亮度摄像头测试...
python bright_camera_test.py

pause
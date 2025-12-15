@echo off
echo === 快速摄像头测试 ===
echo 快速验证摄像头是否能正常工作
echo.

cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    echo 激活Python 3.11环境...
    call camer311\Scripts\activate.bat
) else (
    echo 使用系统Python环境...
)

echo 启动快速摄像头测试...
python quick_camera_test.py

pause
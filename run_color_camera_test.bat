@echo off
echo === 彩色摄像头测试工具 ===
echo 专门诊断摄像头彩色模式问题
echo.

cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    echo 激活Python 3.11环境...
    call camer311\Scripts\activate.bat
) else (
    echo 使用系统Python环境...
)

echo 启动彩色摄像头测试工具...
python color_camera_test.py

pause
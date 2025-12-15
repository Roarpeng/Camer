@echo off
echo === 摄像头诊断工具 ===
echo 检查摄像头是否正常工作，调整曝光和其他参数
echo.

cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    echo 激活Python 3.11环境...
    call camer311\Scripts\activate.bat
) else (
    echo 使用系统Python环境...
)

echo 启动摄像头诊断工具...
python camera_diagnostic.py

pause
@echo off
echo === 修复摄像头彩色模式工具 ===
echo 确保所有工具都使用正确的彩色模式和最佳配置
echo.

cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    echo 激活Python 3.11环境...
    call camer311\Scripts\activate.bat
) else (
    echo 使用系统Python环境...
)

echo 启动摄像头彩色模式修复工具...
python fix_camera_color_mode.py

pause
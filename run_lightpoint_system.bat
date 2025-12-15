@echo off
echo === 基于光点的检测系统 ===
echo.

cd /d "%~dp0"

if not exist "camer311\Scripts\python.exe" (
    echo [ERROR] 虚拟环境不存在，请先运行 activate_env311.bat
    pause
    exit /b 1
)

if not exist "mask.png" (
    echo [ERROR] 未找到mask文件 mask.png
    echo 请确保mask.png文件存在于当前目录
    pause
    exit /b 1
)

echo [INFO] 启动基于光点的检测系统...
echo [INFO] 将mask中的每个白色连通区域识别为一个独立的光点
echo [INFO] 只检测红色光点的出现和消失
echo [INFO] 按 Ctrl+C 停止系统
echo.

camer311\Scripts\python.exe mask_lightpoint_detection_system.py

echo.
echo [INFO] 系统已停止
pause
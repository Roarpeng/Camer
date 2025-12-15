@echo off
echo === 基于mask.png的1080p红色光点检测系统 ===
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

echo [INFO] 启动基于mask.png的1080p检测系统...
echo [INFO] 系统将监控mask白色区域内的红色光点变化
echo [INFO] 基线采集时只采集白色区域内的红色光点
echo [INFO] 按 Ctrl+C 停止系统
echo.

camer311\Scripts\python.exe mask_1080p_detection_system.py

echo.
echo [INFO] 系统已停止
pause
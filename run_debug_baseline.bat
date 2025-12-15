@echo off
echo === 基线检测调试工具 ===
echo.

cd /d "%~dp0"

if not exist "camer311\Scripts\python.exe" (
    echo [ERROR] 虚拟环境不存在，请先运行 activate_env311.bat
    pause
    exit /b 1
)

if not exist "mask.png" (
    echo [ERROR] 未找到mask文件 mask.png
    pause
    exit /b 1
)

echo [INFO] 启动基线检测调试工具...
echo [INFO] 专门用于诊断生产环境系统基线建立问题
echo [INFO] 将输出详细的调试信息和保存调试图像
echo.

camer311\Scripts\python.exe debug_baseline_detection.py

echo.
echo [INFO] 调试完成，请查看 baseline_debug.log 文件
pause
@echo off
echo === Mask系统功能验证 ===
echo.

cd /d "%~dp0"

if not exist "camer311\Scripts\python.exe" (
    echo [ERROR] 虚拟环境不存在，请先运行 activate_env311.bat
    pause
    exit /b 1
)

echo [INFO] 开始验证mask系统功能...
echo [INFO] 检查所有组件是否正常工作
echo.

camer311\Scripts\python.exe verify_mask_system.py

echo.
pause
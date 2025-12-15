@echo off
echo === Mask对齐测试 ===
echo.

cd /d "%~dp0"

if not exist "camer311\Scripts\python.exe" (
    echo [ERROR] 虚拟环境不存在，请先运行 activate_env311.bat
    pause
    exit /b 1
)

echo [INFO] 启动mask对齐测试...
echo.

camer311\Scripts\python.exe test_mask_alignment.py

echo.
echo [INFO] 测试完成
pause
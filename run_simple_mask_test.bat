@echo off
echo === 简化Mask检测测试 ===
echo.

cd /d "%~dp0"

if not exist "camer311\Scripts\python.exe" (
    echo [ERROR] 虚拟环境不存在，请先运行 activate_env311.bat
    pause
    exit /b 1
)

if not exist "m.png" (
    echo [ERROR] 未找到mask文件 m.png
    pause
    exit /b 1
)

echo [INFO] 启动简化mask检测测试...
echo [INFO] 不需要MQTT连接，直接测试颜色变化检测
echo.

camer311\Scripts\python.exe test_mask_detection_simple.py

echo.
echo [INFO] 测试完成
pause
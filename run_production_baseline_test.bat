@echo off
echo === 生产环境基线测试 ===
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

echo [INFO] 启动生产环境基线测试...
echo [INFO] 模拟完整的MQTT触发和基线建立过程
echo [INFO] 与生产环境系统使用完全相同的逻辑
echo.

camer311\Scripts\python.exe test_production_baseline.py

echo.
echo [INFO] 测试完成，详细日志保存在 production_baseline_test.log
pause
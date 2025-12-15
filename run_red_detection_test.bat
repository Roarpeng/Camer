@echo off
echo === 红色检测测试工具 ===
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

echo [INFO] 启动红色检测测试工具...
echo [INFO] 测试当前红色检测参数是否能检测到红色光点
echo.
echo 控制说明:
echo   SPACE - 测试当前帧的红色检测
echo   Q - 退出
echo.

camer311\Scripts\python.exe test_red_detection.py

echo.
echo [INFO] 测试完成
pause
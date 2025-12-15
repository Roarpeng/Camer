@echo off
echo === 红色检测参数调试工具 ===
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

echo [INFO] 启动红色检测参数调试工具...
echo [INFO] 实时调整HSV参数和红色比例阈值
echo [INFO] 使用滑条调整参数，观察红色光点检测效果
echo.
echo 控制说明:
echo   S - 保存参数到文件
echo   R - 重置为默认值
echo   Q - 退出
echo.

camer311\Scripts\python.exe red_detection_tuner.py

echo.
echo [INFO] 调试工具已关闭
pause
@echo off
echo === 光点可视化工具 ===
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

echo [INFO] 启动光点可视化工具...
echo [INFO] 显示mask中识别的光点区域和红色检测效果
echo.
echo 控制说明:
echo   SPACE - 建立基线 (采集红色光点)
echo   R - 重置基线
echo   M - 切换显示模式
echo     0: 光点轮廓
echo     1: 光点编号
echo     2: 红色检测
echo     3: 变化对比
echo   Q - 退出
echo.

camer311\Scripts\python.exe lightpoint_visualizer.py

echo.
echo [INFO] 可视化工具已关闭
pause
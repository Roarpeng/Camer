@echo off
echo === Mask对齐可视化工具 ===
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

echo [INFO] 启动mask对齐可视化工具...
echo [INFO] 实时显示摄像头画面和mask.png的对齐情况
echo [INFO] 调试阶段用于验证mask区域和红色光点检测
echo.
echo 控制说明:
echo   SPACE - 建立基线 (采集mask区域内红色光点)
echo   R - 重置基线
echo   M - 切换显示模式
echo   Q - 退出
echo.

camer311\Scripts\python.exe mask_alignment_visualizer.py

echo.
echo [INFO] 可视化工具已关闭
pause
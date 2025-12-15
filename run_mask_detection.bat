@echo off
echo === 基于mask的颜色变化检测系统 ===
echo.

cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    echo 激活Python 3.11环境...
    call camer311\Scripts\activate.bat
) else (
    echo 警告: 未找到Python 3.11环境，使用系统Python
)

echo 检查mask文件...
if not exist "m.png" (
    echo [ERROR] 未找到mask文件 m.png
    echo 请确保mask文件存在于当前目录
    pause
    exit /b 1
)

echo [OK] 找到mask文件 m.png
echo.
echo 启动基于mask的检测系统...
echo 监控mask区域内红色光点的颜色变化
echo.
python mask_based_detection_system.py

echo.
echo 系统已停止，按任意键退出...
pause > nul
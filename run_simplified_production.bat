@echo off
echo === 简化生产环境系统 ===
echo 消除线程和时序问题的生产系统
echo.

cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    echo 激活Python 3.11环境...
    call camer311\Scripts\activate.bat
) else (
    echo 使用系统Python环境...
)

echo 启动简化生产系统...
python simplified_production_system.py

pause
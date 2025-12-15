@echo off
echo === 红色检测分析器 ===
echo 分析红色检测算法问题
echo.

cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    echo 激活Python 3.11环境...
    call camer311\Scripts\activate.bat
) else (
    echo 使用系统Python环境...
)

echo 启动红色检测分析器...
python red_detection_analyzer.py

pause
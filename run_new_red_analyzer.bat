@echo off
echo === 新的红色检测分析器 ===
echo 完全不设置摄像头参数，用PC默认亮度
echo.

cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    call camer311\Scripts\activate.bat
)

python new_red_analyzer.py

pause
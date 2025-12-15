@echo off
echo === 快速红光检测测试 ===
echo.

cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    echo 激活Python 3.11环境...
    call camer311\Scripts\activate.bat
) else (
    echo 警告: 未找到Python 3.11环境，使用系统Python
)

echo 开始快速检测测试...
python quick_detection_test.py

echo.
echo 测试完成，按任意键退出...
pause > nul
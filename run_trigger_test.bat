@echo off
echo === 触发阈值逻辑测试 ===
echo.

cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    echo 激活Python 3.11环境...
    call camer311\Scripts\activate.bat
) else (
    echo 警告: 未找到Python 3.11环境，使用系统Python
)

echo 测试触发阈值逻辑...
python test_trigger_threshold.py

echo.
echo 测试完成，按任意键退出...
pause > nul
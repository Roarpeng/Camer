@echo off
echo === 综合基线测试 ===
echo 比较不同方法的基线建立效果
echo.

cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    echo 激活Python 3.11环境...
    call camer311\Scripts\activate.bat
) else (
    echo 使用系统Python环境...
)

echo 启动综合基线测试...
python comprehensive_baseline_test.py

pause
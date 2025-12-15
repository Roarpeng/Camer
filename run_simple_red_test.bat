@echo off
echo === 简单红色检测测试 ===
echo 使用最基本的方法检测红色
echo.

cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    echo 激活Python 3.11环境...
    call camer311\Scripts\activate.bat
) else (
    echo 使用系统Python环境...
)

echo 启动简单红色检测测试...
python simple_red_test.py

pause
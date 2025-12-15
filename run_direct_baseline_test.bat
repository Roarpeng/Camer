@echo off
echo === 直接基线测试 ===
echo 绕过MQTT，直接测试基线建立功能
echo.

cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    echo 激活Python 3.11环境...
    call camer311\Scripts\activate.bat
) else (
    echo 使用系统Python环境...
)

echo 启动直接基线测试...
python direct_baseline_test.py

pause
@echo off
echo === 最终生产系统 ===
echo 在成功的红色检测基础上加入MQTT逻辑
echo.

cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    echo 激活Python 3.11环境...
    call camer311\Scripts\activate.bat
) else (
    echo 使用系统Python环境...
)

echo 启动最终生产系统...
python final_production_system.py

pause
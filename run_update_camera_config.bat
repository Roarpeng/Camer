@echo off
echo === 摄像头配置更新工具 ===
echo 根据测试结果更新系统配置
echo.

cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    echo 激活Python 3.11环境...
    call camer311\Scripts\activate.bat
) else (
    echo 使用系统Python环境...
)

echo 启动摄像头配置更新工具...
python update_camera_config.py

pause
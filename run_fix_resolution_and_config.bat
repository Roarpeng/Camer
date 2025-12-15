@echo off
echo === 分辨率和配置修复工具 ===
echo 一次性修复所有系统的分辨率和摄像头配置问题
echo.

cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    echo 激活Python 3.11环境...
    call camer311\Scripts\activate.bat
) else (
    echo 使用系统Python环境...
)

echo 启动分辨率和配置修复工具...
python fix_resolution_and_config.py

pause
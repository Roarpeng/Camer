@echo off
echo === Mask分辨率转换工具 ===
echo 将1080p的mask转换为640x480分辨率
echo.

cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    echo 激活Python 3.11环境...
    call camer311\Scripts\activate.bat
) else (
    echo 使用系统Python环境...
)

echo 启动Mask分辨率转换工具...
python convert_mask_resolution.py

pause
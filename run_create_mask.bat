@echo off
echo === 创建光点区域mask底图 ===
echo.

cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    echo 激活Python 3.11环境...
    call camer311\Scripts\activate.bat
) else (
    echo 警告: 未找到Python 3.11环境，使用系统Python
)

echo 启动光点mask创建工具...
echo 请将图片文件放在当前目录
echo.
python create_light_mask.py

echo.
echo 处理完成，按任意键退出...
pause > nul
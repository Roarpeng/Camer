@echo off
echo === 高级光点区域mask创建工具 ===
echo.

cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    echo 激活Python 3.11环境...
    call camer311\Scripts\activate.bat
) else (
    echo 警告: 未找到Python 3.11环境，使用系统Python
)

echo 启动高级mask创建工具...
echo 支持交互式参数调整和批量处理
echo.
python advanced_mask_creator.py

echo.
echo 处理完成，按任意键退出...
pause > nul
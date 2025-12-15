@echo off
echo === 快速mask调参工具 ===
echo.

cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    echo 激活Python 3.11环境...
    call camer311\Scripts\activate.bat
) else (
    echo 警告: 未找到Python 3.11环境，使用系统Python
)

echo 启动快速调参工具...
echo 简化界面，专注核心参数调整
echo.
python quick_mask_tuner.py

echo.
echo 调参完成，按任意键退出...
pause > nul
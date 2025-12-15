@echo off
echo === 启动最终生产系统 (带视觉显示) ===
echo.

REM 激活虚拟环境
call .\camer311\Scripts\activate.bat

REM 运行系统 (带视觉显示)
python final_production_system.py --view

pause
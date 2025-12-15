@echo off
echo === Mask黑化效果测试 ===
echo.

cd /d "%~dp0"

if not exist "camer311\Scripts\python.exe" (
    echo [ERROR] 虚拟环境不存在，请先运行 activate_env311.bat
    pause
    exit /b 1
)

if not exist "mask.png" (
    echo [ERROR] 未找到mask文件 mask.png
    pause
    exit /b 1
)

echo [INFO] 启动mask黑化效果测试...
echo [INFO] 验证非白色区域是否正确黑化
echo.
echo 控制说明:
echo   1 - 原图
echo   2 - 黑化mask叠加
echo   3 - 半透明mask叠加
echo   Q - 退出
echo.

camer311\Scripts\python.exe test_mask_blackout.py

echo.
echo [INFO] 测试完成
pause
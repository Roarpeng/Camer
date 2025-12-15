@echo off
echo === 平衡红光检测测试 ===
echo.

cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    echo 激活Python 3.11环境...
    call camer311\Scripts\activate.bat
) else (
    echo 警告: 未找到Python 3.11环境，使用系统Python
)

echo 开始平衡红光检测测试...
echo 实时显示检测效果，绿色框标记红光
echo 减少误检，提高检测精度
echo 按 'q' 退出，按 's' 保存帧
echo.
python ultra_sensitive_test.py

echo.
echo 测试完成，按任意键退出...
pause > nul
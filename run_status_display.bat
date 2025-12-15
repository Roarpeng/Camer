@echo off
echo === 检测状态显示系统 ===
echo 实时显示红光检测结果，不显示摄像头画面
echo 显示每个摄像头的红光数量和面积
echo.

call camer311\Scripts\activate.bat

echo 环境已激活，启动检测状态显示...
echo 系统将实时更新检测结果
echo 按 Ctrl+C 可以退出程序
echo.

python detection_status_display.py

echo.
echo 系统已停止，按任意键退出...
pause > nul
@echo off
echo === 检测逻辑测试 ===
echo 测试红光检测和面积比较逻辑
echo.

call camer311\Scripts\activate.bat

echo 环境已激活，开始检测逻辑测试...
echo 可以测试单个摄像头或所有摄像头
echo.

python test_detection_logic.py

echo.
echo 测试完成，按任意键退出...
pause > nul
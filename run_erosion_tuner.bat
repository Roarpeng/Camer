@echo off
echo === 摄像头腐蚀参数调试工具 ===
echo 逐个调试6个摄像头的腐蚀参数
echo 调试完成后自动保存到配置文件
echo.

call camer311\Scripts\activate.bat

echo 环境已激活，开始腐蚀参数调试...
echo 控制说明:
echo   1/2 - 调整腐蚀核大小
echo   3/4 - 调整腐蚀迭代次数
echo   a/z - 调整HSV下限H值
echo   w/x - 调整HSV下限S值
echo   e/c - 调整HSV下限V值
echo   r/v - 调整HSV上限H值
echo   s - 保存当前设置
echo   n - 下一个摄像头
echo   q - 退出
echo.

python camera_erosion_tuner.py

echo.
echo 调试完成，按任意键退出...
pause > nul
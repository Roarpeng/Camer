@echo off
echo === 红光检测系统 ===
echo 纯检测模式，不显示画面
echo 监控红光面积变化，触发MQTT消息
echo.

call camer311\Scripts\activate.bat

echo 环境已激活，启动红光检测系统...
echo 系统将等待changeState MQTT触发
echo 检测到面积变化10%%时发送trigger消息
echo 按 Ctrl+C 可以退出程序
echo.

python red_light_detection_system.py

echo.
echo 系统已停止，按任意键退出...
pause > nul
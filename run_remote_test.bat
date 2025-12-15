@echo off
echo ========================================
echo MQTT摄像头监控系统 - 远程测试
echo ========================================
echo.

echo 激活虚拟环境...
call camer311\Scripts\activate

echo.
echo 开始快速测试...
python quick_test.py

echo.
echo 测试完成！
echo 请查看生成的测试报告文件：
echo - quick_test_report.txt
echo - validation_report.txt (如果生成)
echo.

pause
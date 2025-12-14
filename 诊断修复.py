#!/usr/bin/env python3
"""
MQTT摄像头监控系统诊断和修复工具

解决常见问题：
- 只显示一个黑色视窗
- 摄像头无法初始化
- 参数配置问题
"""

import sys
import os
import cv2
import numpy as np
import logging
from typing import List, Dict, Any


def check_opencv_installation():
    """检查OpenCV安装和摄像头支持"""
    print("🔍 检查OpenCV安装...")
    
    try:
        print(f"   OpenCV版本: {cv2.__version__}")
        
        # 检查摄像头支持
        print("   检查摄像头支持...")
        
        available_cameras = []
        for i in range(10):  # 检查前10个摄像头索引
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    available_cameras.append(i)
                    print(f"   ✓ 摄像头 {i}: 可用 ({frame.shape[1]}x{frame.shape[0]})")
                else:
                    print(f"   ⚠️  摄像头 {i}: 已连接但无法读取画面")
                cap.release()
            else:
                if i < 6:  # 只对前6个显示未找到信息
                    print(f"   ✗ 摄像头 {i}: 未找到")
        
        print(f"   总计找到 {len(available_cameras)} 个可用摄像头")
        return available_cameras
        
    except Exception as e:
        print(f"   ❌ OpenCV检查失败: {e}")
        return []


def test_single_camera_window():
    """测试单个摄像头视窗"""
    print("\n🎥 测试单个摄像头视窗...")
    
    try:
        # 尝试打开第一个摄像头
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("   ❌ 无法打开摄像头0，尝试使用模拟画面")
            cap = None
        
        # 创建测试窗口
        window_name = "测试摄像头视窗"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 640, 480)
        
        print("   ✓ 测试窗口已创建")
        print("   按任意键继续，按 'q' 退出测试")
        
        frame_count = 0
        while True:
            if cap and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    frame = create_test_frame(0)
            else:
                frame = create_test_frame(0)
            
            # 添加测试信息
            cv2.putText(frame, f"Test Frame {frame_count}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, "Press 'q' to quit", (10, frame.shape[0] - 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
            
            cv2.imshow(window_name, frame)
            
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                break
            
            frame_count += 1
        
        if cap:
            cap.release()
        cv2.destroyAllWindows()
        
        print("   ✅ 单个摄像头视窗测试完成")
        return True
        
    except Exception as e:
        print(f"   ❌ 单个摄像头测试失败: {e}")
        return False


def test_multiple_windows():
    """测试6个独立视窗"""
    print("\n🎥 测试6个独立视窗...")
    
    try:
        windows = []
        caps = []
        
        # 创建6个窗口
        for i in range(6):
            window_name = f"摄像头 {i}"
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, 320, 240)
            
            # 排列窗口
            col = i % 3
            row = i // 3
            x = col * 330
            y = row * 270
            cv2.moveWindow(window_name, x, y)
            
            windows.append(window_name)
            
            # 尝试打开摄像头
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                caps.append(cap)
                print(f"   ✓ 摄像头 {i}: 已连接")
            else:
                caps.append(None)
                print(f"   ⚠️  摄像头 {i}: 使用模拟画面")
        
        print("   ✓ 6个视窗已创建")
        print("   按任意键继续，按 'q' 退出测试")
        
        frame_count = 0
        while True:
            for i in range(6):
                # 获取画面
                if caps[i] and caps[i].isOpened():
                    ret, frame = caps[i].read()
                    if not ret:
                        frame = create_test_frame(i)
                else:
                    frame = create_test_frame(i)
                
                # 调整画面大小
                frame = cv2.resize(frame, (320, 240))
                
                # 添加信息
                cv2.putText(frame, f"Camera {i}", (10, 25), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame, f"Frame {frame_count}", (10, 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                
                cv2.imshow(windows[i], frame)
            
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                break
            
            frame_count += 1
        
        # 清理资源
        for cap in caps:
            if cap:
                cap.release()
        cv2.destroyAllWindows()
        
        print("   ✅ 6个独立视窗测试完成")
        return True
        
    except Exception as e:
        print(f"   ❌ 多视窗测试失败: {e}")
        return False


def create_test_frame(camera_id: int, width: int = 640, height: int = 480) -> np.ndarray:
    """创建测试画面"""
    # 创建彩色背景
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    
    # 不同摄像头使用不同颜色
    colors = [
        (100, 50, 50),   # 蓝色调
        (50, 100, 50),   # 绿色调
        (50, 50, 100),   # 红色调
        (100, 100, 50),  # 青色调
        (100, 50, 100),  # 紫色调
        (50, 100, 100)   # 黄色调
    ]
    
    color = colors[camera_id % len(colors)]
    frame[:] = color
    
    # 添加渐变效果
    for y in range(height):
        intensity = int(50 + (y / height) * 100)
        frame[y, :] = [c * intensity // 100 for c in color]
    
    # 添加摄像头标识
    cv2.putText(frame, f"Test Camera {camera_id}", (50, height//2), 
               cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
    
    # 添加一些图形
    cv2.rectangle(frame, (50, 50), (150, 150), (255, 255, 255), 2)
    cv2.circle(frame, (width-100, 100), 50, (255, 255, 255), 2)
    
    return frame


def check_system_resources():
    """检查系统资源"""
    print("\n💻 检查系统资源...")
    
    try:
        import psutil
        
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        print(f"   CPU使用率: {cpu_percent}%")
        
        # 内存使用率
        memory = psutil.virtual_memory()
        print(f"   内存使用率: {memory.percent}% ({memory.used//1024//1024}MB/{memory.total//1024//1024}MB)")
        
        # 磁盘空间
        disk = psutil.disk_usage('.')
        print(f"   磁盘使用率: {disk.percent}% ({disk.used//1024//1024//1024}GB/{disk.total//1024//1024//1024}GB)")
        
        return True
        
    except ImportError:
        print("   ⚠️  psutil未安装，无法检查系统资源")
        print("   安装命令: pip install psutil")
        return False
    except Exception as e:
        print(f"   ❌ 系统资源检查失败: {e}")
        return False


def generate_diagnostic_report():
    """生成诊断报告"""
    print("\n📋 生成诊断报告...")
    
    report = []
    report.append("# MQTT摄像头监控系统诊断报告")
    report.append(f"生成时间: {__import__('datetime').datetime.now()}")
    report.append("")
    
    # OpenCV信息
    try:
        report.append(f"OpenCV版本: {cv2.__version__}")
    except:
        report.append("OpenCV版本: 未安装或无法检测")
    
    # Python信息
    report.append(f"Python版本: {sys.version}")
    report.append(f"操作系统: {os.name}")
    
    # 摄像头检测
    available_cameras = check_opencv_installation()
    report.append(f"可用摄像头数量: {len(available_cameras)}")
    report.append(f"摄像头索引: {available_cameras}")
    
    # 保存报告
    report_file = "diagnostic_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    print(f"   ✅ 诊断报告已保存到: {report_file}")


def main():
    """主诊断函数"""
    print("🔧 MQTT摄像头监控系统诊断工具")
    print("=" * 50)
    
    # 检查OpenCV和摄像头
    available_cameras = check_opencv_installation()
    
    # 检查系统资源
    check_system_resources()
    
    # 生成诊断报告
    generate_diagnostic_report()
    
    print("\n🧪 开始功能测试...")
    
    # 询问用户是否进行测试
    while True:
        choice = input("\n选择测试项目:\n1. 单个摄像头视窗测试\n2. 6个独立视窗测试\n3. 跳过测试\n请选择 (1-3): ").strip()
        
        if choice == '1':
            test_single_camera_window()
            break
        elif choice == '2':
            test_multiple_windows()
            break
        elif choice == '3':
            print("跳过功能测试")
            break
        else:
            print("无效选择，请重新输入")
    
    print("\n📋 诊断建议:")
    
    if len(available_cameras) == 0:
        print("❌ 未检测到可用摄像头")
        print("   建议:")
        print("   - 检查USB摄像头连接")
        print("   - 确认摄像头驱动已安装")
        print("   - 尝试在其他软件中测试摄像头")
    elif len(available_cameras) < 6:
        print(f"⚠️  只检测到{len(available_cameras)}个摄像头，需要6个")
        print("   建议:")
        print("   - 连接更多USB摄像头")
        print("   - 检查USB端口和集线器")
        print("   - 确认所有摄像头都正常工作")
    else:
        print("✅ 摄像头检测正常")
    
    print("\n如果问题仍然存在，请:")
    print("1. 查看生成的诊断报告")
    print("2. 检查config.yaml配置文件")
    print("3. 运行 python test_enhanced_monitor.py 进行完整测试")
    print("4. 使用 python 启动增强监控.py 启动增强版系统")


if __name__ == "__main__":
    main()
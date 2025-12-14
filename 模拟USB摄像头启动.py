#!/usr/bin/env python3
"""
模拟USB摄像头启动脚本

在真实USB摄像头连接之前，使用模拟画面测试系统
- 跳过笔记本内置摄像头（摄像头0）
- 模拟6个USB摄像头（摄像头1-6）
- 完整的控制面板和日志系统
"""

import sys
import time
import numpy as np
import cv2
from mqtt_camera_monitoring.config import VisualMonitorConfig
from mqtt_camera_monitoring.visual_monitor import EnhancedVisualMonitor
from mqtt_camera_monitoring.camera_manager import CameraFrame
from mqtt_camera_monitoring.light_detector import RedLightDetection

# USB摄像头配置 - 跳过摄像头0（内置摄像头）
USB_CAMERA_IDS = [1, 2, 3, 4, 5, 6]  # 模拟的USB摄像头ID
TOTAL_CAMERAS = 6

def create_usb_simulation_frame(usb_camera_id: int, width: int = 640, height: int = 480) -> np.ndarray:
    """创建模拟USB摄像头画面"""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    
    # 不同USB摄像头使用不同的颜色主题
    color_themes = {
        1: (120, 80, 60),   # 棕色调 - USB摄像头1
        2: (60, 120, 80),   # 绿色调 - USB摄像头2
        3: (80, 60, 120),   # 紫色调 - USB摄像头3
        4: (120, 120, 60),  # 黄色调 - USB摄像头4
        5: (120, 60, 120),  # 粉色调 - USB摄像头5
        6: (60, 120, 120)   # 青色调 - USB摄像头6
    }
    
    base_color = color_themes.get(usb_camera_id, (100, 100, 100))
    
    # 创建渐变背景
    for y in range(height):
        intensity = int(50 + (y / height) * 150)
        frame[y, :] = [c * intensity // 150 for c in base_color]
    
    # 添加USB摄像头标识
    cv2.putText(frame, f"USB Camera {usb_camera_id}", (50, 80), 
               cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
    
    # 添加模拟状态
    cv2.putText(frame, "SIMULATED", (50, 120), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    
    # 添加设备信息
    cv2.putText(frame, f"External USB Device", (50, 160), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    
    # 添加分辨率信息
    cv2.putText(frame, f"Resolution: {width}x{height}", (50, 180), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    # 添加时间戳
    timestamp = time.strftime("%H:%M:%S")
    cv2.putText(frame, timestamp, (10, height - 40), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    # 添加帧计数
    frame_count = int(time.time()) % 1000
    cv2.putText(frame, f"Frame: {frame_count}", (10, height - 20), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    # 添加模拟的红色检测区域
    if usb_camera_id % 2 == 0:  # 偶数USB摄像头有红色区域
        # 红色矩形
        cv2.rectangle(frame, (width - 200, 100), (width - 150, 150), (0, 0, 255), -1)
        cv2.putText(frame, "RED", (width - 195, 130), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # 红色圆形
        cv2.circle(frame, (width - 100, 200), 25, (0, 0, 255), -1)
        cv2.putText(frame, "RED", (width - 115, 205), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
    # 添加USB连接状态指示
    cv2.rectangle(frame, (10, 10), (30, 30), (0, 255, 0), -1)
    cv2.putText(frame, "USB", (35, 25), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
    
    return frame

def create_test_detection(usb_camera_id: int) -> RedLightDetection:
    """创建模拟检测结果"""
    if usb_camera_id % 2 == 0:  # 偶数USB摄像头有检测结果
        return RedLightDetection(
            count=2,
            total_area=1200.0 + usb_camera_id * 150,
            bounding_boxes=[
                (440, 100, 50, 50),  # 红色矩形
                (540, 175, 50, 50)   # 红色圆形
            ],
            contours=[],
            timestamp=time.time()
        )
    else:
        return RedLightDetection(
            count=0,
            total_area=0.0,
            bounding_boxes=[],
            contours=[],
            timestamp=time.time()
        )

def main():
    """主启动函数"""
    print("🎥 模拟USB摄像头监控系统")
    print("=" * 60)
    print("系统配置:")
    print("✅ 跳过笔记本内置摄像头（摄像头0）")
    print("✅ 模拟6个外接USB摄像头（摄像头1-6）")
    print("✅ 完整的控制面板和日志系统")
    print("✅ 每个USB摄像头独立参数配置")
    print()
    
    try:
        # 创建配置
        print("1️⃣ 创建系统配置...")
        visual_config = VisualMonitorConfig(
            window_width=400,
            window_height=300,
            show_detection_boxes=True,
            box_color=[0, 255, 0],
            box_thickness=2
        )
        print("✅ 配置创建成功")
        
        # 创建监控器
        print("\n2️⃣ 创建USB摄像头监控器...")
        monitor = EnhancedVisualMonitor(visual_config, camera_count=TOTAL_CAMERAS)
        print("✅ 监控器创建成功")
        
        # 创建窗口
        print("\n3️⃣ 创建6个USB摄像头窗口...")
        success = monitor.create_windows()
        if not success:
            print("❌ 窗口创建失败！")
            return
        
        print("✅ 6个USB摄像头窗口创建成功！")
        
        # 显示窗口布局信息
        print(f"\n🖼️ USB摄像头窗口布局 (3×2网格):")
        for i, usb_id in enumerate(USB_CAMERA_IDS):
            row = i // 3
            col = i % 3
            color_names = ["棕色", "绿色", "紫色", "黄色", "粉色", "青色"]
            print(f"   位置({row},{col}) - USB摄像头{usb_id}: 模拟画面 ({color_names[i]}调)")
        
        print(f"\n🎛️ 控制面板:")
        print("   - 右侧显示控制面板窗口")
        print("   - 6个USB摄像头的参数调整滑块")
        print("   - 实时系统日志显示")
        print("   - 系统状态监控")
        
        print(f"\n🎯 功能演示:")
        print("   - 偶数USB摄像头显示红色检测区域")
        print("   - 实时更新时间戳和帧计数")
        print("   - 模拟红光检测和基线建立")
        print("   - 按 'q' 键退出系统")
        print()
        
        # 等待GUI启动
        time.sleep(2)
        
        # 添加初始日志
        monitor.add_log_entry("INFO", "模拟USB摄像头系统启动")
        monitor.add_log_entry("INFO", "跳过内置摄像头，使用USB摄像头1-6")
        monitor.add_log_entry("INFO", "创建了6个USB摄像头模拟窗口")
        
        # 主循环
        frame_count = 0
        baseline_set = False
        
        print("🔄 开始USB摄像头监控循环...")
        
        while True:
            try:
                # 创建帧数据
                frames = []
                detection_results = []
                
                for i, usb_camera_id in enumerate(USB_CAMERA_IDS):
                    # 创建模拟USB摄像头画面
                    frame_data = create_usb_simulation_frame(usb_camera_id)
                    
                    # 创建CameraFrame对象（使用项目中的摄像头ID 0-5）
                    camera_frame = CameraFrame(
                        camera_id=i,  # 项目中的摄像头ID
                        frame=frame_data,
                        timestamp=time.time(),
                        is_valid=True
                    )
                    frames.append(camera_frame)
                    
                    # 创建检测结果
                    detection = create_test_detection(usb_camera_id)
                    detection_results.append(detection)
                    
                    # 更新检测数据
                    if not baseline_set and frame_count > 30:
                        baseline_count = detection.count
                        baseline_area = detection.total_area
                        monitor.update_camera_detection_data(
                            i, baseline_count, baseline_area, 
                            baseline_count, baseline_area
                        )
                        if i == TOTAL_CAMERAS - 1:
                            baseline_set = True
                            monitor.add_log_entry("INFO", "所有USB摄像头基线已建立")
                            print("✅ USB摄像头基线建立完成")
                    elif baseline_set:
                        # 模拟检测变化
                        current_count = detection.count
                        current_area = detection.total_area
                        
                        # 每150帧模拟一次变化
                        if frame_count % 150 == 0 and i == 0:
                            current_count = max(0, current_count - 1)
                            current_area *= 0.7
                            monitor.add_log_entry("WARNING", f"USB摄像头{USB_CAMERA_IDS[i]}检测到红光变化", i)
                            print(f"⚠️  USB摄像头{USB_CAMERA_IDS[i]}检测到变化")
                        
                        monitor.update_camera_detection_data(
                            i, detection.count, detection.total_area,
                            current_count, current_area
                        )
                
                # 更新显示
                monitor.update_display(frames, detection_results)
                
                # 检查退出
                key = cv2.waitKey(30) & 0xFF
                if key == ord('q'):
                    print("用户请求退出")
                    break
                
                frame_count += 1
                
                # 定期输出状态
                if frame_count % 90 == 0:  # 每3秒
                    print(f"🔄 USB摄像头系统运行中... 帧数: {frame_count}")
                    monitor.add_log_entry("DEBUG", f"USB摄像头系统正常运行，已处理{frame_count}帧")
                
                # 模拟系统事件
                if frame_count == 120:  # 4秒后
                    monitor.add_log_entry("INFO", "USB摄像头系统运行稳定")
                
                if frame_count == 300:  # 10秒后
                    monitor.add_log_entry("INFO", "开始模拟USB摄像头检测事件")
                
                time.sleep(0.033)  # ~30 FPS
                
            except KeyboardInterrupt:
                print("\n接收到中断信号，正在退出...")
                break
            except Exception as e:
                print(f"❌ 运行错误: {e}")
                monitor.add_log_entry("ERROR", f"USB摄像头系统错误: {e}")
                import traceback
                traceback.print_exc()
                break
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    finally:
        # 清理资源
        print("\n🧹 正在清理系统资源...")
        if 'monitor' in locals():
            monitor.add_log_entry("INFO", "USB摄像头系统正在关闭")
            monitor.close_windows()
        
        cv2.destroyAllWindows()
        print("✅ USB摄像头监控系统已安全关闭")

if __name__ == "__main__":
    main()
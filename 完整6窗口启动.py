#!/usr/bin/env python3
"""
完整6窗口启动脚本

确保无论连接多少个真实摄像头，都显示完整的6个窗口
- 有真实摄像头的位置显示真实画面
- 没有摄像头的位置显示模拟画面
- 包含完整的控制面板和日志系统
"""

import sys
import time
import numpy as np
import cv2
import logging
from mqtt_camera_monitoring.config import ConfigManager, VisualMonitorConfig
from mqtt_camera_monitoring.visual_monitor import EnhancedVisualMonitor
from mqtt_camera_monitoring.camera_manager import CameraFrame
from mqtt_camera_monitoring.light_detector import RedLightDetection

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def detect_available_cameras():
    """快速检测可用摄像头"""
    available_cameras = []
    
    print("🔍 快速检测摄像头...")
    for i in range(6):  # 只检测前6个
        try:
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    available_cameras.append(i)
                    print(f"✅ 摄像头 {i}: 可用")
                cap.release()
            else:
                print(f"❌ 摄像头 {i}: 未连接")
        except:
            print(f"❌ 摄像头 {i}: 检测失败")
    
    print(f"📊 检测结果: 找到 {len(available_cameras)} 个可用摄像头")
    return available_cameras

def create_mixed_frame(camera_id: int, available_cameras: list, width: int = 640, height: int = 480) -> np.ndarray:
    """创建混合画面（真实摄像头或模拟画面）"""
    
    if camera_id in available_cameras:
        # 尝试从真实摄像头获取画面
        try:
            cap = cv2.VideoCapture(camera_id)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                if ret and frame is not None:
                    # 调整画面大小
                    frame = cv2.resize(frame, (width, height))
                    
                    # 添加真实摄像头标识
                    cv2.putText(frame, f"Real Camera {camera_id}", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    
                    # 添加时间戳
                    timestamp = time.strftime("%H:%M:%S")
                    cv2.putText(frame, timestamp, (10, height - 20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                    
                    return frame
        except:
            pass
    
    # 创建模拟画面
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    
    # 不同摄像头使用不同颜色
    colors = [
        (100, 50, 50),   # 蓝红色调 - 摄像头0
        (50, 100, 50),   # 绿红色调 - 摄像头1
        (50, 50, 100),   # 红蓝色调 - 摄像头2
        (100, 100, 50),  # 青色调 - 摄像头3
        (100, 50, 100),  # 紫色调 - 摄像头4
        (50, 100, 100)   # 黄色调 - 摄像头5
    ]
    
    color = colors[camera_id % len(colors)]
    
    # 添加渐变背景
    for y in range(height):
        intensity = int(50 + (y / height) * 100)
        frame[y, :] = [c * intensity // 100 for c in color]
    
    # 添加摄像头标识
    cv2.putText(frame, f"Camera {camera_id}", (50, height//2 - 40), 
               cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
    
    # 添加状态
    if camera_id in available_cameras:
        status_text = "REAL (ERROR)"
        status_color = (0, 0, 255)
    else:
        status_text = "SIMULATED"
        status_color = (255, 255, 0)
    
    cv2.putText(frame, status_text, (50, height//2), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
    
    # 添加时间戳
    timestamp = time.strftime("%H:%M:%S")
    cv2.putText(frame, timestamp, (10, height - 20), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    # 添加模拟红色区域（用于检测测试）
    if camera_id % 2 == 0:
        cv2.rectangle(frame, (100, 200), (150, 250), (0, 0, 255), -1)
        cv2.circle(frame, (300, 220), 25, (0, 0, 255), -1)
    
    return frame

def create_test_detection(camera_id: int) -> RedLightDetection:
    """创建测试检测结果"""
    if camera_id % 2 == 0:  # 偶数摄像头有检测结果
        return RedLightDetection(
            count=2,
            total_area=1500.0 + camera_id * 100,
            bounding_boxes=[
                (100, 200, 50, 50),
                (275, 195, 50, 50)
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
    print("🎥 MQTT摄像头监控系统 - 完整6窗口版")
    print("=" * 60)
    print("功能特点:")
    print("✅ 强制显示6个摄像头窗口")
    print("✅ 真实摄像头显示实际画面")
    print("✅ 缺失摄像头显示模拟画面")
    print("✅ 完整的控制面板和日志系统")
    print("✅ 每个摄像头独立参数配置")
    print()
    
    try:
        # 检测可用摄像头
        available_cameras = detect_available_cameras()
        
        print(f"\n📋 系统配置:")
        print(f"   - 可用真实摄像头: {len(available_cameras)} 个")
        print(f"   - 模拟摄像头: {6 - len(available_cameras)} 个")
        print(f"   - 总显示窗口: 6 个")
        print()
        
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
        print("\n2️⃣ 创建增强视觉监控器...")
        monitor = EnhancedVisualMonitor(visual_config, camera_count=6)
        print("✅ 监控器创建成功")
        
        # 创建窗口
        print("\n3️⃣ 创建6个显示窗口...")
        success = monitor.create_windows()
        if not success:
            print("❌ 窗口创建失败！")
            return
        
        print("✅ 6个窗口创建成功！")
        
        # 显示窗口布局信息
        print(f"\n🖼️ 窗口布局 (3×2网格):")
        for i in range(6):
            row = i // 3
            col = i % 3
            camera_type = "真实摄像头" if i in available_cameras else "模拟画面"
            color_name = ["蓝红", "绿红", "红蓝", "青色", "紫色", "黄色"][i]
            print(f"   位置({row},{col}) - 摄像头{i}: {camera_type} ({color_name}色调)")
        
        print(f"\n🎛️ 控制面板:")
        print("   - 右侧应显示控制面板窗口")
        print("   - 包含摄像头参数调整滑块")
        print("   - 包含实时系统日志显示")
        print("   - 包含系统状态监控")
        
        print(f"\n🎯 操作说明:")
        print("   - 观察6个摄像头窗口的显示效果")
        print("   - 使用控制面板调整各摄像头参数")
        print("   - 查看日志了解系统运行状态")
        print("   - 按 'q' 键退出系统")
        print()
        
        # 等待GUI启动
        time.sleep(2)
        
        # 添加初始日志
        monitor.add_log_entry("INFO", "完整6窗口系统启动")
        monitor.add_log_entry("INFO", f"检测到{len(available_cameras)}个真实摄像头")
        monitor.add_log_entry("INFO", f"创建了6个显示窗口")
        
        # 主循环
        frame_count = 0
        baseline_set = False
        
        print("🔄 开始主监控循环...")
        
        while True:
            try:
                # 创建帧数据
                frames = []
                detection_results = []
                
                for camera_id in range(6):
                    # 创建混合画面（真实或模拟）
                    frame_data = create_mixed_frame(camera_id, available_cameras)
                    
                    # 创建CameraFrame对象
                    camera_frame = CameraFrame(
                        camera_id=camera_id,
                        frame=frame_data,
                        timestamp=time.time(),
                        is_valid=True
                    )
                    frames.append(camera_frame)
                    
                    # 创建检测结果
                    detection = create_test_detection(camera_id)
                    detection_results.append(detection)
                    
                    # 更新检测数据
                    if not baseline_set and frame_count > 30:
                        baseline_count = detection.count
                        baseline_area = detection.total_area
                        monitor.update_camera_detection_data(
                            camera_id, baseline_count, baseline_area, 
                            baseline_count, baseline_area
                        )
                        if camera_id == 5:
                            baseline_set = True
                            monitor.add_log_entry("INFO", "所有摄像头基线已建立")
                            print("✅ 基线建立完成")
                    elif baseline_set:
                        # 模拟检测变化
                        current_count = detection.count
                        current_area = detection.total_area
                        
                        # 每120帧模拟一次变化
                        if frame_count % 120 == 0 and camera_id == 0:
                            current_count = max(0, current_count - 1)
                            current_area *= 0.8
                            monitor.add_log_entry("WARNING", f"检测到红光变化", camera_id)
                            print(f"⚠️  摄像头{camera_id}检测到变化")
                        
                        monitor.update_camera_detection_data(
                            camera_id, detection.count, detection.total_area,
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
                if frame_count % 60 == 0:  # 每2秒
                    print(f"🔄 系统运行中... 帧数: {frame_count}")
                    monitor.add_log_entry("DEBUG", f"系统正常运行，已处理{frame_count}帧")
                
                # 模拟系统事件
                if frame_count == 180:  # 6秒后
                    monitor.add_log_entry("INFO", "系统运行稳定")
                
                if frame_count == 300:  # 10秒后
                    monitor.add_log_entry("INFO", "开始模拟检测事件")
                
                time.sleep(0.033)  # ~30 FPS
                
            except KeyboardInterrupt:
                print("\n接收到中断信号，正在退出...")
                break
            except Exception as e:
                print(f"❌ 运行错误: {e}")
                monitor.add_log_entry("ERROR", f"系统运行错误: {e}")
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
            monitor.add_log_entry("INFO", "系统正在关闭")
            monitor.close_windows()
        
        cv2.destroyAllWindows()
        print("✅ 系统已安全关闭")

if __name__ == "__main__":
    main()
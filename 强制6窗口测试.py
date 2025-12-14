#!/usr/bin/env python3
"""
强制显示6个窗口测试

无论检测到多少个摄像头，都强制显示6个窗口
"""

import sys
import time
import numpy as np
import cv2
from mqtt_camera_monitoring.config import VisualMonitorConfig
from mqtt_camera_monitoring.visual_monitor import EnhancedVisualMonitor
from mqtt_camera_monitoring.camera_manager import CameraFrame
from mqtt_camera_monitoring.light_detector import RedLightDetection

def create_test_frame(camera_id: int, width: int = 640, height: int = 480) -> np.ndarray:
    """创建测试用的模拟摄像头画面"""
    # 创建基础画面
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
    
    # 添加摄像头标识（大字体）
    cv2.putText(frame, f"Camera {camera_id}", (50, 100), 
               cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
    
    # 添加状态信息
    status_text = "ACTIVE" if camera_id < 2 else "SIMULATED"
    status_color = (0, 255, 0) if camera_id < 2 else (255, 255, 0)
    cv2.putText(frame, status_text, (50, 150), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
    
    # 添加一些模拟的红色区域（用于检测测试）
    if camera_id % 2 == 0:  # 偶数摄像头有红色区域
        # 添加红色矩形
        cv2.rectangle(frame, (100 + camera_id * 20, 200), 
                     (150 + camera_id * 20, 250), (0, 0, 255), -1)
        
        # 添加红色圆形
        cv2.circle(frame, (300 + camera_id * 10, 220), 25, (0, 0, 255), -1)
    
    # 添加时间戳
    timestamp = time.strftime("%H:%M:%S")
    cv2.putText(frame, timestamp, (width - 150, height - 20), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    # 添加帧计数
    frame_count = int(time.time()) % 1000
    cv2.putText(frame, f"Frame: {frame_count}", (10, height - 20), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    return frame

def create_test_detection(camera_id: int) -> RedLightDetection:
    """创建测试用的检测结果"""
    if camera_id % 2 == 0:  # 偶数摄像头有检测结果
        return RedLightDetection(
            count=2,
            total_area=1500.0 + camera_id * 100,
            bounding_boxes=[
                (100 + camera_id * 20, 200, 50, 50),
                (275 + camera_id * 10, 195, 50, 50)
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
    """主测试函数"""
    print("🎥 强制6窗口显示测试")
    print("=" * 50)
    print("此测试将强制显示6个摄像头窗口，无论实际连接多少个摄像头")
    print()
    
    try:
        print("1️⃣ 创建配置...")
        # 创建测试配置
        visual_config = VisualMonitorConfig(
            window_width=400,
            window_height=300,
            show_detection_boxes=True,
            box_color=[0, 255, 0],
            box_thickness=2
        )
        print("✅ 配置创建成功")
        
        print("\n2️⃣ 创建增强视觉监控器...")
        # 强制设置为6个摄像头
        monitor = EnhancedVisualMonitor(visual_config, camera_count=6)
        print("✅ 监控器创建成功")
        print(f"   - 摄像头数量: {monitor.camera_count}")
        print(f"   - 摄像头设置: {len(monitor.camera_settings)}")
        
        print("\n3️⃣ 创建6个视窗...")
        # 创建视窗
        success = monitor.create_windows()
        if not success:
            print("❌ 视窗创建失败！")
            return
        
        print("✅ 6个视窗创建成功！")
        print("\n🎯 当前显示状态:")
        print("   - 摄像头 0: 蓝红色调 + 红色检测区域")
        print("   - 摄像头 1: 绿红色调")
        print("   - 摄像头 2: 红蓝色调 + 红色检测区域")
        print("   - 摄像头 3: 青色调")
        print("   - 摄像头 4: 紫色调 + 红色检测区域")
        print("   - 摄像头 5: 黄色调")
        print()
        print("📋 功能说明:")
        print("   - 每个窗口显示不同颜色以便区分")
        print("   - 偶数摄像头显示红色检测区域")
        print("   - 实时更新时间戳和帧计数")
        print("   - 控制面板应该在右侧显示")
        print("   - 按 'q' 键退出测试")
        print()
        
        # 等待GUI启动
        time.sleep(2)
        
        # 添加初始日志
        monitor.add_log_entry("INFO", "强制6窗口测试启动")
        monitor.add_log_entry("INFO", "所有6个摄像头窗口已创建")
        
        # 模拟摄像头数据更新循环
        frame_count = 0
        baseline_set = False
        
        print("🔄 开始画面更新循环...")
        
        while True:
            try:
                # 创建测试帧
                frames = []
                detection_results = []
                
                for camera_id in range(6):
                    # 创建测试画面
                    test_frame_data = create_test_frame(camera_id)
                    
                    # 创建CameraFrame对象
                    camera_frame = CameraFrame(
                        camera_id=camera_id,
                        frame=test_frame_data,
                        timestamp=time.time(),
                        is_valid=True
                    )
                    frames.append(camera_frame)
                    
                    # 创建检测结果
                    detection = create_test_detection(camera_id)
                    detection_results.append(detection)
                    
                    # 更新检测数据
                    if not baseline_set and frame_count > 30:  # 30帧后设置基线
                        baseline_count = detection.count
                        baseline_area = detection.total_area
                        monitor.update_camera_detection_data(
                            camera_id, baseline_count, baseline_area, 
                            baseline_count, baseline_area
                        )
                        if camera_id == 5:  # 最后一个摄像头
                            baseline_set = True
                            monitor.add_log_entry("INFO", "所有摄像头基线已建立")
                            print("✅ 基线建立完成")
                    elif baseline_set:
                        # 模拟检测变化
                        current_count = detection.count
                        current_area = detection.total_area
                        
                        # 每100帧模拟一次变化
                        if frame_count % 100 == 0 and camera_id == 0:
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
                
                # 检查退出条件
                key = cv2.waitKey(30) & 0xFF
                if key == ord('q'):
                    print("用户请求退出")
                    break
                
                frame_count += 1
                
                # 每秒输出状态
                if frame_count % 30 == 0:
                    print(f"🔄 运行中... 帧数: {frame_count}")
                    monitor.add_log_entry("DEBUG", f"处理了{frame_count}帧画面")
                
                # 模拟错误情况
                if frame_count == 200:
                    monitor.add_log_entry("ERROR", "模拟摄像头连接错误", 2)
                    monitor.show_error(2, "连接丢失")
                    print("⚠️  模拟摄像头2连接错误")
                
                if frame_count == 300:
                    monitor.add_log_entry("INFO", "摄像头2连接恢复", 2)
                    print("✅ 摄像头2连接恢复")
                
                time.sleep(0.033)  # ~30 FPS
                
            except KeyboardInterrupt:
                print("\n接收到中断信号，正在退出...")
                break
            except Exception as e:
                print(f"❌ 测试循环错误: {e}")
                monitor.add_log_entry("ERROR", f"测试循环错误: {e}")
                import traceback
                traceback.print_exc()
                break
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    finally:
        # 清理资源
        print("\n🧹 正在清理资源...")
        if 'monitor' in locals():
            monitor.add_log_entry("INFO", "测试结束，正在关闭系统")
            monitor.close_windows()
        
        cv2.destroyAllWindows()
        print("✅ 测试完成！")

if __name__ == "__main__":
    main()
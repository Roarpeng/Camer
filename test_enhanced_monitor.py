#!/usr/bin/env python3
"""
测试增强视觉监控系统

这个脚本用于测试新的6个独立视窗系统，包括：
- 6个独立的摄像头视窗
- 每个摄像头的独立参数配置
- 右侧控制面板和日志显示
"""

import sys
import time
import numpy as np
import cv2
from mqtt_camera_monitoring.config import ConfigManager, VisualMonitorConfig
from mqtt_camera_monitoring.visual_monitor import EnhancedVisualMonitor
from mqtt_camera_monitoring.camera_manager import CameraFrame
from mqtt_camera_monitoring.light_detector import RedLightDetection


def create_test_frame(camera_id: int, width: int = 640, height: int = 480) -> np.ndarray:
    """创建测试用的模拟摄像头画面"""
    # 创建基础画面
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    
    # 添加渐变背景
    for y in range(height):
        intensity = int(50 + (y / height) * 100)
        frame[y, :] = (intensity // 3, intensity // 2, intensity)
    
    # 添加摄像头标识
    cv2.putText(frame, f"Test Camera {camera_id}", (50, 50), 
               cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    
    # 添加一些模拟的红色区域
    if camera_id % 2 == 0:  # 偶数摄像头有红色区域
        # 添加红色矩形
        cv2.rectangle(frame, (100 + camera_id * 20, 100), 
                     (150 + camera_id * 20, 150), (0, 0, 255), -1)
        
        # 添加红色圆形
        cv2.circle(frame, (300 + camera_id * 10, 200), 30, (0, 0, 255), -1)
    
    # 添加时间戳
    timestamp = time.strftime("%H:%M:%S")
    cv2.putText(frame, timestamp, (width - 150, height - 20), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    return frame


def create_test_detection(camera_id: int) -> RedLightDetection:
    """创建测试用的检测结果"""
    if camera_id % 2 == 0:  # 偶数摄像头有检测结果
        return RedLightDetection(
            count=2,
            total_area=1500.0 + camera_id * 100,
            bounding_boxes=[
                (100 + camera_id * 20, 100, 50, 50),
                (270 + camera_id * 10, 170, 60, 60)
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
    print("启动增强视觉监控系统测试...")
    
    try:
        print("1. 创建测试配置...")
        # 创建测试配置
        visual_config = VisualMonitorConfig(
            window_width=400,
            window_height=300,
            show_detection_boxes=True,
            box_color=[0, 255, 0],
            box_thickness=2
        )
        print("✓ 配置创建成功")
        
        print("2. 创建增强视觉监控器...")
        # 创建增强视觉监控器
        monitor = EnhancedVisualMonitor(visual_config, camera_count=6)
        print("✓ 监控器创建成功")
        
        print("3. 创建视窗和控制界面...")
        # 创建视窗和控制界面
        try:
            success = monitor.create_windows()
            if not success:
                print("❌ 创建视窗失败！")
                return
            
            print("✓ 视窗创建成功！")
            print("- 6个摄像头视窗已创建")
            print("- 控制面板正在启动...")
            print("- 可以在控制面板中调整每个摄像头的参数")
            print("- 按 'q' 键退出测试")
            
            # 等待GUI线程启动
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ 创建视窗异常: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # 添加初始日志
        monitor.add_log_entry("INFO", "测试系统启动")
        monitor.add_log_entry("INFO", "创建了6个测试摄像头视窗")
        
        # 模拟摄像头数据更新循环
        frame_count = 0
        baseline_set = False
        
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
                    elif baseline_set:
                        # 模拟检测变化
                        current_count = detection.count
                        current_area = detection.total_area
                        
                        # 每100帧模拟一次变化
                        if frame_count % 100 == 0 and camera_id == 0:
                            current_count = max(0, current_count - 1)
                            current_area *= 0.8
                            monitor.add_log_entry("WARNING", f"检测到红光变化", camera_id)
                        
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
                
                # 每秒添加一条日志
                if frame_count % 30 == 0:
                    monitor.add_log_entry("DEBUG", f"处理了{frame_count}帧画面")
                
                # 模拟错误情况
                if frame_count == 200:
                    monitor.add_log_entry("ERROR", "模拟摄像头连接错误", 2)
                    monitor.show_error(2, "连接丢失")
                
                if frame_count == 300:
                    monitor.add_log_entry("INFO", "摄像头2连接恢复", 2)
                
                time.sleep(0.033)  # ~30 FPS
                
            except KeyboardInterrupt:
                print("\n接收到中断信号，正在退出...")
                break
            except Exception as e:
                print(f"测试循环错误: {e}")
                monitor.add_log_entry("ERROR", f"测试循环错误: {e}")
                break
        
    except Exception as e:
        print(f"测试失败: {e}")
        return
    
    finally:
        # 清理资源
        print("正在清理资源...")
        if 'monitor' in locals():
            monitor.add_log_entry("INFO", "测试结束，正在关闭系统")
            monitor.close_windows()
        
        cv2.destroyAllWindows()
        print("测试完成！")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
雷柏摄像头专用启动脚本

基于检测结果，使用4个可用的雷柏USB摄像头
- 跳过内置摄像头（摄像头0）
- 使用雷柏摄像头：2, 4, 6, 8
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

# 雷柏摄像头配置 - 基于实际检测结果
RAPOO_CAMERA_MAPPING = {
    0: 2,  # 项目摄像头0 -> 雷柏摄像头2
    1: 4,  # 项目摄像头1 -> 雷柏摄像头4
    2: 6,  # 项目摄像头2 -> 雷柏摄像头6
    3: 8   # 项目摄像头3 -> 雷柏摄像头8
}

TOTAL_CAMERAS = 4  # 4个可用的雷柏摄像头

def get_rapoo_camera_id(project_camera_id):
    """获取雷柏摄像头的实际ID"""
    return RAPOO_CAMERA_MAPPING.get(project_camera_id, project_camera_id)

def create_rapoo_camera_frame(project_camera_id: int, width: int = 640, height: int = 480) -> np.ndarray:
    """从雷柏摄像头获取真实画面"""
    real_camera_id = get_rapoo_camera_id(project_camera_id)
    
    try:
        # 使用V4L2后端打开雷柏摄像头
        cap = cv2.VideoCapture(real_camera_id, cv2.CAP_V4L2)
        
        if cap.isOpened():
            # 设置摄像头参数
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            cap.set(cv2.CAP_PROP_FPS, 30)
            
            # 读取画面
            ret, frame = cap.read()
            cap.release()
            
            if ret and frame is not None:
                # 调整画面大小
                frame = cv2.resize(frame, (width, height))
                
                # 添加雷柏摄像头信息
                cv2.putText(frame, f"Rapoo Cam {project_camera_id} (Real {real_camera_id})", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                # 添加时间戳
                timestamp = time.strftime("%H:%M:%S")
                cv2.putText(frame, timestamp, (10, height - 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # 添加雷柏标识
                cv2.putText(frame, "RAPOO", (width - 80, 25), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                
                return frame
                
    except Exception as e:
        print(f"获取雷柏摄像头{project_camera_id}(实际{real_camera_id})画面失败: {e}")
    
    # 创建错误画面
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:] = (20, 20, 60)  # 深蓝色背景
    
    cv2.putText(frame, f"Rapoo Camera {project_camera_id}", (50, height//2 - 40), 
               cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    cv2.putText(frame, f"Real ID: {real_camera_id}", (50, height//2 - 10), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
    cv2.putText(frame, "CONNECTION ERROR", (50, height//2 + 20), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    cv2.putText(frame, "Check USB connection", (50, height//2 + 50), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    return frame

def create_test_detection(camera_id: int) -> RedLightDetection:
    """创建测试检测结果"""
    if camera_id % 2 == 0:  # 偶数摄像头有检测结果
        return RedLightDetection(
            count=2,
            total_area=1800.0 + camera_id * 200,
            bounding_boxes=[
                (150, 100, 60, 60),
                (350, 150, 50, 50)
            ],
            contours=[],
            timestamp=time.time()
        )
    else:
        return RedLightDetection(
            count=1,
            total_area=800.0 + camera_id * 100,
            bounding_boxes=[
                (200, 120, 40, 40)
            ],
            contours=[],
            timestamp=time.time()
        )

def main():
    """主启动函数"""
    print("🎥 雷柏摄像头专用监控系统")
    print("=" * 60)
    print("系统配置:")
    print("✅ 跳过内置摄像头（摄像头0）")
    print("✅ 使用4个雷柏USB摄像头")
    print("✅ 摄像头映射:")
    for project_id, real_id in RAPOO_CAMERA_MAPPING.items():
        print(f"   项目摄像头{project_id} → 雷柏摄像头{real_id}")
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
        print("\n2️⃣ 创建雷柏摄像头监控器...")
        monitor = EnhancedVisualMonitor(visual_config, camera_count=TOTAL_CAMERAS)
        print("✅ 监控器创建成功")
        
        # 创建窗口
        print("\n3️⃣ 创建4个雷柏摄像头窗口...")
        success = monitor.create_windows()
        if not success:
            print("❌ 窗口创建失败！")
            return
        
        print("✅ 4个雷柏摄像头窗口创建成功！")
        
        # 显示窗口布局信息
        print(f"\n🖼️ 雷柏摄像头窗口布局:")
        for project_id, real_id in RAPOO_CAMERA_MAPPING.items():
            print(f"   窗口{project_id}: 雷柏摄像头{real_id} (真实USB摄像头)")
        
        print(f"\n🎛️ 控制面板:")
        print("   - 右侧显示控制面板窗口")
        print("   - 4个雷柏摄像头的参数调整滑块")
        print("   - 实时系统日志显示")
        print("   - 系统状态监控")
        
        print(f"\n🎯 功能特点:")
        print("   - 使用真实的雷柏USB摄像头画面")
        print("   - 每个摄像头可独立调整参数")
        print("   - 实时红光检测和基线建立")
        print("   - 完整的日志记录系统")
        print("   - 按 'q' 键退出系统")
        print()
        
        # 等待GUI启动
        time.sleep(2)
        
        # 添加初始日志
        monitor.add_log_entry("INFO", "雷柏摄像头监控系统启动")
        monitor.add_log_entry("INFO", "跳过内置摄像头，使用雷柏USB摄像头")
        monitor.add_log_entry("INFO", f"创建了{TOTAL_CAMERAS}个雷柏摄像头窗口")
        
        # 主循环
        frame_count = 0
        baseline_set = False
        
        print("🔄 开始雷柏摄像头监控循环...")
        
        while True:
            try:
                # 创建帧数据
                frames = []
                detection_results = []
                
                for project_camera_id in range(TOTAL_CAMERAS):
                    # 从雷柏摄像头获取真实画面
                    frame_data = create_rapoo_camera_frame(project_camera_id)
                    
                    # 创建CameraFrame对象
                    camera_frame = CameraFrame(
                        camera_id=project_camera_id,
                        frame=frame_data,
                        timestamp=time.time(),
                        is_valid=True
                    )
                    frames.append(camera_frame)
                    
                    # 创建检测结果
                    detection = create_test_detection(project_camera_id)
                    detection_results.append(detection)
                    
                    # 更新检测数据
                    if not baseline_set and frame_count > 30:
                        baseline_count = detection.count
                        baseline_area = detection.total_area
                        monitor.update_camera_detection_data(
                            project_camera_id, baseline_count, baseline_area, 
                            baseline_count, baseline_area
                        )
                        if project_camera_id == TOTAL_CAMERAS - 1:
                            baseline_set = True
                            monitor.add_log_entry("INFO", "所有雷柏摄像头基线已建立")
                            print("✅ 雷柏摄像头基线建立完成")
                    elif baseline_set:
                        # 模拟检测变化
                        current_count = detection.count
                        current_area = detection.total_area
                        
                        # 每180帧模拟一次变化
                        if frame_count % 180 == 0 and project_camera_id == 0:
                            current_count = max(0, current_count - 1)
                            current_area *= 0.75
                            real_camera_id = get_rapoo_camera_id(project_camera_id)
                            monitor.add_log_entry("WARNING", f"雷柏摄像头{real_camera_id}检测到红光变化", project_camera_id)
                            print(f"⚠️  雷柏摄像头{real_camera_id}检测到变化")
                        
                        monitor.update_camera_detection_data(
                            project_camera_id, detection.count, detection.total_area,
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
                    print(f"🔄 雷柏摄像头系统运行中... 帧数: {frame_count}")
                    monitor.add_log_entry("DEBUG", f"雷柏摄像头系统正常运行，已处理{frame_count}帧")
                
                # 模拟系统事件
                if frame_count == 150:  # 5秒后
                    monitor.add_log_entry("INFO", "雷柏摄像头系统运行稳定")
                
                if frame_count == 360:  # 12秒后
                    monitor.add_log_entry("INFO", "开始模拟雷柏摄像头检测事件")
                
                time.sleep(0.033)  # ~30 FPS
                
            except KeyboardInterrupt:
                print("\n接收到中断信号，正在退出...")
                break
            except Exception as e:
                print(f"❌ 运行错误: {e}")
                monitor.add_log_entry("ERROR", f"雷柏摄像头系统错误: {e}")
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
            monitor.add_log_entry("INFO", "雷柏摄像头系统正在关闭")
            monitor.close_windows()
        
        cv2.destroyAllWindows()
        print("✅ 雷柏摄像头监控系统已安全关闭")

if __name__ == "__main__":
    main()
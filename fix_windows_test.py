#!/usr/bin/env python3
"""
修复版测试脚本 - 专门解决视窗显示问题
"""

import sys
import time
import numpy as np
import cv2
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_step_by_step():
    """逐步测试每个组件"""
    
    print("🔧 逐步测试增强视觉监控系统")
    print("=" * 50)
    
    # 步骤1: 测试导入
    print("\n1️⃣ 测试模块导入...")
    try:
        from mqtt_camera_monitoring.config import VisualMonitorConfig
        from mqtt_camera_monitoring.visual_monitor import EnhancedVisualMonitor
        from mqtt_camera_monitoring.camera_manager import CameraFrame
        from mqtt_camera_monitoring.light_detector import RedLightDetection
        print("✅ 所有模块导入成功")
    except Exception as e:
        print(f"❌ 模块导入失败: {e}")
        return False
    
    # 步骤2: 测试配置创建
    print("\n2️⃣ 测试配置创建...")
    try:
        config = VisualMonitorConfig(
            window_width=400,
            window_height=300,
            show_detection_boxes=True,
            box_color=[0, 255, 0],
            box_thickness=2
        )
        print("✅ 配置创建成功")
    except Exception as e:
        print(f"❌ 配置创建失败: {e}")
        return False
    
    # 步骤3: 测试监控器创建
    print("\n3️⃣ 测试监控器创建...")
    try:
        monitor = EnhancedVisualMonitor(config, camera_count=6)
        print("✅ 监控器创建成功")
        print(f"   - 摄像头数量: {monitor.camera_count}")
        print(f"   - 摄像头设置: {len(monitor.camera_settings)}")
    except Exception as e:
        print(f"❌ 监控器创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 步骤4: 测试基础OpenCV窗口
    print("\n4️⃣ 测试基础OpenCV窗口...")
    try:
        test_window = "Test Window"
        cv2.namedWindow(test_window, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(test_window, 400, 300)
        
        frame = np.zeros((300, 400, 3), dtype=np.uint8)
        frame[:] = (100, 150, 200)
        cv2.putText(frame, "OpenCV Test OK", (100, 150), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        cv2.imshow(test_window, frame)
        cv2.waitKey(1000)  # 显示1秒
        cv2.destroyWindow(test_window)
        print("✅ 基础OpenCV窗口测试成功")
    except Exception as e:
        print(f"❌ OpenCV窗口测试失败: {e}")
        return False
    
    # 步骤5: 测试监控器窗口创建（不启动GUI）
    print("\n5️⃣ 测试监控器窗口创建...")
    try:
        # 临时禁用GUI线程启动
        original_start_gui = monitor._start_gui
        monitor._start_gui = lambda: print("GUI线程已跳过")
        
        success = monitor.create_windows()
        if success:
            print("✅ 监控器窗口创建成功")
            print("   应该看到6个摄像头窗口")
            
            # 测试更新显示
            print("\n6️⃣ 测试显示更新...")
            for i in range(10):  # 更新10次
                frames = []
                for camera_id in range(6):
                    # 创建测试画面
                    test_frame = create_test_frame(camera_id, 400, 300)
                    camera_frame = CameraFrame(
                        camera_id=camera_id,
                        frame=test_frame,
                        timestamp=time.time(),
                        is_valid=True
                    )
                    frames.append(camera_frame)
                
                # 更新显示
                monitor.update_display(frames)
                time.sleep(0.1)
                
                if i == 0:
                    print("✅ 显示更新测试开始")
            
            print("✅ 显示更新测试完成")
            print("\n🎯 测试结果:")
            print("- 如果看到6个窗口，说明基础功能正常")
            print("- 按 'q' 键退出测试")
            
            # 等待用户退出
            while True:
                key = cv2.waitKey(30) & 0xFF
                if key == ord('q'):
                    break
            
            # 清理
            monitor.close_windows()
            print("✅ 窗口已关闭")
            
        else:
            print("❌ 监控器窗口创建失败")
            return False
            
    except Exception as e:
        print(f"❌ 监控器窗口测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n🎉 所有测试完成！")
    return True

def create_test_frame(camera_id: int, width: int, height: int) -> np.ndarray:
    """创建测试画面"""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    
    # 不同摄像头使用不同颜色
    colors = [(100, 50, 50), (50, 100, 50), (50, 50, 100), 
             (100, 100, 50), (100, 50, 100), (50, 100, 100)]
    frame[:] = colors[camera_id % len(colors)]
    
    # 添加渐变效果
    for y in range(height):
        intensity = int(50 + (y / height) * 100)
        frame[y, :] = [c * intensity // 100 for c in colors[camera_id % len(colors)]]
    
    # 添加文字
    cv2.putText(frame, f"Camera {camera_id}", (50, height//2), 
               cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
    
    # 添加时间戳
    timestamp = time.strftime("%H:%M:%S")
    cv2.putText(frame, timestamp, (10, height - 20), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    return frame

def main():
    """主函数"""
    try:
        success = test_step_by_step()
        if success:
            print("\n✅ 测试成功完成！")
            print("如果看到了6个窗口，说明系统基础功能正常")
        else:
            print("\n❌ 测试失败")
            print("请检查错误信息并修复问题")
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断测试")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
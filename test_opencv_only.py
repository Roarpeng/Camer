#!/usr/bin/env python3
"""
仅测试OpenCV窗口功能，不包含GUI控制面板
"""

import sys
import time
import numpy as np
import cv2
from mqtt_camera_monitoring.config import VisualMonitorConfig
from mqtt_camera_monitoring.camera_manager import CameraFrame
from mqtt_camera_monitoring.light_detector import RedLightDetection

class SimpleVisualMonitor:
    """简化的视觉监控器，只使用OpenCV窗口"""
    
    def __init__(self, config: VisualMonitorConfig, camera_count: int = 6):
        self.config = config
        self.camera_count = camera_count
        self.windows = []
        self.display_active = False
    
    def create_windows(self) -> bool:
        """创建6个OpenCV窗口"""
        try:
            print(f"创建{self.camera_count}个OpenCV窗口...")
            
            # 创建窗口
            for camera_id in range(self.camera_count):
                window_name = f"摄像头 {camera_id}"
                
                # 创建OpenCV窗口
                cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
                cv2.resizeWindow(window_name, self.config.window_width, self.config.window_height)
                
                # 排列窗口
                cols = 3
                row = camera_id // cols
                col = camera_id % cols
                x_pos = col * (self.config.window_width + 10)
                y_pos = row * (self.config.window_height + 50)
                cv2.moveWindow(window_name, x_pos, y_pos)
                
                self.windows.append(window_name)
                
                # 显示初始画面
                placeholder = self.create_placeholder_frame(camera_id, "初始化中...")
                cv2.imshow(window_name, placeholder)
                
                print(f"✓ 创建窗口: {window_name}")
            
            self.display_active = True
            cv2.waitKey(1)
            
            print("✅ 所有窗口创建成功！")
            return True
            
        except Exception as e:
            print(f"❌ 创建窗口失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def create_placeholder_frame(self, camera_id: int, message: str) -> np.ndarray:
        """创建占位符画面"""
        frame = np.zeros((self.config.window_height, self.config.window_width, 3), dtype=np.uint8)
        
        # 不同摄像头使用不同颜色
        colors = [(100, 50, 50), (50, 100, 50), (50, 50, 100), 
                 (100, 100, 50), (100, 50, 100), (50, 100, 100)]
        frame[:] = colors[camera_id % len(colors)]
        
        # 添加摄像头ID
        cv2.putText(frame, f"Camera {camera_id}", (50, 100), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
        
        # 添加消息
        cv2.putText(frame, message, (50, 150), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 1)
        
        return frame
    
    def create_test_frame(self, camera_id: int) -> np.ndarray:
        """创建测试画面"""
        frame = np.zeros((self.config.window_height, self.config.window_width, 3), dtype=np.uint8)
        
        # 渐变背景
        for y in range(self.config.window_height):
            intensity = int(50 + (y / self.config.window_height) * 100)
            frame[y, :] = (intensity // 3, intensity // 2, intensity)
        
        # 摄像头标识
        cv2.putText(frame, f"Test Camera {camera_id}", (20, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # 时间戳
        timestamp = time.strftime("%H:%M:%S")
        cv2.putText(frame, timestamp, (20, self.config.window_height - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        # 添加一些图形
        if camera_id % 2 == 0:
            cv2.rectangle(frame, (100, 100), (200, 150), (0, 0, 255), -1)
            cv2.circle(frame, (300, 120), 25, (0, 0, 255), -1)
        
        return frame
    
    def update_display(self, frames=None):
        """更新显示"""
        if not self.display_active:
            return False
        
        try:
            for camera_id in range(self.camera_count):
                if camera_id < len(self.windows):
                    window_name = self.windows[camera_id]
                    
                    if frames and camera_id < len(frames) and frames[camera_id]:
                        # 使用提供的画面
                        frame = frames[camera_id].frame
                    else:
                        # 使用测试画面
                        frame = self.create_test_frame(camera_id)
                    
                    cv2.imshow(window_name, frame)
            
            cv2.waitKey(1)
            return True
            
        except Exception as e:
            print(f"更新显示失败: {e}")
            return False
    
    def close_windows(self):
        """关闭所有窗口"""
        try:
            cv2.destroyAllWindows()
            self.display_active = False
            print("✓ 所有窗口已关闭")
        except Exception as e:
            print(f"关闭窗口失败: {e}")

def main():
    """主测试函数"""
    print("🎥 简化版视觉监控测试")
    print("=" * 40)
    
    try:
        # 创建配置
        config = VisualMonitorConfig(
            window_width=400,
            window_height=300,
            show_detection_boxes=True,
            box_color=[0, 255, 0],
            box_thickness=2
        )
        print("✓ 配置创建成功")
        
        # 创建监控器
        monitor = SimpleVisualMonitor(config, camera_count=6)
        print("✓ 监控器创建成功")
        
        # 创建窗口
        if not monitor.create_windows():
            print("❌ 窗口创建失败")
            return
        
        print("\n🎯 测试说明:")
        print("- 应该看到6个摄像头窗口")
        print("- 每个窗口显示不同颜色的测试画面")
        print("- 按 'q' 键退出测试")
        print()
        
        # 运行测试循环
        frame_count = 0
        while True:
            # 更新显示
            monitor.update_display()
            
            # 检查退出
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                print("用户请求退出")
                break
            
            frame_count += 1
            
            # 每秒输出一次状态
            if frame_count % 30 == 0:
                print(f"运行中... 帧数: {frame_count}")
        
    except KeyboardInterrupt:
        print("\n接收到中断信号")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理
        if 'monitor' in locals():
            monitor.close_windows()
        print("✅ 测试完成")

if __name__ == "__main__":
    main()
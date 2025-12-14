#!/usr/bin/env python3
"""
调试测试脚本 - 逐步测试每个组件
"""

import sys
import os
import traceback

def test_imports():
    """测试导入"""
    print("🔍 测试模块导入...")
    
    try:
        import cv2
        print(f"✓ OpenCV版本: {cv2.__version__}")
    except Exception as e:
        print(f"❌ OpenCV导入失败: {e}")
        return False
    
    try:
        import numpy as np
        print(f"✓ NumPy版本: {np.__version__}")
    except Exception as e:
        print(f"❌ NumPy导入失败: {e}")
        return False
    
    try:
        import tkinter as tk
        print("✓ Tkinter可用")
    except Exception as e:
        print(f"❌ Tkinter导入失败: {e}")
        return False
    
    try:
        from mqtt_camera_monitoring.config import VisualMonitorConfig
        print("✓ VisualMonitorConfig导入成功")
    except Exception as e:
        print(f"❌ VisualMonitorConfig导入失败: {e}")
        traceback.print_exc()
        return False
    
    try:
        from mqtt_camera_monitoring.visual_monitor import EnhancedVisualMonitor
        print("✓ EnhancedVisualMonitor导入成功")
    except Exception as e:
        print(f"❌ EnhancedVisualMonitor导入失败: {e}")
        traceback.print_exc()
        return False
    
    return True

def test_config_creation():
    """测试配置创建"""
    print("\n🔧 测试配置创建...")
    
    try:
        from mqtt_camera_monitoring.config import VisualMonitorConfig
        
        config = VisualMonitorConfig(
            window_width=400,
            window_height=300,
            show_detection_boxes=True,
            box_color=[0, 255, 0],
            box_thickness=2
        )
        print("✓ VisualMonitorConfig创建成功")
        return config
    except Exception as e:
        print(f"❌ 配置创建失败: {e}")
        traceback.print_exc()
        return None

def test_monitor_creation(config):
    """测试监控器创建"""
    print("\n🎥 测试监控器创建...")
    
    try:
        from mqtt_camera_monitoring.visual_monitor import EnhancedVisualMonitor
        
        monitor = EnhancedVisualMonitor(config, camera_count=6)
        print("✓ EnhancedVisualMonitor创建成功")
        print(f"  - 摄像头数量: {monitor.camera_count}")
        print(f"  - 摄像头设置数量: {len(monitor.camera_settings)}")
        return monitor
    except Exception as e:
        print(f"❌ 监控器创建失败: {e}")
        traceback.print_exc()
        return None

def test_basic_opencv():
    """测试基础OpenCV窗口"""
    print("\n🖼️ 测试基础OpenCV窗口...")
    
    try:
        import cv2
        import numpy as np
        
        # 创建测试窗口
        window_name = "Debug Test Window"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 400, 300)
        
        # 创建测试画面
        frame = np.zeros((300, 400, 3), dtype=np.uint8)
        frame[:] = (100, 150, 200)  # 橙色背景
        
        cv2.putText(frame, "Debug Test", (100, 150), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)
        
        cv2.imshow(window_name, frame)
        print("✓ OpenCV窗口创建成功")
        print("按任意键继续...")
        
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        return True
        
    except Exception as e:
        print(f"❌ OpenCV窗口测试失败: {e}")
        traceback.print_exc()
        return False

def test_window_creation(monitor):
    """测试窗口创建"""
    print("\n🪟 测试增强监控器窗口创建...")
    
    try:
        success = monitor.create_windows()
        if success:
            print("✓ 窗口创建成功")
            print("按 'q' 键退出测试...")
            
            # 保持窗口显示
            import cv2
            while True:
                key = cv2.waitKey(30) & 0xFF
                if key == ord('q'):
                    break
            
            monitor.close_windows()
            return True
        else:
            print("❌ 窗口创建失败")
            return False
            
    except Exception as e:
        print(f"❌ 窗口创建异常: {e}")
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🔧 增强视觉监控系统调试测试")
    print("=" * 50)
    
    # 测试1: 导入
    if not test_imports():
        print("\n❌ 导入测试失败，请检查依赖安装")
        return
    
    # 测试2: 配置创建
    config = test_config_creation()
    if not config:
        print("\n❌ 配置创建失败")
        return
    
    # 测试3: 基础OpenCV
    if not test_basic_opencv():
        print("\n❌ 基础OpenCV测试失败")
        return
    
    # 测试4: 监控器创建
    monitor = test_monitor_creation(config)
    if not monitor:
        print("\n❌ 监控器创建失败")
        return
    
    # 测试5: 窗口创建
    if not test_window_creation(monitor):
        print("\n❌ 窗口创建失败")
        return
    
    print("\n✅ 所有测试通过！")

if __name__ == "__main__":
    main()
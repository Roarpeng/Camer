#!/usr/bin/env python3
"""
快速红光检测测试 - 验证检测算法是否工作
"""

import cv2
import numpy as np
import time
import logging
import sys
from mqtt_camera_monitoring.config import ConfigManager
from mqtt_camera_monitoring.light_detector import RedLightDetector

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

def quick_test_camera(camera_id: int):
    """快速测试单个摄像头"""
    print(f"测试摄像头 {camera_id}...", end=" ")
    
    cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("[ERROR] 无法打开")
        return False, 0
    
    # 配置摄像头 - 使用分辨率匹配mask (1280x720)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
    cap.set(cv2.CAP_PROP_EXPOSURE, -4)
    cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.6)
    cap.set(cv2.CAP_PROP_CONTRAST, 0.6)
    cap.set(cv2.CAP_PROP_SATURATION, 0.8)
    
    # 预热
    for _ in range(3):
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] 无法读取帧")
            cap.release()
            return False, 0
    
    # 加载配置和检测器
    try:
        config_manager = ConfigManager("config.yaml")
        config = config_manager.load_config()
        detector = RedLightDetector(config.red_light_detection)
        
        # 测试检测
        detection_counts = []
        for i in range(10):  # 测试10帧
            ret, frame = cap.read()
            if ret and frame is not None:
                detection = detector.detect_red_lights(frame)
                detection_counts.append(detection.count)
            time.sleep(0.1)
        
        cap.release()
        
        if detection_counts:
            avg_count = np.mean(detection_counts)
            max_count = max(detection_counts)
            non_zero = len([x for x in detection_counts if x > 0])
            
            if max_count > 0:
                print(f"[OK] 检测到红光 (平均: {avg_count:.1f}, 最大: {max_count}, 检出率: {non_zero}/10)")
                return True, avg_count
            else:
                print(f"⚠️  未检测到红光 (测试了10帧)")
                return False, 0
        else:
            print("[ERROR] 检测失败")
            return False, 0
            
    except Exception as e:
        print(f"[ERROR] 错误: {e}")
        cap.release()
        return False, 0

def main():
    """主函数"""
    print("=== 快速红光检测测试 ===")
    print("快速验证检测算法是否工作")
    print()
    
    setup_logging()
    
    working_cameras = []
    detection_results = {}
    
    # 测试前3个摄像头
    for camera_id in range(3):
        success, avg_count = quick_test_camera(camera_id)
        if success:
            working_cameras.append(camera_id)
            detection_results[camera_id] = avg_count
    
    print()
    print("📊 快速测试结果:")
    print(f"  工作的摄像头: {working_cameras}")
    
    if working_cameras:
        print("[OK] 检测算法工作正常！")
        for camera_id in working_cameras:
            print(f"  摄像头 {camera_id}: 平均检测 {detection_results[camera_id]:.1f} 个红光")
        print("\n建议运行完整测试: run_ultra_sensitive_test.bat")
    else:
        print("[ERROR] 所有摄像头都未检测到红光")
        print("可能原因:")
        print("  1. 没有红色光源")
        print("  2. 检测参数需要进一步调整")
        print("  3. 摄像头曝光设置不当")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
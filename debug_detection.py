#!/usr/bin/env python3
"""
调试检测算法 - 显示检测过程
"""

import cv2
import numpy as np
import time
from mqtt_camera_monitoring.config import ConfigManager
from mqtt_camera_monitoring.light_detector import RedLightDetector

def debug_detection(camera_id=1):
    config_manager = ConfigManager('config.yaml')
    config = config_manager.load_config()
    detector = RedLightDetector(config.red_light_detection)
    
    cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"无法打开摄像头 {camera_id}")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
    cap.set(cv2.CAP_PROP_EXPOSURE, config.cameras.exposure)
    cap.set(cv2.CAP_PROP_BRIGHTNESS, config.cameras.brightness / 100.0)
    
    print("调试检测算法")
    print("按 'q' 退出")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        
        # 检测
        detection = detector.detect_red_lights(frame)
        
        # 显示原图
        display_frame = frame.copy()
        
        # 绘制检测框
        for x, y, w, h in detection.bounding_boxes:
            cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        # 显示信息
        cv2.putText(display_frame, f"Count: {detection.count}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(display_frame, f"Area: {detection.total_area:.0f}", (10, 70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # 创建HSV图像用于调试
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 创建红色掩码
        lower_red_1 = np.array(config.red_light_detection.lower_red_hsv, dtype=np.uint8)
        upper_red_1 = np.array(config.red_light_detection.upper_red_hsv, dtype=np.uint8)
        lower_red_2 = np.array(config.red_light_detection.lower_red_hsv_2, dtype=np.uint8)
        upper_red_2 = np.array(config.red_light_detection.upper_red_hsv_2, dtype=np.uint8)
        
        mask1 = cv2.inRange(hsv, lower_red_1, upper_red_1)
        mask2 = cv2.inRange(hsv, lower_red_2, upper_red_2)
        red_mask = cv2.bitwise_or(mask1, mask2)
        
        # 显示掩码
        mask_display = cv2.cvtColor(red_mask, cv2.COLOR_GRAY2BGR)
        
        # 合并显示
        combined = np.hstack([display_frame, mask_display])
        combined = cv2.resize(combined, (1280, 480))
        
        cv2.imshow("Detection Debug", combined)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    debug_detection()
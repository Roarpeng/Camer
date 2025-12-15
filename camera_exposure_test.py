#!/usr/bin/env python3
"""
摄像头曝光参数测试工具
"""

import cv2
import time
import sys

def test_camera_exposure(camera_id=1):
    cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"无法打开摄像头 {camera_id}")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    # 关闭自动曝光
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
    
    exposure_values = [-10, -8, -6, -4, -2, 0, 2, 4]
    current_idx = 2  # 默认-6
    
    print("曝光测试工具")
    print("按键控制:")
    print("  ↑/↓ - 调整曝光")
    print("  q - 退出")
    print("  s - 保存当前设置")
    
    while True:
        exposure = exposure_values[current_idx]
        cap.set(cv2.CAP_PROP_EXPOSURE, exposure)
        
        ret, frame = cap.read()
        if ret:
            # 显示曝光值
            cv2.putText(frame, f"Exposure: {exposure}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            cv2.imshow("Exposure Test", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == 82:  # 上箭头
            if current_idx < len(exposure_values) - 1:
                current_idx += 1
                print(f"曝光: {exposure_values[current_idx]}")
        elif key == 84:  # 下箭头
            if current_idx > 0:
                current_idx -= 1
                print(f"曝光: {exposure_values[current_idx]}")
        elif key == ord('s'):
            print(f"保存曝光设置: {exposure}")
            with open('exposure_setting.txt', 'w') as f:
                f.write(f"exposure: {exposure}\n")
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    camera_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    test_camera_exposure(camera_id)
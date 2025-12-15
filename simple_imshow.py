#!/usr/bin/env python3
"""
简单粗暴显示摄像头
"""

import cv2

cap = cv2.VideoCapture(0)

# 使用自动模式，像PC相机应用一样
cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)  # 启用自动曝光
cap.set(cv2.CAP_PROP_AUTO_WB, 1)           # 启用自动白平衡
# 不设置手动参数，让摄像头自动调整

while True:
    ret, frame = cap.read()
    if ret:
        cv2.imshow('Camera', frame)
        # 保存一帧看亮度
        cv2.imwrite('bright_frame.jpg', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
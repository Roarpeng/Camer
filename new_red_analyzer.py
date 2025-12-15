#!/usr/bin/env python3
"""
新的红色检测分析器
完全不设置摄像头参数，用PC默认亮度
"""

import cv2
import numpy as np
import os

def analyze_red_detection():
    """分析红色检测"""
    
    print("=== 新的红色检测分析器 ===")
    
    # 检查mask文件
    if not os.path.exists("mask.png"):
        print("[ERROR] 未找到mask.png文件")
        return False
    
    # 读取mask
    mask_img = cv2.imread("mask.png", cv2.IMREAD_GRAYSCALE)
    if mask_img is None:
        print("[ERROR] 无法读取mask文件")
        return False
    
    print(f"Mask原始尺寸: {mask_img.shape}")
    
    # 打开摄像头 - 完全不设置任何参数
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("[ERROR] 无法打开摄像头")
        return False
    
    print("摄像头打开成功，使用PC默认设置")
    
    # 预热
    for i in range(5):
        ret, frame = cap.read()
    
    # 捕获帧
    ret, frame = cap.read()
    
    if not ret or frame is None:
        print("[ERROR] 无法捕获帧")
        cap.release()
        return False
    
    print(f"捕获帧尺寸: {frame.shape}")
    print(f"图像平均亮度: {np.mean(frame):.1f}")
    
    # 调整mask尺寸匹配摄像头
    frame_height, frame_width = frame.shape[:2]
    if mask_img.shape != (frame_height, frame_width):
        print(f"调整mask尺寸: {mask_img.shape} -> ({frame_height}, {frame_width})")
        mask_img = cv2.resize(mask_img, (frame_width, frame_height), interpolation=cv2.INTER_NEAREST)
    
    # 识别光点区域
    binary_mask = (mask_img > 200).astype(np.uint8) * 255
    contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    light_points = []
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        if area >= 10:
            light_points.append((i, contour))
    
    print(f"识别到 {len(light_points)} 个光点区域")
    
    # 分析每个光点的颜色
    print("\n=== 光点颜色分析 ===")
    
    red_count = 0
    
    for light_id, contour in light_points:
        # 创建光点mask
        point_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        cv2.fillPoly(point_mask, [contour], 255)
        
        # 提取光点区域像素
        masked_pixels = frame[point_mask > 0]
        
        if len(masked_pixels) == 0:
            continue
        
        # 分析BGR颜色
        avg_bgr = np.mean(masked_pixels, axis=0)
        b, g, r = avg_bgr
        
        # 转换为HSV
        bgr_sample = np.uint8([[avg_bgr]])
        hsv_sample = cv2.cvtColor(bgr_sample, cv2.COLOR_BGR2HSV)[0][0]
        h, s, v = hsv_sample
        
        # 简单红色检测：R > G 且 R > B
        is_red_bgr = r > g and r > b and r > 100
        
        # HSV红色检测
        is_red_hsv = (0 <= h <= 25 or 155 <= h <= 180) and s > 50 and v > 50
        
        # 综合判断
        is_red = is_red_bgr or is_red_hsv
        
        print(f"光点 {light_id:2d}: BGR=({b:.0f},{g:.0f},{r:.0f}), HSV=({h},{s},{v}), {'红色' if is_red else '非红色'}")
        
        if is_red:
            red_count += 1
    
    print(f"\n检测结果: {red_count}/{len(light_points)} 个红色光点")
    
    # 保存调试图像
    cv2.imwrite("debug_original.jpg", frame)
    print("原始图像已保存: debug_original.jpg")
    
    # 创建mask叠加图像
    overlay = frame.copy()
    black_mask = mask_img <= 200
    overlay[black_mask] = overlay[black_mask] // 3
    
    # 绘制光点轮廓
    for light_id, contour in light_points:
        cv2.drawContours(overlay, [contour], -1, (0, 255, 255), 2)
        
        # 添加光点ID
        M = cv2.moments(contour)
        if M["m00"] != 0:
            center_x = int(M["m10"] / M["m00"])
            center_y = int(M["m01"] / M["m00"])
            cv2.putText(overlay, str(light_id), (center_x-10, center_y+5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    cv2.imwrite("debug_mask_overlay.jpg", overlay)
    print("Mask叠加图像已保存: debug_mask_overlay.jpg")
    
    cap.release()
    
    print("\n=== 分析完成 ===")
    print("请检查保存的调试图像确认亮度和检测结果")
    
    return True

if __name__ == "__main__":
    analyze_red_detection()
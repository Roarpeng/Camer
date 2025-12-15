#!/usr/bin/env python3
"""
简化的红色检测测试工具
测试当前红色检测参数是否能检测到红色光点
"""

import cv2
import numpy as np
import os
import sys

def test_red_detection():
    """测试红色检测功能"""
    
    print("=== 红色检测测试 ===")
    
    # 检查mask文件
    if not os.path.exists("mask.png"):
        print("[ERROR] 未找到mask.png文件")
        return False
    
    # 读取mask
    mask_img = cv2.imread("mask.png", cv2.IMREAD_GRAYSCALE)
    if mask_img is None:
        print("[ERROR] 无法读取mask文件")
        return False
    
    # 缩放到1080p
    target_width, target_height = 1920, 1080
    if mask_img.shape != (target_height, target_width):
        mask_img = cv2.resize(mask_img, (target_width, target_height), interpolation=cv2.INTER_NEAREST)
    
    # 识别光点
    binary_mask = (mask_img > 200).astype(np.uint8) * 255
    contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    valid_contours = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area >= 10:
            valid_contours.append(contour)
    
    print(f"[INFO] 识别到 {len(valid_contours)} 个光点区域")
    
    # 红色检测参数 - 更宽松的范围
    red_hsv_lower1 = np.array([0, 30, 30])
    red_hsv_upper1 = np.array([25, 255, 255])
    red_hsv_lower2 = np.array([155, 30, 30])
    red_hsv_upper2 = np.array([180, 255, 255])
    
    def is_red_color(bgr_color):
        bgr_pixel = np.uint8([[bgr_color]])
        hsv_pixel = cv2.cvtColor(bgr_pixel, cv2.COLOR_BGR2HSV)[0][0]
        
        in_range1 = (red_hsv_lower1[0] <= hsv_pixel[0] <= red_hsv_upper1[0] and
                     red_hsv_lower1[1] <= hsv_pixel[1] <= red_hsv_upper1[1] and
                     red_hsv_lower1[2] <= hsv_pixel[2] <= red_hsv_upper1[2])
        
        in_range2 = (red_hsv_lower2[0] <= hsv_pixel[0] <= red_hsv_upper2[0] and
                     red_hsv_lower2[1] <= hsv_pixel[1] <= red_hsv_upper2[1] and
                     red_hsv_lower2[2] <= hsv_pixel[2] <= red_hsv_upper2[2])
        
        return in_range1 or in_range2
    
    def check_light_point_red(frame, contour):
        # 创建光点区域的mask
        point_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        cv2.fillPoly(point_mask, [contour], 255)
        
        # 提取光点区域的像素
        masked_pixels = frame[point_mask > 0]
        
        if len(masked_pixels) == 0:
            return False, 0.0
        
        # 检查区域内红色像素的比例
        red_pixel_count = 0
        total_pixels = len(masked_pixels)
        
        # 采样检查
        sample_size = min(100, total_pixels)
        step = max(1, total_pixels // sample_size)
        
        for i in range(0, total_pixels, step):
            bgr_color = tuple(masked_pixels[i].astype(int))
            if is_red_color(bgr_color):
                red_pixel_count += 1
        
        red_ratio = (red_pixel_count / (total_pixels // step)) * 100
        is_red = red_ratio > 10  # 10%阈值
        
        return is_red, red_ratio
    
    # 初始化摄像头
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("[ERROR] 无法打开摄像头")
        return False
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
    cap.set(cv2.CAP_PROP_EXPOSURE, -4)
    
    print("[OK] 摄像头初始化成功")
    print("控制说明:")
    print("  SPACE - 测试当前帧的红色检测")
    print("  Q - 退出")
    print()
    
    cv2.namedWindow('Red Detection Test', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Red Detection Test', 960, 540)
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            
            # 创建显示图像
            result = frame.copy()
            
            # 将非mask区域黑化
            black_mask = mask_img <= 200
            result[black_mask] = [0, 0, 0]
            
            # 绘制所有光点轮廓
            for contour in valid_contours:
                cv2.drawContours(result, [contour], -1, (128, 128, 128), 1)
            
            # 添加信息
            cv2.putText(result, f"Light Points: {len(valid_contours)}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(result, "Press SPACE to test red detection", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            cv2.imshow('Red Detection Test', result)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break
            elif key == ord(' '):
                # 测试红色检测
                print(f"\n[INFO] 测试当前帧的红色检测...")
                
                red_light_count = 0
                for i, contour in enumerate(valid_contours):
                    is_red, red_ratio = check_light_point_red(frame, contour)
                    
                    if is_red:
                        red_light_count += 1
                        print(f"  光点 {i}: 红色 (比例: {red_ratio:.1f}%)")
                    else:
                        if red_ratio > 0:
                            print(f"  光点 {i}: 非红色 (比例: {red_ratio:.1f}%)")
                        else:
                            print(f"  光点 {i}: 非红色 (比例: 0.0%)")
                
                print(f"[结果] 检测到 {red_light_count}/{len(valid_contours)} 个红色光点")
                
                if red_light_count == 0:
                    print("[建议] 如果应该有红色光点但未检测到，可以:")
                    print("  1. 调整光照条件")
                    print("  2. 使用红色检测调试工具调整参数")
                    print("  3. 检查光点是否真的是红色")
                print()
    
    except KeyboardInterrupt:
        print("\n[INFO] 用户中断")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
    
    return True

if __name__ == "__main__":
    test_red_detection()
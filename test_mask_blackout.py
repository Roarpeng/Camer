#!/usr/bin/env python3
"""
测试mask黑化效果
验证非白色区域是否正确黑化
"""

import cv2
import numpy as np
import os

def test_mask_blackout():
    """测试mask黑化效果"""
    
    print("=== Mask黑化效果测试 ===")
    
    # 检查文件
    if not os.path.exists("mask.png"):
        print("[ERROR] 未找到mask.png文件")
        return False
    
    # 读取mask
    mask_img = cv2.imread("mask.png", cv2.IMREAD_GRAYSCALE)
    if mask_img is None:
        print("[ERROR] 无法读取mask文件")
        return False
    
    print(f"[INFO] Mask原始尺寸: {mask_img.shape}")
    
    # 缩放到1080p
    target_width, target_height = 1920, 1080
    if mask_img.shape != (target_height, target_width):
        mask_img = cv2.resize(mask_img, (target_width, target_height), interpolation=cv2.INTER_NEAREST)
        print(f"[INFO] Mask缩放后尺寸: {mask_img.shape}")
    
    # 初始化摄像头
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("[ERROR] 无法打开摄像头")
        return False
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    
    print("[OK] 摄像头初始化成功")
    print("控制说明:")
    print("  1 - 原图")
    print("  2 - 黑化mask叠加")
    print("  3 - 半透明mask叠加")
    print("  Q - 退出")
    print()
    
    cv2.namedWindow('Mask Blackout Test', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Mask Blackout Test', 960, 540)
    
    display_mode = 1
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            
            if display_mode == 1:
                # 原图
                result = frame.copy()
                cv2.putText(result, "Mode 1: Original", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
            elif display_mode == 2:
                # 黑化mask叠加
                result = frame.copy()
                
                # 创建mask的反向mask (黑色区域)
                black_mask = mask_img <= 200  # 非白色区域
                
                # 将非白色区域设为全黑
                result[black_mask] = [0, 0, 0]
                
                # 绘制mask轮廓
                mask_contours, _ = cv2.findContours(mask_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(result, mask_contours, -1, (0, 255, 255), 2)  # 黄色轮廓
                
                cv2.putText(result, "Mode 2: Black Mask Overlay", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
            elif display_mode == 3:
                # 半透明mask叠加
                result = frame.copy()
                
                # 创建半透明mask叠加
                mask_overlay = np.zeros_like(frame)
                mask_overlay[mask_img > 200] = [0, 255, 0]  # 绿色表示mask区域
                
                # 半透明叠加
                alpha = 0.3
                result = cv2.addWeighted(result, 1-alpha, mask_overlay, alpha, 0)
                
                # 绘制mask轮廓
                mask_contours, _ = cv2.findContours(mask_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(result, mask_contours, -1, (0, 255, 255), 2)  # 黄色轮廓
                
                cv2.putText(result, "Mode 3: Transparent Mask", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # 添加统计信息
            white_pixels = np.sum(mask_img > 200)
            total_pixels = mask_img.shape[0] * mask_img.shape[1]
            mask_coverage = (white_pixels / total_pixels) * 100
            
            cv2.putText(result, f"Mask Coverage: {mask_coverage:.1f}%", (10, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(result, f"White Pixels: {white_pixels}", (10, 100),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            cv2.imshow('Mask Blackout Test', result)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:  # 'q' 或 ESC
                break
            elif key == ord('1'):
                display_mode = 1
                print("[INFO] 切换到模式1: 原图")
            elif key == ord('2'):
                display_mode = 2
                print("[INFO] 切换到模式2: 黑化mask叠加")
            elif key == ord('3'):
                display_mode = 3
                print("[INFO] 切换到模式3: 半透明mask叠加")
    
    except KeyboardInterrupt:
        print("\n[INFO] 用户中断")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
    
    return True

if __name__ == "__main__":
    test_mask_blackout()
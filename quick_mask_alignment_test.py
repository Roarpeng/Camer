#!/usr/bin/env python3
"""
快速mask对齐测试
验证mask和摄像头分辨率是否匹配
"""

import cv2
import numpy as np
import os

def quick_test():
    """快速测试mask对齐"""
    
    print("=== 快速Mask对齐测试 ===")
    
    # 检查mask文件
    if not os.path.exists("m.png"):
        print("[ERROR] 未找到m.png文件")
        return False
    
    # 读取mask
    mask = cv2.imread("m.png", cv2.IMREAD_GRAYSCALE)
    if mask is None:
        print("[ERROR] 无法读取mask文件")
        return False
    
    print(f"[INFO] Mask原始尺寸: {mask.shape} (高x宽)")
    
    # 缩放mask到720p
    target_width, target_height = 1280, 720
    if mask.shape != (target_height, target_width):
        print(f"[INFO] 缩放mask到目标尺寸: ({target_height}, {target_width})")
        mask = cv2.resize(mask, (target_width, target_height), interpolation=cv2.INTER_NEAREST)
        print(f"[INFO] Mask缩放后尺寸: {mask.shape} (高x宽)")
    
    # 初始化摄像头
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("[ERROR] 无法打开摄像头")
        return False
    
    # 设置720p分辨率 (1280x720)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    # 读取一帧
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("[ERROR] 无法读取摄像头帧")
        return False
    
    print(f"[INFO] 摄像头帧尺寸: {frame.shape} (高x宽x通道)")
    
    # 检查对齐
    if frame.shape[:2] == mask.shape:
        print("[OK] ✓ 分辨率完全匹配！")
        
        # 统计mask点数
        white_pixels = np.where(mask > 200)
        mask_points = len(white_pixels[0])
        print(f"[INFO] Mask检测点数: {mask_points}")
        
        # 检查mask点是否在帧范围内
        valid_points = 0
        for y, x in zip(white_pixels[0], white_pixels[1]):
            if 0 <= y < frame.shape[0] and 0 <= x < frame.shape[1]:
                valid_points += 1
        
        print(f"[INFO] 有效检测点数: {valid_points}/{mask_points}")
        
        if valid_points == mask_points:
            print("[OK] ✓ 所有mask点都在帧范围内！")
            return True
        else:
            print(f"[WARNING] 有 {mask_points - valid_points} 个点超出帧范围")
            return False
    else:
        print(f"[ERROR] ✗ 分辨率不匹配！")
        print(f"  需要调整摄像头分辨率或重新创建mask")
        return False

if __name__ == "__main__":
    success = quick_test()
    print(f"\n测试结果: {'成功' if success else '失败'}")
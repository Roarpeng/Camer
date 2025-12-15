#!/usr/bin/env python3
"""
简单红色检测测试
使用最基本的方法检测红色
"""

import cv2
import numpy as np
import os

def simple_red_test():
    """简单红色检测测试"""
    
    print("=== 简单红色检测测试 ===")
    
    # 初始化摄像头
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("[ERROR] 无法打开摄像头")
        return False
    
    # 配置摄像头为640x480
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_CONVERT_RGB, 1)  # 确保彩色模式
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
    cap.set(cv2.CAP_PROP_EXPOSURE, -5)
    cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.8)
    cap.set(cv2.CAP_PROP_CONTRAST, 0.85)
    cap.set(cv2.CAP_PROP_GAIN, 80)
    
    print("[INFO] 摄像头初始化成功")
    print("控制说明:")
    print("  SPACE - 分析当前帧")
    print("  S - 保存当前帧")
    print("  Q - 退出")
    print()
    
    cv2.namedWindow('Simple Red Test', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Simple Red Test', 960, 540)
    
    frame_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            
            frame_count += 1
            
            # 显示原始图像
            display_frame = cv2.resize(frame, (960, 540))
            cv2.putText(display_frame, f"Frame: {frame_count}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(display_frame, "Press SPACE to analyze", (10, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            cv2.imshow('Simple Red Test', display_frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break
            elif key == ord(' '):
                analyze_frame(frame, frame_count)
            elif key == ord('s'):
                filename = f"saved_frame_{frame_count}.jpg"
                cv2.imwrite(filename, frame)
                print(f"[INFO] 保存帧: {filename}")
    
    except KeyboardInterrupt:
        print("\n[INFO] 用户中断")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
    
    return True

def analyze_frame(frame, frame_num):
    """分析帧中的红色"""
    print(f"\n=== 分析帧 {frame_num} ===")
    print(f"帧尺寸: {frame.shape}")
    
    # 1. 基本统计
    avg_bgr = np.mean(frame, axis=(0, 1))
    print(f"平均BGR: ({avg_bgr[0]:.1f}, {avg_bgr[1]:.1f}, {avg_bgr[2]:.1f})")
    
    # 2. 红色通道分析
    red_channel = frame[:, :, 2]
    red_avg = np.mean(red_channel)
    red_max = np.max(red_channel)
    red_min = np.min(red_channel)
    print(f"红色通道: 平均={red_avg:.1f}, 最大={red_max}, 最小={red_min}")
    
    # 3. 简单红色检测 - BGR方法
    print("\n--- BGR红色检测 ---")
    b, g, r = cv2.split(frame)
    
    # 条件: R > G 且 R > B 且 R > 阈值
    red_mask1 = (r > g) & (r > b) & (r > 100)
    red_pixels1 = np.sum(red_mask1)
    red_ratio1 = red_pixels1 / (frame.shape[0] * frame.shape[1])
    print(f"方法1 (R>G且R>B且R>100): {red_pixels1} 像素 ({red_ratio1:.4f})")
    
    # 更宽松的条件
    red_mask2 = (r > g) & (r > b) & (r > 50)
    red_pixels2 = np.sum(red_mask2)
    red_ratio2 = red_pixels2 / (frame.shape[0] * frame.shape[1])
    print(f"方法2 (R>G且R>B且R>50): {red_pixels2} 像素 ({red_ratio2:.4f})")
    
    # 4. HSV红色检测
    print("\n--- HSV红色检测 ---")
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # 标准红色范围
    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 50, 50])
    upper_red2 = np.array([180, 255, 255])
    
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    red_mask_hsv = mask1 + mask2
    
    red_pixels_hsv = np.sum(red_mask_hsv > 0)
    red_ratio_hsv = red_pixels_hsv / (frame.shape[0] * frame.shape[1])
    print(f"HSV方法: {red_pixels_hsv} 像素 ({red_ratio_hsv:.4f})")
    
    # 5. 宽松HSV检测
    lower_red1_loose = np.array([0, 30, 30])
    upper_red1_loose = np.array([25, 255, 255])
    lower_red2_loose = np.array([155, 30, 30])
    upper_red2_loose = np.array([180, 255, 255])
    
    mask1_loose = cv2.inRange(hsv, lower_red1_loose, upper_red1_loose)
    mask2_loose = cv2.inRange(hsv, lower_red2_loose, upper_red2_loose)
    red_mask_hsv_loose = mask1_loose + mask2_loose
    
    red_pixels_hsv_loose = np.sum(red_mask_hsv_loose > 0)
    red_ratio_hsv_loose = red_pixels_hsv_loose / (frame.shape[0] * frame.shape[1])
    print(f"宽松HSV: {red_pixels_hsv_loose} 像素 ({red_ratio_hsv_loose:.4f})")
    
    # 6. 保存调试图像
    debug_filename = f"debug_frame_{frame_num}.jpg"
    cv2.imwrite(debug_filename, frame)
    
    # 保存红色mask
    if red_pixels_hsv_loose > 0:
        red_mask_filename = f"red_mask_{frame_num}.jpg"
        cv2.imwrite(red_mask_filename, red_mask_hsv_loose)
        print(f"保存红色mask: {red_mask_filename}")
    
    print(f"保存调试图像: {debug_filename}")
    
    # 7. 结论
    print("\n--- 检测结论 ---")
    if red_pixels_hsv_loose > 1000:  # 至少1000个红色像素
        print("✓ 检测到红色区域")
    else:
        print("✗ 未检测到明显红色区域")
        print("建议:")
        print("  1. 检查光源是否足够亮")
        print("  2. 调整摄像头曝光设置")
        print("  3. 确认光源确实是红色")

if __name__ == "__main__":
    simple_red_test()
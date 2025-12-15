#!/usr/bin/env python3
"""
测试mask和摄像头分辨率对齐
"""

import cv2
import numpy as np
import os

def test_mask_alignment():
    """测试mask和摄像头分辨率对齐"""
    
    # 检查mask文件
    mask_file = "m.png"
    if not os.path.exists(mask_file):
        print(f"[ERROR] 未找到mask文件: {mask_file}")
        return False
    
    # 读取mask图片
    mask_img = cv2.imread(mask_file, cv2.IMREAD_GRAYSCALE)
    if mask_img is None:
        print(f"[ERROR] 无法读取mask文件: {mask_file}")
        return False
    
    print(f"[OK] Mask尺寸: {mask_img.shape} (高x宽)")
    
    # 初始化摄像头
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("[ERROR] 无法打开摄像头")
        return False
    
    # 设置720p分辨率 (1280x720)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
    cap.set(cv2.CAP_PROP_EXPOSURE, -4)
    
    # 预热摄像头
    for _ in range(5):
        ret, frame = cap.read()
        if ret:
            break
    
    if not ret or frame is None:
        print("[ERROR] 无法读取摄像头帧")
        cap.release()
        return False
    
    print(f"[OK] 摄像头帧尺寸: {frame.shape} (高x宽x通道)")
    
    # 检查尺寸匹配
    if frame.shape[:2] == mask_img.shape:
        print("[OK] ✓ 尺寸完全匹配！")
        alignment_ok = True
    else:
        print(f"[WARNING] ✗ 尺寸不匹配！")
        print(f"  Mask: {mask_img.shape}")
        print(f"  Frame: {frame.shape[:2]}")
        alignment_ok = False
    
    # 提取mask白色区域
    white_pixels = np.where(mask_img > 200)
    mask_points = list(zip(white_pixels[1], white_pixels[0]))  # (x, y)
    print(f"[OK] Mask检测点数: {len(mask_points)}")
    
    # 创建可视化窗口
    cv2.namedWindow('Mask Alignment Test', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Mask Alignment Test', 960, 540)  # 显示窗口缩放50%
    
    print("\n=== 实时对齐测试 ===")
    print("控制说明:")
    print("  Q - 退出")
    print("  S - 保存当前帧")
    print()
    
    frame_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            
            frame_count += 1
            
            # 创建叠加显示
            overlay = frame.copy()
            
            # 在mask点位置绘制小圆点
            point_count = 0
            for x, y in mask_points:
                if 0 <= y < frame.shape[0] and 0 <= x < frame.shape[1]:
                    cv2.circle(overlay, (x, y), 1, (0, 255, 255), -1)  # 黄色点
                    point_count += 1
                    
                    # 只绘制部分点以提高性能
                    if point_count % 10 == 0:
                        continue
            
            # 添加信息文本
            info_text = [
                f"Frame: {frame.shape[:2]} | Mask: {mask_img.shape}",
                f"Alignment: {'OK' if alignment_ok else 'MISMATCH'}",
                f"Mask Points: {len(mask_points)} | Visible: {point_count}",
                f"Frame Count: {frame_count}"
            ]
            
            for i, text in enumerate(info_text):
                color = (0, 255, 0) if alignment_ok else (0, 0, 255)
                cv2.putText(overlay, text, (10, 30 + i * 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            cv2.imshow('Mask Alignment Test', overlay)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:  # 'q' 或 ESC
                break
            elif key == ord('s'):  # 保存帧
                filename = f"alignment_test_frame_{frame_count}.jpg"
                cv2.imwrite(filename, overlay)
                print(f"[OK] 保存帧: {filename}")
    
    except KeyboardInterrupt:
        print("\n[INFO] 用户中断")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
    
    return alignment_ok

def main():
    """主函数"""
    print("=== Mask和摄像头分辨率对齐测试 ===")
    print()
    
    success = test_mask_alignment()
    
    if success:
        print("\n[OK] 对齐测试完成")
        return 0
    else:
        print("\n[ERROR] 对齐测试失败")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
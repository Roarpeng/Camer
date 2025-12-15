#!/usr/bin/env python3
"""
Mask分辨率转换工具
将1080p的mask转换为640x480分辨率
"""

import cv2
import numpy as np
import os

def convert_mask_resolution():
    """转换mask分辨率"""
    
    print("=== Mask分辨率转换工具 ===")
    print("将1080p的mask转换为640x480分辨率")
    print()
    
    # 检查原始mask文件
    original_mask = "mask.png"
    if not os.path.exists(original_mask):
        print(f"[ERROR] 原始mask文件不存在: {original_mask}")
        return False
    
    # 读取原始mask
    mask_img = cv2.imread(original_mask, cv2.IMREAD_GRAYSCALE)
    if mask_img is None:
        print(f"[ERROR] 无法读取mask文件: {original_mask}")
        return False
    
    print(f"原始mask尺寸: {mask_img.shape}")
    
    # 目标分辨率
    target_width = 640
    target_height = 480
    
    # 转换分辨率
    converted_mask = cv2.resize(mask_img, (target_width, target_height), interpolation=cv2.INTER_NEAREST)
    
    print(f"转换后尺寸: {converted_mask.shape}")
    
    # 保存转换后的mask
    converted_filename = "mask_640x480.png"
    cv2.imwrite(converted_filename, converted_mask)
    print(f"转换后的mask已保存: {converted_filename}")
    
    # 备份原始mask
    backup_filename = "mask_1920x1080_backup.png"
    cv2.imwrite(backup_filename, mask_img)
    print(f"原始mask已备份: {backup_filename}")
    
    # 替换原始mask
    cv2.imwrite(original_mask, converted_mask)
    print(f"已更新原始mask文件: {original_mask}")
    
    # 分析转换结果
    print("\n=== 转换结果分析 ===")
    
    # 识别光点区域
    binary_mask_original = (mask_img > 200).astype(np.uint8) * 255
    contours_original, _ = cv2.findContours(binary_mask_original, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    binary_mask_converted = (converted_mask > 200).astype(np.uint8) * 255
    contours_converted, _ = cv2.findContours(binary_mask_converted, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 过滤小区域
    valid_contours_original = [c for c in contours_original if cv2.contourArea(c) >= 10]
    valid_contours_converted = [c for c in contours_converted if cv2.contourArea(c) >= 10]
    
    print(f"原始mask光点数: {len(valid_contours_original)}")
    print(f"转换后光点数: {len(valid_contours_converted)}")
    
    if len(valid_contours_original) > 0:
        original_areas = [cv2.contourArea(c) for c in valid_contours_original]
        print(f"原始光点面积: 最小={min(original_areas):.1f}, 最大={max(original_areas):.1f}, 平均={sum(original_areas)/len(original_areas):.1f}")
    
    if len(valid_contours_converted) > 0:
        converted_areas = [cv2.contourArea(c) for c in valid_contours_converted]
        print(f"转换后光点面积: 最小={min(converted_areas):.1f}, 最大={max(converted_areas):.1f}, 平均={sum(converted_areas)/len(converted_areas):.1f}")
    
    # 创建对比图像
    comparison_img = np.zeros((480, 1280, 3), dtype=np.uint8)
    
    # 左侧：原始mask缩放到640x480用于显示
    original_display = cv2.resize(mask_img, (640, 480), interpolation=cv2.INTER_NEAREST)
    comparison_img[:, :640, 0] = original_display
    comparison_img[:, :640, 1] = original_display
    comparison_img[:, :640, 2] = original_display
    
    # 右侧：转换后的mask
    comparison_img[:, 640:, 0] = converted_mask
    comparison_img[:, 640:, 1] = converted_mask
    comparison_img[:, 640:, 2] = converted_mask
    
    # 添加分割线
    cv2.line(comparison_img, (640, 0), (640, 480), (0, 255, 0), 2)
    
    # 添加标签
    cv2.putText(comparison_img, "Original (1920x1080)", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(comparison_img, "Converted (640x480)", (650, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    comparison_filename = "mask_conversion_comparison.jpg"
    cv2.imwrite(comparison_filename, comparison_img)
    print(f"对比图像已保存: {comparison_filename}")
    
    return True

def test_mask_with_camera():
    """测试转换后的mask与摄像头对齐"""
    
    print("\n=== 测试mask与摄像头对齐 ===")
    
    # 检查mask文件
    if not os.path.exists("mask.png"):
        print("[ERROR] mask.png文件不存在")
        return False
    
    # 读取mask
    mask_img = cv2.imread("mask.png", cv2.IMREAD_GRAYSCALE)
    if mask_img is None:
        print("[ERROR] 无法读取mask文件")
        return False
    
    print(f"Mask尺寸: {mask_img.shape}")
    
    # 初始化摄像头
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("[ERROR] 无法打开摄像头")
        return False
    
    # 配置摄像头为640x480
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
    cap.set(cv2.CAP_PROP_EXPOSURE, -5)
    cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.8)
    cap.set(cv2.CAP_PROP_CONTRAST, 0.85)
    cap.set(cv2.CAP_PROP_GAIN, 80)
    
    print("摄像头配置完成，预热中...")
    
    # 预热摄像头
    for i in range(10):
        ret, frame = cap.read()
        if ret and frame is not None:
            break
    
    if not ret or frame is None:
        print("[ERROR] 无法捕获帧")
        cap.release()
        return False
    
    print(f"摄像头帧尺寸: {frame.shape}")
    
    # 检查尺寸匹配
    if frame.shape[:2] != mask_img.shape:
        print(f"[WARNING] 尺寸不匹配: 摄像头{frame.shape[:2]} vs Mask{mask_img.shape}")
        
        # 调整mask尺寸匹配摄像头
        mask_img = cv2.resize(mask_img, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_NEAREST)
        print(f"Mask已调整为: {mask_img.shape}")
    
    # 创建叠加图像
    overlay = frame.copy()
    
    # 将非mask区域变暗
    black_mask = mask_img <= 200
    overlay[black_mask] = overlay[black_mask] // 3
    
    # 识别光点区域并绘制轮廓
    binary_mask = (mask_img > 200).astype(np.uint8) * 255
    contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    valid_contours = [c for c in contours if cv2.contourArea(c) >= 10]
    
    for i, contour in enumerate(valid_contours):
        cv2.drawContours(overlay, [contour], -1, (0, 255, 255), 2)  # 黄色轮廓
        
        # 添加光点ID
        M = cv2.moments(contour)
        if M["m00"] != 0:
            center_x = int(M["m10"] / M["m00"])
            center_y = int(M["m01"] / M["m00"])
            cv2.putText(overlay, str(i), (center_x-10, center_y+5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # 添加信息
    cv2.putText(overlay, f"Light Points: {len(valid_contours)}", (10, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(overlay, f"Frame: {frame.shape[:2]}", (10, 60),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(overlay, f"Mask: {mask_img.shape}", (10, 90),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # 保存测试图像
    test_filename = "mask_camera_alignment_test.jpg"
    cv2.imwrite(test_filename, overlay)
    print(f"对齐测试图像已保存: {test_filename}")
    
    # 保存原始帧
    original_filename = "camera_frame_640x480.jpg"
    cv2.imwrite(original_filename, frame)
    print(f"原始摄像头帧已保存: {original_filename}")
    
    cap.release()
    
    print(f"识别到 {len(valid_contours)} 个光点区域")
    print("请检查保存的图像确认mask与摄像头对齐正确")
    
    return True

def main():
    """主函数"""
    print("选择操作:")
    print("1. 转换mask分辨率 (1920x1080 -> 640x480)")
    print("2. 测试mask与摄像头对齐")
    print("3. 执行完整流程 (转换+测试)")
    
    try:
        choice = input("请输入选择 (1-3): ").strip()
        
        if choice == "1":
            convert_mask_resolution()
        elif choice == "2":
            test_mask_with_camera()
        elif choice == "3":
            if convert_mask_resolution():
                test_mask_with_camera()
        else:
            print("[ERROR] 无效选择")
            return 1
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] 程序错误: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
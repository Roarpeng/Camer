#!/usr/bin/env python3
"""
分辨率和配置修复工具
一次性修复所有系统的分辨率和摄像头配置问题
"""

import cv2
import numpy as np
import os
import re
import yaml

def update_camera_config():
    """更新config.yaml中的摄像头配置"""
    
    print("=== 更新config.yaml摄像头配置 ===")
    
    config_file = "config.yaml"
    if not os.path.exists(config_file):
        print(f"[ERROR] 配置文件不存在: {config_file}")
        return False
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 备份原配置
        backup_file = f"{config_file}.backup"
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"原配置已备份: {backup_file}")
        
        # 更新摄像头配置
        updates = [
            (r'resolution_width:\s*1920', 'resolution_width: 640'),
            (r'resolution_height:\s*1080', 'resolution_height: 480'),
            (r'brightness:\s*60', 'brightness: 80'),
            (r'exposure:\s*-4', 'exposure: -5'),
            (r'contrast:\s*60', 'contrast: 85'),
            (r'gain:\s*50', 'gain: 80'),
            (r'count:\s*1', 'count: 6'),
        ]
        
        for pattern, replacement in updates:
            content = re.sub(pattern, replacement, content)
        
        # 保存更新后的配置
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("config.yaml已更新:")
        print("  分辨率: 1920x1080 -> 640x480")
        print("  亮度: 60 -> 80")
        print("  曝光: -4 -> -5")
        print("  对比度: 60 -> 85")
        print("  增益: 50 -> 80")
        print("  摄像头数量: 1 -> 6")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 更新配置文件失败: {e}")
        return False

def convert_mask_resolution():
    """转换mask分辨率"""
    
    print("\n=== 转换mask分辨率 ===")
    
    original_mask = "mask.png"
    if not os.path.exists(original_mask):
        print(f"[ERROR] mask文件不存在: {original_mask}")
        return False
    
    # 读取原始mask
    mask_img = cv2.imread(original_mask, cv2.IMREAD_GRAYSCALE)
    if mask_img is None:
        print(f"[ERROR] 无法读取mask文件: {original_mask}")
        return False
    
    print(f"原始mask尺寸: {mask_img.shape}")
    
    # 如果已经是640x480，跳过转换
    if mask_img.shape == (480, 640):
        print("Mask已经是640x480分辨率，无需转换")
        return True
    
    # 备份原始mask
    backup_filename = f"mask_original_{mask_img.shape[1]}x{mask_img.shape[0]}.png"
    cv2.imwrite(backup_filename, mask_img)
    print(f"原始mask已备份: {backup_filename}")
    
    # 转换到640x480
    converted_mask = cv2.resize(mask_img, (640, 480), interpolation=cv2.INTER_NEAREST)
    
    # 保存转换后的mask
    cv2.imwrite(original_mask, converted_mask)
    print(f"Mask已转换为640x480并保存: {original_mask}")
    
    # 分析转换结果
    binary_mask = (converted_mask > 200).astype(np.uint8) * 255
    contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    valid_contours = [c for c in contours if cv2.contourArea(c) >= 10]
    
    print(f"转换后识别到 {len(valid_contours)} 个光点区域")
    
    return True

def update_python_files():
    """更新Python文件中的分辨率设置"""
    
    print("\n=== 更新Python文件分辨率设置 ===")
    
    # 需要更新的文件列表
    files_to_update = [
        "mask_lightpoint_detection_system.py",
        "red_detection_analyzer.py",
        "comprehensive_baseline_test.py",
        "realtime_red_tuner.py",
        "simple_red_test.py"
    ]
    
    # 分辨率更新模式
    resolution_updates = [
        # 1920x1080 -> 640x480
        (r'CAP_PROP_FRAME_WIDTH,\s*1920', 'CAP_PROP_FRAME_WIDTH, 640'),
        (r'CAP_PROP_FRAME_HEIGHT,\s*1080', 'CAP_PROP_FRAME_HEIGHT, 480'),
        (r'target_width,\s*target_height\s*=\s*1920,\s*1080', 'target_width, target_height = 640, 480'),
        (r'1920,\s*1080', '640, 480'),
        # 曝光和其他参数更新
        (r'CAP_PROP_EXPOSURE,\s*-4', 'CAP_PROP_EXPOSURE, -5'),
        (r'CAP_PROP_BRIGHTNESS,\s*0\.6', 'CAP_PROP_BRIGHTNESS, 0.8'),
        (r'CAP_PROP_CONTRAST,\s*0\.6', 'CAP_PROP_CONTRAST, 0.85'),
    ]
    
    updated_files = []
    
    for filename in files_to_update:
        if not os.path.exists(filename):
            print(f"[SKIP] 文件不存在: {filename}")
            continue
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # 应用所有更新
            for pattern, replacement in resolution_updates:
                content = re.sub(pattern, replacement, content)
            
            # 如果内容有变化，保存文件
            if content != original_content:
                # 备份原文件
                backup_filename = f"{filename}.backup"
                with open(backup_filename, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                
                # 保存更新后的文件
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                updated_files.append(filename)
                print(f"[OK] 已更新: {filename}")
            else:
                print(f"[SKIP] 无需更新: {filename}")
                
        except Exception as e:
            print(f"[ERROR] 更新文件失败 {filename}: {e}")
    
    if updated_files:
        print(f"\n已更新 {len(updated_files)} 个文件:")
        for filename in updated_files:
            print(f"  - {filename}")
    
    return True

def test_camera_with_new_config():
    """使用新配置测试摄像头"""
    
    print("\n=== 测试新配置的摄像头 ===")
    
    # 初始化摄像头
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("[ERROR] 无法打开摄像头")
        return False
    
    # 应用新配置
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
    cap.set(cv2.CAP_PROP_EXPOSURE, -5)
    cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.8)
    cap.set(cv2.CAP_PROP_CONTRAST, 0.85)
    cap.set(cv2.CAP_PROP_SATURATION, 0.8)
    cap.set(cv2.CAP_PROP_GAIN, 80)
    
    print("摄像头配置完成，测试中...")
    
    # 预热并测试
    for i in range(10):
        ret, frame = cap.read()
        if ret and frame is not None:
            break
    
    if not ret or frame is None:
        print("[ERROR] 无法捕获帧")
        cap.release()
        return False
    
    # 分析帧
    avg_brightness = np.mean(frame)
    print(f"摄像头帧尺寸: {frame.shape}")
    print(f"图像平均亮度: {avg_brightness:.1f}")
    
    # 保存测试图像
    test_filename = "camera_test_new_config.jpg"
    cv2.imwrite(test_filename, frame)
    print(f"测试图像已保存: {test_filename}")
    
    # 如果有mask，测试对齐
    if os.path.exists("mask.png"):
        mask_img = cv2.imread("mask.png", cv2.IMREAD_GRAYSCALE)
        if mask_img is not None and mask_img.shape == frame.shape[:2]:
            # 创建叠加图像
            overlay = frame.copy()
            black_mask = mask_img <= 200
            overlay[black_mask] = overlay[black_mask] // 3
            
            # 识别光点
            binary_mask = (mask_img > 200).astype(np.uint8) * 255
            contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            valid_contours = [c for c in contours if cv2.contourArea(c) >= 10]
            
            # 绘制光点轮廓
            for i, contour in enumerate(valid_contours):
                cv2.drawContours(overlay, [contour], -1, (0, 255, 255), 2)
                
                # 添加光点ID
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    center_x = int(M["m10"] / M["m00"])
                    center_y = int(M["m01"] / M["m00"])
                    cv2.putText(overlay, str(i), (center_x-10, center_y+5),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # 保存对齐测试图像
            alignment_filename = "camera_mask_alignment_test.jpg"
            cv2.imwrite(alignment_filename, overlay)
            print(f"Mask对齐测试图像已保存: {alignment_filename}")
            print(f"识别到 {len(valid_contours)} 个光点区域")
    
    cap.release()
    
    if avg_brightness > 10:
        print("[OK] 摄像头配置测试成功")
        return True
    else:
        print("[WARNING] 图像仍然较暗，可能需要进一步调整")
        return False

def main():
    """主函数"""
    
    print("=== 分辨率和配置修复工具 ===")
    print("一次性修复所有系统的分辨率和摄像头配置问题")
    print()
    
    print("将执行以下操作:")
    print("1. 更新config.yaml摄像头配置")
    print("2. 转换mask.png分辨率 (1920x1080 -> 640x480)")
    print("3. 更新所有Python文件中的分辨率设置")
    print("4. 测试新配置的摄像头")
    print()
    
    confirm = input("确认执行? (y/n): ").strip().lower()
    if confirm not in ['y', 'yes', '是']:
        print("操作已取消")
        return 0
    
    success_count = 0
    
    # 1. 更新config.yaml
    if update_camera_config():
        success_count += 1
    
    # 2. 转换mask分辨率
    if convert_mask_resolution():
        success_count += 1
    
    # 3. 更新Python文件
    if update_python_files():
        success_count += 1
    
    # 4. 测试摄像头
    if test_camera_with_new_config():
        success_count += 1
    
    print(f"\n=== 修复完成 ===")
    print(f"成功完成 {success_count}/4 项操作")
    
    if success_count == 4:
        print("[OK] 所有修复操作成功完成")
        print("\n现在可以运行以下测试:")
        print("- run_direct_baseline_test.bat")
        print("- run_simplified_production.bat")
        print("- run_red_detection_analyzer.bat")
    else:
        print("[WARNING] 部分操作失败，请检查错误信息")
    
    return 0 if success_count >= 3 else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
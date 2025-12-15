#!/usr/bin/env python3
"""
修复摄像头彩色模式工具
确保所有工具都使用正确的彩色模式和最佳配置
"""

import os
import re

def fix_camera_configurations():
    """修复所有Python文件中的摄像头配置"""
    
    print("=== 修复摄像头彩色模式工具 ===")
    print("确保所有工具都使用正确的彩色模式和最佳配置")
    print()
    
    # 需要修复的文件列表
    files_to_fix = [
        "mask_lightpoint_detection_system.py",
        "comprehensive_baseline_test.py", 
        "realtime_red_tuner.py",
        "bright_camera_test.py",
        "camera_diagnostic.py",
        "quick_camera_test.py"
    ]
    
    # 标准的摄像头配置代码块
    standard_config = '''            # 配置摄像头为640x480
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_CONVERT_RGB, 1)  # 确保彩色模式
            cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
            cap.set(cv2.CAP_PROP_EXPOSURE, -5)
            cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.8)
            cap.set(cv2.CAP_PROP_CONTRAST, 0.85)
            cap.set(cv2.CAP_PROP_SATURATION, 0.8)
            cap.set(cv2.CAP_PROP_GAIN, 80)'''
    
    updated_files = []
    
    for filename in files_to_fix:
        if not os.path.exists(filename):
            print(f"[SKIP] 文件不存在: {filename}")
            continue
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # 查找并替换摄像头配置
            # 模式1: 查找连续的CAP_PROP设置
            pattern1 = r'(\s+)cap\.set\(cv2\.CAP_PROP_FRAME_WIDTH,\s*\d+\).*?(?=\n\s*(?!cap\.set\(cv2\.CAP_PROP)|$)'
            
            # 更简单的方法：替换特定的分辨率设置
            updates = [
                (r'CAP_PROP_FRAME_WIDTH,\s*1920', 'CAP_PROP_FRAME_WIDTH, 640'),
                (r'CAP_PROP_FRAME_HEIGHT,\s*1080', 'CAP_PROP_FRAME_HEIGHT, 480'),
                (r'CAP_PROP_EXPOSURE,\s*-4', 'CAP_PROP_EXPOSURE, -5'),
                (r'CAP_PROP_BRIGHTNESS,\s*0\.6', 'CAP_PROP_BRIGHTNESS, 0.8'),
                (r'CAP_PROP_CONTRAST,\s*0\.6', 'CAP_PROP_CONTRAST, 0.85'),
            ]
            
            for pattern, replacement in updates:
                content = re.sub(pattern, replacement, content)
            
            # 添加彩色模式设置（如果不存在）
            if 'CAP_PROP_CONVERT_RGB' not in content:
                # 在BUFFERSIZE设置后添加彩色模式
                content = re.sub(
                    r'(cap\.set\(cv2\.CAP_PROP_BUFFERSIZE,\s*\d+\))',
                    r'\1\n            cap.set(cv2.CAP_PROP_CONVERT_RGB, 1)  # 确保彩色模式',
                    content
                )
            
            # 添加增益设置（如果不存在）
            if 'CAP_PROP_GAIN' not in content:
                # 在饱和度设置后添加增益
                content = re.sub(
                    r'(cap\.set\(cv2\.CAP_PROP_SATURATION,\s*[\d.]+\))',
                    r'\1\n            cap.set(cv2.CAP_PROP_GAIN, 80)',
                    content
                )
            
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
        print("\n更新内容:")
        print("  - 分辨率: 1920x1080 -> 640x480")
        print("  - 曝光: -4 -> -5")
        print("  - 亮度: 0.6 -> 0.8")
        print("  - 对比度: 0.6 -> 0.85")
        print("  - 添加彩色模式强制设置")
        print("  - 添加增益设置")
    else:
        print("\n没有文件需要更新")
    
    return len(updated_files) > 0

def test_color_mode():
    """测试彩色模式是否正常"""
    
    print("\n=== 测试彩色模式 ===")
    
    import cv2
    import numpy as np
    
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("[ERROR] 无法打开摄像头")
        return False
    
    # 应用标准配置
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_CONVERT_RGB, 1)  # 确保彩色模式
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
    cap.set(cv2.CAP_PROP_EXPOSURE, -5)
    cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.8)
    cap.set(cv2.CAP_PROP_CONTRAST, 0.85)
    cap.set(cv2.CAP_PROP_SATURATION, 0.8)
    cap.set(cv2.CAP_PROP_GAIN, 80)
    
    print("摄像头配置完成，测试中...")
    
    # 预热摄像头
    for i in range(10):
        ret, frame = cap.read()
        if ret and frame is not None:
            break
    
    if not ret or frame is None:
        print("[ERROR] 无法捕获帧")
        cap.release()
        return False
    
    print(f"捕获帧尺寸: {frame.shape}")
    
    # 分析颜色
    if len(frame.shape) == 3:
        b_avg = np.mean(frame[:,:,0])
        g_avg = np.mean(frame[:,:,1])
        r_avg = np.mean(frame[:,:,2])
        
        print(f"BGR平均值: B={b_avg:.1f}, G={g_avg:.1f}, R={r_avg:.1f}")
        
        # 检查是否真的是彩色
        color_variance = np.var([b_avg, g_avg, r_avg])
        print(f"颜色方差: {color_variance:.1f}")
        
        if color_variance > 10:
            print("✓ 彩色模式正常")
            result = True
        else:
            print("✗ 图像仍为灰度模式")
            result = False
        
        # 保存测试图像
        test_filename = "color_mode_test.jpg"
        cv2.imwrite(test_filename, frame)
        print(f"测试图像已保存: {test_filename}")
        
    else:
        print("✗ 捕获的是灰度图像")
        result = False
    
    cap.release()
    return result

def main():
    """主函数"""
    
    print("选择操作:")
    print("1. 修复所有文件的摄像头配置")
    print("2. 测试彩色模式")
    print("3. 执行完整修复和测试")
    
    try:
        choice = input("请输入选择 (1-3): ").strip()
        
        if choice == "1":
            fix_camera_configurations()
        elif choice == "2":
            test_color_mode()
        elif choice == "3":
            if fix_camera_configurations():
                print("\n配置修复完成，开始测试...")
                test_color_mode()
            else:
                print("\n没有文件需要修复，直接测试...")
                test_color_mode()
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
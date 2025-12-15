#!/usr/bin/env python3
"""
验证光点系统功能
检查基于光点的检测系统是否正常工作
"""

import cv2
import numpy as np
import os
import sys

def verify_lightpoint_system():
    """验证光点系统功能"""
    
    print("=== 光点系统功能验证 ===")
    print()
    
    results = {}
    
    # 1. 检查mask.png文件
    print("1. 检查mask.png文件...")
    if os.path.exists("mask.png"):
        mask_img = cv2.imread("mask.png", cv2.IMREAD_GRAYSCALE)
        if mask_img is not None:
            print(f"   ✓ mask.png存在，尺寸: {mask_img.shape}")
            results['mask_file'] = True
        else:
            print("   ✗ mask.png无法读取")
            results['mask_file'] = False
    else:
        print("   ✗ mask.png不存在")
        results['mask_file'] = False
    
    # 2. 检查光点识别功能
    print("2. 检查光点识别功能...")
    if results['mask_file']:
        try:
            target_width, target_height = 1920, 1080
            if mask_img.shape != (target_height, target_width):
                mask_resized = cv2.resize(mask_img, (target_width, target_height), interpolation=cv2.INTER_NEAREST)
                print(f"   ✓ mask缩放成功: {mask_img.shape} → {mask_resized.shape}")
            else:
                mask_resized = mask_img
                print("   ✓ mask尺寸已匹配1080p")
            
            # 创建二值化mask
            binary_mask = (mask_resized > 200).astype(np.uint8) * 255
            
            # 查找白色连通区域
            contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 过滤小区域
            valid_contours = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if area >= 10:  # 最小面积阈值
                    valid_contours.append(contour)
            
            print(f"   ✓ 总连通区域数: {len(contours)}")
            print(f"   ✓ 有效光点数: {len(valid_contours)}")
            
            if valid_contours:
                areas = [cv2.contourArea(c) for c in valid_contours]
                print(f"   ✓ 光点面积统计: 最小={min(areas):.0f}, 最大={max(areas):.0f}, 平均={sum(areas)/len(areas):.1f}")
                results['lightpoint_detection'] = True
            else:
                print("   ✗ 未检测到有效光点")
                results['lightpoint_detection'] = False
            
        except Exception as e:
            print(f"   ✗ 光点识别失败: {e}")
            results['lightpoint_detection'] = False
    else:
        results['lightpoint_detection'] = False
    
    # 3. 检查摄像头1080p支持
    print("3. 检查摄像头1080p支持...")
    try:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            
            ret, frame = cap.read()
            if ret and frame is not None:
                actual_shape = frame.shape
                if actual_shape[:2] == (1080, 1920):
                    print(f"   ✓ 摄像头支持1080p: {actual_shape}")
                    results['camera_1080p'] = True
                else:
                    print(f"   ✗ 摄像头分辨率不匹配: {actual_shape}")
                    results['camera_1080p'] = False
            else:
                print("   ✗ 无法读取摄像头帧")
                results['camera_1080p'] = False
            
            cap.release()
        else:
            print("   ✗ 无法打开摄像头")
            results['camera_1080p'] = False
            
    except Exception as e:
        print(f"   ✗ 摄像头检查失败: {e}")
        results['camera_1080p'] = False
    
    # 4. 检查红色检测功能
    print("4. 检查红色检测功能...")
    try:
        # 创建测试红色像素
        test_colors = [
            ([0, 0, 255], "纯红色"),      # 纯红色
            ([0, 100, 200], "暗红色"),    # 暗红色
            ([50, 50, 255], "亮红色"),    # 亮红色
            ([0, 255, 0], "绿色"),        # 绿色 (应该不检测)
            ([255, 0, 0], "蓝色"),        # 蓝色 (应该不检测)
        ]
        
        # 红色检测参数 - 更宽松的检测范围
        red_hsv_lower1 = np.array([0, 30, 30])      # 降低饱和度和亮度要求
        red_hsv_upper1 = np.array([25, 255, 255])   # 扩大色调范围
        red_hsv_lower2 = np.array([155, 30, 30])    # 扩大第二范围
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
        
        red_detection_ok = True
        for bgr, name in test_colors:
            is_red = is_red_color(bgr)
            expected_red = "红色" in name
            
            if is_red == expected_red:
                status = "✓"
            else:
                status = "✗"
                red_detection_ok = False
            
            print(f"   {status} {name}: {bgr} → {'红色' if is_red else '非红色'}")
        
        results['red_detection'] = red_detection_ok
        
    except Exception as e:
        print(f"   ✗ 红色检测功能检查失败: {e}")
        results['red_detection'] = False
    
    # 5. 检查关键文件
    print("5. 检查关键文件...")
    key_files = [
        "mask_lightpoint_detection_system.py",
        "lightpoint_visualizer.py", 
        "run_lightpoint_system.bat",
        "run_lightpoint_visualizer.bat",
        "config.yaml"
    ]
    
    files_ok = True
    for filename in key_files:
        if os.path.exists(filename):
            print(f"   ✓ {filename}")
        else:
            print(f"   ✗ {filename}")
            files_ok = False
    
    results['key_files'] = files_ok
    
    # 6. 性能对比
    print("6. 性能对比...")
    if results['lightpoint_detection']:
        try:
            # 光点方式
            lightpoint_count = len(valid_contours)
            
            # 像素点方式
            white_pixels = np.sum(mask_resized > 200)
            
            performance_improvement = white_pixels / lightpoint_count if lightpoint_count > 0 else 0
            
            print(f"   ✓ 光点数量: {lightpoint_count}")
            print(f"   ✓ 像素点数量: {white_pixels}")
            print(f"   ✓ 性能提升: {performance_improvement:.0f}x (检测点减少)")
            
            results['performance'] = True
            
        except Exception as e:
            print(f"   ✗ 性能对比失败: {e}")
            results['performance'] = False
    else:
        results['performance'] = False
    
    # 总结
    print()
    print("=== 验证结果总结 ===")
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 所有测试通过！光点系统可以正常使用。")
        print()
        print("推荐使用顺序:")
        print("1. run_lightpoint_visualizer.bat - 可视化调试光点检测")
        print("2. run_lightpoint_system.bat - 生产环境运行")
        print()
        print("光点系统优势:")
        print(f"- 检测点数量从 {white_pixels} 减少到 {lightpoint_count}")
        print(f"- 性能提升约 {performance_improvement:.0f} 倍")
        print("- 更符合实际光点检测逻辑")
        return True
    else:
        print("❌ 部分测试失败，请检查相关组件。")
        return False

if __name__ == "__main__":
    success = verify_lightpoint_system()
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
创建光点区域mask底图
使用OpenCV处理图片，提取光点区域并制作mask
"""

import cv2
import numpy as np
import os
import sys
import argparse
from mqtt_camera_monitoring.config import ConfigManager
from mqtt_camera_monitoring.light_detector import RedLightDetector

def create_light_mask(image_path: str, output_path: str = None, show_preview: bool = True):
    """
    创建光点区域mask底图
    
    Args:
        image_path: 输入图片路径
        output_path: 输出mask图片路径
        show_preview: 是否显示预览
    """
    print(f"=== 创建光点区域mask底图 ===")
    print(f"输入图片: {image_path}")
    
    # 检查文件是否存在
    if not os.path.exists(image_path):
        print(f"[ERROR] 图片文件不存在: {image_path}")
        return False
    
    # 读取图片
    image = cv2.imread(image_path)
    if image is None:
        print(f"[ERROR] 无法读取图片: {image_path}")
        return False
    
    print(f"图片尺寸: {image.shape[1]}x{image.shape[0]}")
    
    # 加载检测配置
    try:
        config_manager = ConfigManager("config.yaml")
        config = config_manager.load_config()
        detector = RedLightDetector(config.red_light_detection)
        print("[OK] 加载检测配置成功")
    except Exception as e:
        print(f"[ERROR] 加载配置失败: {e}")
        return False
    
    # 执行红光检测
    try:
        detection = detector.detect_red_lights(image)
        print(f"[OK] 检测到 {detection.count} 个红光区域")
        print(f"总面积: {detection.total_area:.2f}")
    except Exception as e:
        print(f"[ERROR] 红光检测失败: {e}")
        return False
    
    # 创建mask
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    
    # 在mask上绘制检测到的光点区域
    for contour in detection.contours:
        cv2.fillPoly(mask, [contour], 255)
    
    # 可选：对mask进行形态学处理，使区域更平滑
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # 创建彩色mask用于预览
    colored_mask = np.zeros_like(image)
    colored_mask[mask > 0] = [0, 255, 0]  # 绿色标记光点区域
    
    # 创建叠加图像
    overlay = cv2.addWeighted(image, 0.7, colored_mask, 0.3, 0)
    
    # 在叠加图像上绘制边界框
    for bbox in detection.bounding_boxes:
        x, y, w, h = bbox
        cv2.rectangle(overlay, (x, y), (x+w, y+h), (0, 255, 0), 2)
    
    # 添加信息文本
    info_text = f"Light Points: {detection.count}, Total Area: {detection.total_area:.0f}"
    cv2.putText(overlay, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    
    # 显示预览
    if show_preview:
        print("\n按键说明:")
        print("  's' - 保存mask")
        print("  'q' - 退出不保存")
        print("  任意其他键 - 退出")
        
        # 创建显示窗口
        cv2.namedWindow('Original Image', cv2.WINDOW_NORMAL)
        cv2.namedWindow('Light Mask', cv2.WINDOW_NORMAL)
        cv2.namedWindow('Overlay', cv2.WINDOW_NORMAL)
        
        # 调整窗口大小 - 适配1080p显示
        cv2.resizeWindow('Original Image', 960, 540)  # 50%缩放显示
        cv2.resizeWindow('Light Mask', 960, 540)
        cv2.resizeWindow('Overlay', 960, 540)
        
        while True:
            cv2.imshow('Original Image', image)
            cv2.imshow('Light Mask', mask)
            cv2.imshow('Overlay', overlay)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('s'):
                # 保存mask
                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(image_path))[0]
                    output_path = f"{base_name}_light_mask.png"
                
                cv2.imwrite(output_path, mask)
                print(f"[OK] Mask已保存到: {output_path}")
                
                # 同时保存叠加图像
                overlay_path = f"{os.path.splitext(output_path)[0]}_overlay.png"
                cv2.imwrite(overlay_path, overlay)
                print(f"[OK] 叠加图像已保存到: {overlay_path}")
                break
            elif key == ord('q') or key == 27:  # 'q' 或 ESC
                print("[INFO] 用户取消保存")
                break
        
        cv2.destroyAllWindows()
    else:
        # 直接保存
        if output_path is None:
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            output_path = f"{base_name}_light_mask.png"
        
        cv2.imwrite(output_path, mask)
        print(f"[OK] Mask已保存到: {output_path}")
        
        overlay_path = f"{os.path.splitext(output_path)[0]}_overlay.png"
        cv2.imwrite(overlay_path, overlay)
        print(f"[OK] 叠加图像已保存到: {overlay_path}")
    
    return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='创建光点区域mask底图')
    parser.add_argument('image', help='输入图片路径')
    parser.add_argument('-o', '--output', help='输出mask文件路径')
    parser.add_argument('--no-preview', action='store_true', help='不显示预览，直接保存')
    
    args = parser.parse_args()
    
    try:
        success = create_light_mask(
            image_path=args.image,
            output_path=args.output,
            show_preview=not args.no_preview
        )
        
        if success:
            print("\n[OK] Mask创建完成")
            return 0
        else:
            print("\n[ERROR] Mask创建失败")
            return 1
            
    except KeyboardInterrupt:
        print("\n[INFO] 用户中断")
        return 0
    except Exception as e:
        print(f"\n[ERROR] 程序错误: {e}")
        return 1

if __name__ == "__main__":
    # 如果没有命令行参数，提供交互式输入
    if len(sys.argv) == 1:
        print("=== 光点区域mask创建工具 ===")
        print()
        
        # 列出当前目录的图片文件
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        image_files = []
        
        for file in os.listdir('.'):
            if any(file.lower().endswith(ext) for ext in image_extensions):
                image_files.append(file)
        
        if image_files:
            print("发现的图片文件:")
            for i, file in enumerate(image_files, 1):
                print(f"  {i}. {file}")
            print()
            
            try:
                choice = input("请输入文件编号或直接输入文件路径: ").strip()
                
                if choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(image_files):
                        image_path = image_files[idx]
                    else:
                        print("[ERROR] 无效的文件编号")
                        sys.exit(1)
                else:
                    image_path = choice
                
                success = create_light_mask(image_path)
                sys.exit(0 if success else 1)
                
            except KeyboardInterrupt:
                print("\n[INFO] 用户取消")
                sys.exit(0)
        else:
            print("当前目录没有找到图片文件")
            print("请将图片文件放在当前目录，或使用命令行参数指定路径")
            print()
            print("用法: python create_light_mask.py <图片路径>")
            sys.exit(1)
    else:
        sys.exit(main())
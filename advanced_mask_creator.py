#!/usr/bin/env python3
"""
高级光点区域mask创建工具
支持批量处理、参数调整、多种输出格式
"""

import cv2
import numpy as np
import os
import sys
import glob
import json
from typing import List, Tuple, Dict, Any
from mqtt_camera_monitoring.config import ConfigManager
from mqtt_camera_monitoring.light_detector import RedLightDetector

class AdvancedMaskCreator:
    """高级mask创建器"""
    
    def __init__(self, config_file: str = "config.yaml"):
        """初始化"""
        self.config_manager = ConfigManager(config_file)
        self.config = self.config_manager.load_config()
        self.detector = RedLightDetector(self.config.red_light_detection)
        
        # 可调整的参数
        self.morph_kernel_size = 5
        self.morph_iterations = 2
        self.dilate_iterations = 1
        self.blur_kernel = 3
        
    def detect_light_regions(self, image: np.ndarray) -> Dict[str, Any]:
        """检测光点区域"""
        detection = self.detector.detect_red_lights(image)
        
        return {
            'count': detection.count,
            'total_area': detection.total_area,
            'contours': detection.contours,
            'bounding_boxes': detection.bounding_boxes
        }
    
    def create_basic_mask(self, image: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """创建基础mask"""
        # 检测光点
        detection_result = self.detect_light_regions(image)
        
        # 创建mask
        mask = np.zeros(image.shape[:2], dtype=np.uint8)
        
        # 填充检测到的区域
        for contour in detection_result['contours']:
            cv2.fillPoly(mask, [contour], 255)
        
        return mask, detection_result
    
    def create_enhanced_mask(self, image: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """创建增强mask（包含形态学处理）"""
        mask, detection_result = self.create_basic_mask(image)
        
        if np.any(mask):
            # 形态学处理
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, 
                                             (self.morph_kernel_size, self.morph_kernel_size))
            
            # 闭运算：填充小洞
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, 
                                  iterations=self.morph_iterations)
            
            # 开运算：去除小噪点
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
            
            # 可选的膨胀操作
            if self.dilate_iterations > 0:
                mask = cv2.dilate(mask, kernel, iterations=self.dilate_iterations)
        
        return mask, detection_result
    
    def create_blurred_mask(self, image: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """创建模糊边缘的mask"""
        mask, detection_result = self.create_enhanced_mask(image)
        
        if np.any(mask) and self.blur_kernel > 0:
            # 高斯模糊创建软边缘
            mask = cv2.GaussianBlur(mask, (self.blur_kernel, self.blur_kernel), 0)
        
        return mask, detection_result
    
    def create_visualization(self, image: np.ndarray, mask: np.ndarray, 
                           detection_result: Dict[str, Any]) -> np.ndarray:
        """创建可视化图像"""
        # 创建彩色mask
        colored_mask = np.zeros_like(image)
        colored_mask[mask > 0] = [0, 255, 0]  # 绿色
        
        # 叠加图像
        overlay = cv2.addWeighted(image, 0.7, colored_mask, 0.3, 0)
        
        # 绘制边界框
        for bbox in detection_result['bounding_boxes']:
            x, y, w, h = bbox
            cv2.rectangle(overlay, (x, y), (x+w, y+h), (0, 255, 0), 2)
            # 添加面积标签
            area = w * h
            cv2.putText(overlay, f"{area}", (x, y-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # 添加统计信息
        info_lines = [
            f"Light Points: {detection_result['count']}",
            f"Total Area: {detection_result['total_area']:.0f}",
            f"Morph Kernel: {self.morph_kernel_size}",
            f"Morph Iter: {self.morph_iterations}"
        ]
        
        for i, line in enumerate(info_lines):
            y_pos = 30 + i * 25
            cv2.putText(overlay, line, (10, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        return overlay
    
    def process_image_interactive(self, image_path: str) -> bool:
        """交互式处理单张图片"""
        print(f"\n=== 处理图片: {os.path.basename(image_path)} ===")
        
        # 读取图片
        image = cv2.imread(image_path)
        if image is None:
            print(f"[ERROR] 无法读取图片: {image_path}")
            return False
        
        print(f"图片尺寸: {image.shape[1]}x{image.shape[0]}")
        
        # 创建窗口
        cv2.namedWindow('Original', cv2.WINDOW_NORMAL)
        cv2.namedWindow('Mask', cv2.WINDOW_NORMAL)
        cv2.namedWindow('Overlay', cv2.WINDOW_NORMAL)
        cv2.namedWindow('Controls', cv2.WINDOW_NORMAL)
        
        # 调整窗口大小
        cv2.resizeWindow('Original', 400, 300)
        cv2.resizeWindow('Mask', 400, 300)
        cv2.resizeWindow('Overlay', 400, 300)
        cv2.resizeWindow('Controls', 400, 200)
        
        # 创建控制面板
        controls = np.zeros((200, 400, 3), dtype=np.uint8)
        
        def update_display():
            """更新显示"""
            mask, detection_result = self.create_enhanced_mask(image)
            overlay = self.create_visualization(image, mask, detection_result)
            
            # 更新控制面板
            controls.fill(0)
            control_lines = [
                "Controls:",
                f"Kernel Size: {self.morph_kernel_size} (1/2 to change)",
                f"Morph Iter: {self.morph_iterations} (3/4 to change)",
                f"Dilate Iter: {self.dilate_iterations} (5/6 to change)",
                f"Blur Kernel: {self.blur_kernel} (7/8 to change)",
                "",
                "S - Save mask    Q - Quit    R - Reset"
            ]
            
            for i, line in enumerate(control_lines):
                cv2.putText(controls, line, (10, 25 + i * 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            cv2.imshow('Original', image)
            cv2.imshow('Mask', mask)
            cv2.imshow('Overlay', overlay)
            cv2.imshow('Controls', controls)
            
            return mask, detection_result
        
        # 初始显示
        current_mask, current_detection = update_display()
        
        print("\n交互式调整:")
        print("  1/2 - 调整形态学核大小")
        print("  3/4 - 调整形态学迭代次数")
        print("  5/6 - 调整膨胀迭代次数")
        print("  7/8 - 调整模糊核大小")
        print("  R - 重置参数")
        print("  S - 保存mask")
        print("  Q - 退出")
        
        while True:
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('1') and self.morph_kernel_size > 1:
                self.morph_kernel_size -= 2
                current_mask, current_detection = update_display()
            elif key == ord('2'):
                self.morph_kernel_size += 2
                current_mask, current_detection = update_display()
            elif key == ord('3') and self.morph_iterations > 0:
                self.morph_iterations -= 1
                current_mask, current_detection = update_display()
            elif key == ord('4'):
                self.morph_iterations += 1
                current_mask, current_detection = update_display()
            elif key == ord('5') and self.dilate_iterations > 0:
                self.dilate_iterations -= 1
                current_mask, current_detection = update_display()
            elif key == ord('6'):
                self.dilate_iterations += 1
                current_mask, current_detection = update_display()
            elif key == ord('7') and self.blur_kernel > 0:
                self.blur_kernel = max(0, self.blur_kernel - 2)
                current_mask, current_detection = update_display()
            elif key == ord('8'):
                self.blur_kernel += 2
                current_mask, current_detection = update_display()
            elif key == ord('r'):
                # 重置参数
                self.morph_kernel_size = 5
                self.morph_iterations = 2
                self.dilate_iterations = 1
                self.blur_kernel = 3
                current_mask, current_detection = update_display()
                print("[INFO] 参数已重置")
            elif key == ord('s'):
                # 保存mask
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                
                # 保存不同版本的mask
                basic_mask, _ = self.create_basic_mask(image)
                enhanced_mask, _ = self.create_enhanced_mask(image)
                blurred_mask, _ = self.create_blurred_mask(image)
                overlay = self.create_visualization(image, enhanced_mask, current_detection)
                
                cv2.imwrite(f"{base_name}_mask_basic.png", basic_mask)
                cv2.imwrite(f"{base_name}_mask_enhanced.png", enhanced_mask)
                cv2.imwrite(f"{base_name}_mask_blurred.png", blurred_mask)
                cv2.imwrite(f"{base_name}_overlay.png", overlay)
                
                # 保存参数
                params = {
                    'morph_kernel_size': self.morph_kernel_size,
                    'morph_iterations': self.morph_iterations,
                    'dilate_iterations': self.dilate_iterations,
                    'blur_kernel': self.blur_kernel,
                    'detection_result': {
                        'count': current_detection['count'],
                        'total_area': float(current_detection['total_area'])
                    }
                }
                
                with open(f"{base_name}_mask_params.json", 'w') as f:
                    json.dump(params, f, indent=2)
                
                print(f"[OK] 已保存:")
                print(f"  - {base_name}_mask_basic.png")
                print(f"  - {base_name}_mask_enhanced.png")
                print(f"  - {base_name}_mask_blurred.png")
                print(f"  - {base_name}_overlay.png")
                print(f"  - {base_name}_mask_params.json")
                break
            elif key == ord('q') or key == 27:
                print("[INFO] 用户取消")
                break
        
        cv2.destroyAllWindows()
        return True

def main():
    """主函数"""
    print("=== 高级光点区域mask创建工具 ===")
    print()
    
    # 查找图片文件
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff']
    image_files = []
    
    for ext in image_extensions:
        image_files.extend(glob.glob(ext))
        image_files.extend(glob.glob(ext.upper()))
    
    if not image_files:
        print("当前目录没有找到图片文件")
        print("支持的格式: JPG, PNG, BMP, TIFF")
        return 1
    
    print(f"发现 {len(image_files)} 个图片文件:")
    for i, file in enumerate(image_files, 1):
        print(f"  {i}. {file}")
    print()
    
    try:
        creator = AdvancedMaskCreator()
        
        if len(image_files) == 1:
            # 单个文件直接处理
            creator.process_image_interactive(image_files[0])
        else:
            # 多个文件选择处理
            choice = input("请输入文件编号 (1-{}) 或 'a' 处理所有文件: ".format(len(image_files))).strip()
            
            if choice.lower() == 'a':
                # 批量处理
                for image_file in image_files:
                    creator.process_image_interactive(image_file)
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(image_files):
                    creator.process_image_interactive(image_files[idx])
                else:
                    print("[ERROR] 无效的文件编号")
                    return 1
            else:
                print("[ERROR] 无效的选择")
                return 1
        
        print("\n[OK] 处理完成")
        return 0
        
    except KeyboardInterrupt:
        print("\n[INFO] 用户中断")
        return 0
    except Exception as e:
        print(f"\n[ERROR] 程序错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
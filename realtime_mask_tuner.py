#!/usr/bin/env python3
"""
实时mask调参工具 - 提供滑动条控制和实时预览
"""

import cv2
import numpy as np
import os
import sys
import glob
import json
from typing import List, Tuple, Dict, Any, Optional
from mqtt_camera_monitoring.config import ConfigManager
from mqtt_camera_monitoring.light_detector import RedLightDetector

class RealtimeMaskTuner:
    """实时mask调参器"""
    
    def __init__(self, config_file: str = "config.yaml"):
        """初始化"""
        self.config_manager = ConfigManager(config_file)
        self.config = self.config_manager.load_config()
        
        # 当前图片和结果
        self.current_image = None
        self.current_mask = None
        self.current_detection = None
        
        # 可调参数 - 使用滑动条控制
        self.params = {
            # HSV参数
            'lower_h1': 0,      # 红色HSV范围1 - 色相下限
            'upper_h1': 18,     # 红色HSV范围1 - 色相上限
            'lower_s1': 25,     # 红色HSV范围1 - 饱和度下限
            'lower_v1': 25,     # 红色HSV范围1 - 亮度下限
            'upper_s1': 255,    # 红色HSV范围1 - 饱和度上限
            'upper_v1': 255,    # 红色HSV范围1 - 亮度上限
            
            'lower_h2': 160,    # 红色HSV范围2 - 色相下限
            'upper_h2': 180,    # 红色HSV范围2 - 色相上限
            'lower_s2': 25,     # 红色HSV范围2 - 饱和度下限
            'lower_v2': 25,     # 红色HSV范围2 - 亮度下限
            'upper_s2': 255,    # 红色HSV范围2 - 饱和度上限
            'upper_v2': 255,    # 红色HSV范围2 - 亮度上限
            
            # 处理参数
            'brightness_thresh': 30,    # 亮度阈值
            'min_area': 3,              # 最小轮廓面积
            'max_area': 800,            # 最大轮廓面积 (缩放到800以适应滑动条)
            'gaussian_blur': 1,         # 高斯模糊核大小
            'morph_kernel': 2,          # 形态学核大小
            'morph_iter': 1,            # 形态学迭代次数
            'erosion_iter': 0,          # 腐蚀迭代次数
            
            # 后处理参数
            'close_iter': 2,            # 闭运算迭代次数
            'open_iter': 1,             # 开运算迭代次数
            'dilate_iter': 0,           # 膨胀迭代次数
            'final_blur': 0,            # 最终模糊
        }
        
        # 窗口名称
        self.main_window = "Realtime Mask Tuner"
        self.control_window = "Controls"
        
        # 创建窗口
        cv2.namedWindow(self.main_window, cv2.WINDOW_NORMAL)
        cv2.namedWindow(self.control_window, cv2.WINDOW_NORMAL)
        
        # 设置窗口大小
        cv2.resizeWindow(self.main_window, 1200, 800)
        cv2.resizeWindow(self.control_window, 400, 800)
        
        # 创建滑动条
        self._create_trackbars()
        
    def _create_trackbars(self):
        """创建滑动条"""
        # HSV范围1参数
        cv2.createTrackbar('H1_Min', self.control_window, self.params['lower_h1'], 179, self._on_trackbar_change)
        cv2.createTrackbar('H1_Max', self.control_window, self.params['upper_h1'], 179, self._on_trackbar_change)
        cv2.createTrackbar('S1_Min', self.control_window, self.params['lower_s1'], 255, self._on_trackbar_change)
        cv2.createTrackbar('S1_Max', self.control_window, self.params['upper_s1'], 255, self._on_trackbar_change)
        cv2.createTrackbar('V1_Min', self.control_window, self.params['lower_v1'], 255, self._on_trackbar_change)
        cv2.createTrackbar('V1_Max', self.control_window, self.params['upper_v1'], 255, self._on_trackbar_change)
        
        # HSV范围2参数
        cv2.createTrackbar('H2_Min', self.control_window, self.params['lower_h2'], 179, self._on_trackbar_change)
        cv2.createTrackbar('H2_Max', self.control_window, self.params['upper_h2'], 179, self._on_trackbar_change)
        cv2.createTrackbar('S2_Min', self.control_window, self.params['lower_s2'], 255, self._on_trackbar_change)
        cv2.createTrackbar('S2_Max', self.control_window, self.params['upper_s2'], 255, self._on_trackbar_change)
        cv2.createTrackbar('V2_Min', self.control_window, self.params['lower_v2'], 255, self._on_trackbar_change)
        cv2.createTrackbar('V2_Max', self.control_window, self.params['upper_v2'], 255, self._on_trackbar_change)
        
        # 处理参数
        cv2.createTrackbar('Brightness', self.control_window, self.params['brightness_thresh'], 255, self._on_trackbar_change)
        cv2.createTrackbar('Min_Area', self.control_window, self.params['min_area'], 100, self._on_trackbar_change)
        cv2.createTrackbar('Max_Area', self.control_window, self.params['max_area'], 2000, self._on_trackbar_change)
        cv2.createTrackbar('Blur', self.control_window, self.params['gaussian_blur'], 15, self._on_trackbar_change)
        cv2.createTrackbar('Morph_K', self.control_window, self.params['morph_kernel'], 15, self._on_trackbar_change)
        cv2.createTrackbar('Morph_I', self.control_window, self.params['morph_iter'], 10, self._on_trackbar_change)
        cv2.createTrackbar('Erosion', self.control_window, self.params['erosion_iter'], 10, self._on_trackbar_change)
        
        # 后处理参数
        cv2.createTrackbar('Close', self.control_window, self.params['close_iter'], 10, self._on_trackbar_change)
        cv2.createTrackbar('Open', self.control_window, self.params['open_iter'], 10, self._on_trackbar_change)
        cv2.createTrackbar('Dilate', self.control_window, self.params['dilate_iter'], 10, self._on_trackbar_change)
        cv2.createTrackbar('Final_Blur', self.control_window, self.params['final_blur'], 15, self._on_trackbar_change)
    
    def _on_trackbar_change(self, val):
        """滑动条变化回调"""
        # 更新参数
        self.params['lower_h1'] = cv2.getTrackbarPos('H1_Min', self.control_window)
        self.params['upper_h1'] = cv2.getTrackbarPos('H1_Max', self.control_window)
        self.params['lower_s1'] = cv2.getTrackbarPos('S1_Min', self.control_window)
        self.params['upper_s1'] = cv2.getTrackbarPos('S1_Max', self.control_window)
        self.params['lower_v1'] = cv2.getTrackbarPos('V1_Min', self.control_window)
        self.params['upper_v1'] = cv2.getTrackbarPos('V1_Max', self.control_window)
        
        self.params['lower_h2'] = cv2.getTrackbarPos('H2_Min', self.control_window)
        self.params['upper_h2'] = cv2.getTrackbarPos('H2_Max', self.control_window)
        self.params['lower_s2'] = cv2.getTrackbarPos('S2_Min', self.control_window)
        self.params['upper_s2'] = cv2.getTrackbarPos('S2_Max', self.control_window)
        self.params['lower_v2'] = cv2.getTrackbarPos('V2_Min', self.control_window)
        self.params['upper_v2'] = cv2.getTrackbarPos('V2_Max', self.control_window)
        
        self.params['brightness_thresh'] = cv2.getTrackbarPos('Brightness', self.control_window)
        self.params['min_area'] = cv2.getTrackbarPos('Min_Area', self.control_window)
        self.params['max_area'] = cv2.getTrackbarPos('Max_Area', self.control_window)
        self.params['gaussian_blur'] = cv2.getTrackbarPos('Blur', self.control_window)
        self.params['morph_kernel'] = cv2.getTrackbarPos('Morph_K', self.control_window)
        self.params['morph_iter'] = cv2.getTrackbarPos('Morph_I', self.control_window)
        self.params['erosion_iter'] = cv2.getTrackbarPos('Erosion', self.control_window)
        
        self.params['close_iter'] = cv2.getTrackbarPos('Close', self.control_window)
        self.params['open_iter'] = cv2.getTrackbarPos('Open', self.control_window)
        self.params['dilate_iter'] = cv2.getTrackbarPos('Dilate', self.control_window)
        self.params['final_blur'] = cv2.getTrackbarPos('Final_Blur', self.control_window)
        
        # 实时更新显示
        if self.current_image is not None:
            self._update_display()
    
    def _detect_red_lights_custom(self, image: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """使用自定义参数检测红光"""
        if image is None or image.size == 0:
            return np.zeros(image.shape[:2], dtype=np.uint8), {'count': 0, 'total_area': 0, 'contours': [], 'bounding_boxes': []}
        
        # 预处理 - 高斯模糊
        if self.params['gaussian_blur'] > 0:
            kernel_size = max(1, self.params['gaussian_blur'])
            if kernel_size % 2 == 0:
                kernel_size += 1
            blurred = cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
        else:
            blurred = image.copy()
        
        # 转换到HSV
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        
        # 创建HSV mask
        lower_red_1 = np.array([self.params['lower_h1'], self.params['lower_s1'], self.params['lower_v1']], dtype=np.uint8)
        upper_red_1 = np.array([self.params['upper_h1'], self.params['upper_s1'], self.params['upper_v1']], dtype=np.uint8)
        lower_red_2 = np.array([self.params['lower_h2'], self.params['lower_s2'], self.params['lower_v2']], dtype=np.uint8)
        upper_red_2 = np.array([self.params['upper_h2'], self.params['upper_s2'], self.params['upper_v2']], dtype=np.uint8)
        
        mask1 = cv2.inRange(hsv, lower_red_1, upper_red_1)
        mask2 = cv2.inRange(hsv, lower_red_2, upper_red_2)
        red_mask = cv2.bitwise_or(mask1, mask2)
        
        # 亮度过滤
        if self.params['brightness_thresh'] > 0:
            brightness_mask = hsv[:, :, 2] > self.params['brightness_thresh']
            red_mask = cv2.bitwise_and(red_mask, brightness_mask.astype(np.uint8) * 255)
        
        # 形态学处理
        if self.params['morph_kernel'] > 0 and self.params['morph_iter'] > 0:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, 
                                             (self.params['morph_kernel'], self.params['morph_kernel']))
            red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel, 
                                      iterations=self.params['morph_iter'])
        
        # 腐蚀
        if self.params['erosion_iter'] > 0 and self.params['morph_kernel'] > 0:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, 
                                             (self.params['morph_kernel'], self.params['morph_kernel']))
            red_mask = cv2.erode(red_mask, kernel, iterations=self.params['erosion_iter'])
        
        # 后处理
        if self.params['morph_kernel'] > 0:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, 
                                             (self.params['morph_kernel'], self.params['morph_kernel']))
            
            # 闭运算
            if self.params['close_iter'] > 0:
                red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel, 
                                          iterations=self.params['close_iter'])
            
            # 开运算
            if self.params['open_iter'] > 0:
                red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel, 
                                          iterations=self.params['open_iter'])
            
            # 膨胀
            if self.params['dilate_iter'] > 0:
                red_mask = cv2.dilate(red_mask, kernel, iterations=self.params['dilate_iter'])
        
        # 最终模糊
        if self.params['final_blur'] > 0:
            kernel_size = max(1, self.params['final_blur'])
            if kernel_size % 2 == 0:
                kernel_size += 1
            red_mask = cv2.GaussianBlur(red_mask, (kernel_size, kernel_size), 0)
        
        # 查找轮廓
        contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 过滤轮廓
        valid_contours = []
        bounding_boxes = []
        total_area = 0.0
        
        min_area = self.params['min_area']
        max_area = self.params['max_area'] * 100  # 恢复实际大小
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if min_area <= area <= max_area:
                valid_contours.append(contour)
                total_area += area
                x, y, w, h = cv2.boundingRect(contour)
                bounding_boxes.append((x, y, w, h))
        
        detection_result = {
            'count': len(valid_contours),
            'total_area': total_area,
            'contours': valid_contours,
            'bounding_boxes': bounding_boxes
        }
        
        return red_mask, detection_result
    
    def _update_display(self):
        """更新显示"""
        if self.current_image is None:
            return
        
        # 执行检测
        mask, detection = self._detect_red_lights_custom(self.current_image)
        self.current_mask = mask
        self.current_detection = detection
        
        # 创建显示图像
        h, w = self.current_image.shape[:2]
        
        # 创建四个子图：原图、HSV、mask、叠加
        display_h = h // 2
        display_w = w // 2
        
        # 调整图像大小
        original_small = cv2.resize(self.current_image, (display_w, display_h))
        
        # HSV图像
        hsv = cv2.cvtColor(self.current_image, cv2.COLOR_BGR2HSV)
        hsv_small = cv2.resize(hsv, (display_w, display_h))
        
        # Mask图像
        mask_colored = cv2.applyColorMap(mask, cv2.COLORMAP_JET)
        mask_small = cv2.resize(mask_colored, (display_w, display_h))
        
        # 叠加图像
        overlay = self.current_image.copy()
        
        # 绘制检测结果
        for contour in detection['contours']:
            cv2.fillPoly(overlay, [contour], (0, 255, 0))
        
        for bbox in detection['bounding_boxes']:
            x, y, w, h = bbox
            cv2.rectangle(overlay, (x, y), (x+w, y+h), (0, 255, 0), 2)
            # 添加面积标签
            area = cv2.contourArea(detection['contours'][detection['bounding_boxes'].index(bbox)])
            cv2.putText(overlay, f"{int(area)}", (x, y-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # 添加统计信息
        info_text = f"Count: {detection['count']}, Area: {detection['total_area']:.0f}"
        cv2.putText(overlay, info_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        overlay_small = cv2.resize(overlay, (display_w, display_h))
        
        # 组合四个子图
        top_row = np.hstack([original_small, hsv_small])
        bottom_row = np.hstack([mask_small, overlay_small])
        combined = np.vstack([top_row, bottom_row])
        
        # 添加标签
        cv2.putText(combined, "Original", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(combined, "HSV", (display_w + 10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(combined, "Mask", (10, display_h + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(combined, "Result", (display_w + 10, display_h + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.imshow(self.main_window, combined)
    
    def load_image(self, image_path: str) -> bool:
        """加载图片"""
        image = cv2.imread(image_path)
        if image is None:
            print(f"[ERROR] 无法读取图片: {image_path}")
            return False
        
        self.current_image = image
        self._update_display()
        print(f"[OK] 已加载图片: {os.path.basename(image_path)}")
        print(f"图片尺寸: {image.shape[1]}x{image.shape[0]}")
        return True
    
    def save_results(self, base_name: str):
        """保存结果"""
        if self.current_image is None or self.current_mask is None:
            print("[ERROR] 没有可保存的结果")
            return False
        
        # 保存mask
        cv2.imwrite(f"{base_name}_mask.png", self.current_mask)
        
        # 保存叠加图像
        overlay = self.current_image.copy()
        colored_mask = np.zeros_like(self.current_image)
        colored_mask[self.current_mask > 0] = [0, 255, 0]
        overlay = cv2.addWeighted(self.current_image, 0.7, colored_mask, 0.3, 0)
        
        for bbox in self.current_detection['bounding_boxes']:
            x, y, w, h = bbox
            cv2.rectangle(overlay, (x, y), (x+w, y+h), (0, 255, 0), 2)
        
        cv2.imwrite(f"{base_name}_overlay.png", overlay)
        
        # 保存参数
        params_to_save = self.params.copy()
        params_to_save['detection_result'] = {
            'count': self.current_detection['count'],
            'total_area': float(self.current_detection['total_area'])
        }
        
        with open(f"{base_name}_params.json", 'w') as f:
            json.dump(params_to_save, f, indent=2)
        
        print(f"[OK] 已保存:")
        print(f"  - {base_name}_mask.png")
        print(f"  - {base_name}_overlay.png")
        print(f"  - {base_name}_params.json")
        return True
    
    def run(self):
        """运行调参器"""
        print("=== 实时mask调参工具 ===")
        print("控制说明:")
        print("  使用滑动条调整参数")
        print("  S - 保存当前结果")
        print("  R - 重置参数")
        print("  Q - 退出")
        print("  1-9 - 快速切换图片")
        print()
        
        # 查找图片文件
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff']
        image_files = []
        
        for ext in image_extensions:
            image_files.extend(glob.glob(ext))
            image_files.extend(glob.glob(ext.upper()))
        
        if not image_files:
            print("[ERROR] 当前目录没有找到图片文件")
            return False
        
        print(f"发现 {len(image_files)} 个图片文件:")
        for i, file in enumerate(image_files[:9], 1):  # 最多显示9个
            print(f"  {i}. {file}")
        print()
        
        # 加载第一个图片
        current_image_index = 0
        if not self.load_image(image_files[current_image_index]):
            return False
        
        while True:
            key = cv2.waitKey(30) & 0xFF
            
            if key == ord('q') or key == 27:  # 'q' 或 ESC
                print("[INFO] 退出程序")
                break
            elif key == ord('s'):
                # 保存结果
                base_name = os.path.splitext(os.path.basename(image_files[current_image_index]))[0]
                self.save_results(base_name)
            elif key == ord('r'):
                # 重置参数
                self._reset_parameters()
                print("[INFO] 参数已重置")
            elif ord('1') <= key <= ord('9'):
                # 切换图片
                img_index = key - ord('1')
                if img_index < len(image_files):
                    current_image_index = img_index
                    self.load_image(image_files[current_image_index])
        
        cv2.destroyAllWindows()
        return True
    
    def _reset_parameters(self):
        """重置参数到默认值"""
        # 重置参数
        self.params = {
            'lower_h1': 0, 'upper_h1': 18, 'lower_s1': 25, 'lower_v1': 25, 'upper_s1': 255, 'upper_v1': 255,
            'lower_h2': 160, 'upper_h2': 180, 'lower_s2': 25, 'lower_v2': 25, 'upper_s2': 255, 'upper_v2': 255,
            'brightness_thresh': 30, 'min_area': 3, 'max_area': 800, 'gaussian_blur': 1,
            'morph_kernel': 2, 'morph_iter': 1, 'erosion_iter': 0,
            'close_iter': 2, 'open_iter': 1, 'dilate_iter': 0, 'final_blur': 0,
        }
        
        # 更新滑动条
        for param, value in self.params.items():
            trackbar_names = {
                'lower_h1': 'H1_Min', 'upper_h1': 'H1_Max', 'lower_s1': 'S1_Min', 'upper_s1': 'S1_Max',
                'lower_v1': 'V1_Min', 'upper_v1': 'V1_Max', 'lower_h2': 'H2_Min', 'upper_h2': 'H2_Max',
                'lower_s2': 'S2_Min', 'upper_s2': 'S2_Max', 'lower_v2': 'V2_Min', 'upper_v2': 'V2_Max',
                'brightness_thresh': 'Brightness', 'min_area': 'Min_Area', 'max_area': 'Max_Area',
                'gaussian_blur': 'Blur', 'morph_kernel': 'Morph_K', 'morph_iter': 'Morph_I',
                'erosion_iter': 'Erosion', 'close_iter': 'Close', 'open_iter': 'Open',
                'dilate_iter': 'Dilate', 'final_blur': 'Final_Blur'
            }
            
            if param in trackbar_names:
                cv2.setTrackbarPos(trackbar_names[param], self.control_window, value)

def main():
    """主函数"""
    try:
        tuner = RealtimeMaskTuner()
        tuner.run()
        return 0
    except KeyboardInterrupt:
        print("\n[INFO] 用户中断")
        return 0
    except Exception as e:
        print(f"\n[ERROR] 程序错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
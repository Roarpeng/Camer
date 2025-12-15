#!/usr/bin/env python3
"""
快速mask调参工具 - 简化版本，专注于核心参数调整
"""

import cv2
import numpy as np
import os
import sys
import glob

class QuickMaskTuner:
    """快速mask调参器"""
    
    def __init__(self):
        """初始化"""
        self.current_image = None
        self.window_name = "Quick Mask Tuner"
        
        # 核心参数
        self.hsv_lower = [0, 25, 25]      # HSV下限
        self.hsv_upper = [18, 255, 255]   # HSV上限
        self.hsv_lower2 = [160, 25, 25]   # HSV下限2
        self.hsv_upper2 = [180, 255, 255] # HSV上限2
        self.min_area = 3                 # 最小面积
        self.blur_size = 1                # 模糊大小
        self.morph_size = 2               # 形态学核大小
        
        # 创建窗口和滑动条
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 1000, 700)
        
        # 创建滑动条
        cv2.createTrackbar('H_Min', self.window_name, self.hsv_lower[0], 179, self._update)
        cv2.createTrackbar('H_Max', self.window_name, self.hsv_upper[0], 179, self._update)
        cv2.createTrackbar('S_Min', self.window_name, self.hsv_lower[1], 255, self._update)
        cv2.createTrackbar('S_Max', self.window_name, self.hsv_upper[1], 255, self._update)
        cv2.createTrackbar('V_Min', self.window_name, self.hsv_lower[2], 255, self._update)
        cv2.createTrackbar('V_Max', self.window_name, self.hsv_upper[2], 255, self._update)
        
        cv2.createTrackbar('H2_Min', self.window_name, self.hsv_lower2[0], 179, self._update)
        cv2.createTrackbar('H2_Max', self.window_name, self.hsv_upper2[0], 179, self._update)
        cv2.createTrackbar('S2_Min', self.window_name, self.hsv_lower2[1], 255, self._update)
        cv2.createTrackbar('S2_Max', self.window_name, self.hsv_upper2[1], 255, self._update)
        cv2.createTrackbar('V2_Min', self.window_name, self.hsv_lower2[2], 255, self._update)
        cv2.createTrackbar('V2_Max', self.window_name, self.hsv_upper2[2], 255, self._update)
        
        cv2.createTrackbar('Min_Area', self.window_name, self.min_area, 100, self._update)
        cv2.createTrackbar('Blur', self.window_name, self.blur_size, 15, self._update)
        cv2.createTrackbar('Morph', self.window_name, self.morph_size, 15, self._update)
    
    def _update(self, val=None):
        """更新显示"""
        if self.current_image is None:
            return
        
        # 获取滑动条值
        self.hsv_lower[0] = cv2.getTrackbarPos('H_Min', self.window_name)
        self.hsv_upper[0] = cv2.getTrackbarPos('H_Max', self.window_name)
        self.hsv_lower[1] = cv2.getTrackbarPos('S_Min', self.window_name)
        self.hsv_upper[1] = cv2.getTrackbarPos('S_Max', self.window_name)
        self.hsv_lower[2] = cv2.getTrackbarPos('V_Min', self.window_name)
        self.hsv_upper[2] = cv2.getTrackbarPos('V_Max', self.window_name)
        
        self.hsv_lower2[0] = cv2.getTrackbarPos('H2_Min', self.window_name)
        self.hsv_upper2[0] = cv2.getTrackbarPos('H2_Max', self.window_name)
        self.hsv_lower2[1] = cv2.getTrackbarPos('S2_Min', self.window_name)
        self.hsv_upper2[1] = cv2.getTrackbarPos('S2_Max', self.window_name)
        self.hsv_lower2[2] = cv2.getTrackbarPos('V2_Min', self.window_name)
        self.hsv_upper2[2] = cv2.getTrackbarPos('V2_Max', self.window_name)
        
        self.min_area = cv2.getTrackbarPos('Min_Area', self.window_name)
        self.blur_size = cv2.getTrackbarPos('Blur', self.window_name)
        self.morph_size = cv2.getTrackbarPos('Morph', self.window_name)
        
        # 处理图像
        processed = self._process_image()
        
        # 显示结果
        cv2.imshow(self.window_name, processed)
    
    def _process_image(self):
        """处理图像并返回结果"""
        image = self.current_image.copy()
        h, w = image.shape[:2]
        
        # 预处理
        if self.blur_size > 0:
            blur_kernel = max(1, self.blur_size)
            if blur_kernel % 2 == 0:
                blur_kernel += 1
            blurred = cv2.GaussianBlur(image, (blur_kernel, blur_kernel), 0)
        else:
            blurred = image.copy()
        
        # HSV转换
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        
        # 创建mask
        lower1 = np.array(self.hsv_lower, dtype=np.uint8)
        upper1 = np.array(self.hsv_upper, dtype=np.uint8)
        lower2 = np.array(self.hsv_lower2, dtype=np.uint8)
        upper2 = np.array(self.hsv_upper2, dtype=np.uint8)
        
        mask1 = cv2.inRange(hsv, lower1, upper1)
        mask2 = cv2.inRange(hsv, lower2, upper2)
        mask = cv2.bitwise_or(mask1, mask2)
        
        # 形态学处理
        if self.morph_size > 0:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (self.morph_size, self.morph_size))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # 查找轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 过滤轮廓
        valid_contours = []
        total_area = 0
        for contour in contours:
            area = cv2.contourArea(contour)
            if area >= self.min_area:
                valid_contours.append(contour)
                total_area += area
        
        # 创建显示图像 (2x2布局)
        display_h = h // 2
        display_w = w // 2
        
        # 原图
        original_small = cv2.resize(image, (display_w, display_h))
        
        # HSV图
        hsv_display = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        hsv_small = cv2.resize(hsv_display, (display_w, display_h))
        
        # Mask图
        mask_colored = cv2.applyColorMap(mask, cv2.COLORMAP_JET)
        mask_small = cv2.resize(mask_colored, (display_w, display_h))
        
        # 结果图
        result = image.copy()
        
        # 绘制轮廓和边界框
        for contour in valid_contours:
            # 填充轮廓
            cv2.fillPoly(result, [contour], (0, 255, 0))
            
            # 绘制边界框
            x, y, w_box, h_box = cv2.boundingRect(contour)
            cv2.rectangle(result, (x, y), (x+w_box, y+h_box), (0, 255, 0), 2)
            
            # 添加面积标签
            area = cv2.contourArea(contour)
            cv2.putText(result, f"{int(area)}", (x, y-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # 添加统计信息
        info_text = f"Count: {len(valid_contours)}, Total Area: {total_area:.0f}"
        cv2.putText(result, info_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        # 添加参数信息
        param_text = f"HSV1:[{self.hsv_lower[0]}-{self.hsv_upper[0]},{self.hsv_lower[1]}-{self.hsv_upper[1]},{self.hsv_lower[2]}-{self.hsv_upper[2]}]"
        cv2.putText(result, param_text, (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        param_text2 = f"HSV2:[{self.hsv_lower2[0]}-{self.hsv_upper2[0]},{self.hsv_lower2[1]}-{self.hsv_upper2[1]},{self.hsv_lower2[2]}-{self.hsv_upper2[2]}]"
        cv2.putText(result, param_text2, (10, 80), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        result_small = cv2.resize(result, (display_w, display_h))
        
        # 组合四个子图
        top_row = np.hstack([original_small, hsv_small])
        bottom_row = np.hstack([mask_small, result_small])
        combined = np.vstack([top_row, bottom_row])
        
        # 添加标签
        cv2.putText(combined, "Original", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(combined, "HSV", (display_w + 10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(combined, "Mask", (10, display_h + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(combined, "Result", (display_w + 10, display_h + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        return combined
    
    def load_image(self, image_path):
        """加载图片"""
        image = cv2.imread(image_path)
        if image is None:
            print(f"[ERROR] 无法读取图片: {image_path}")
            return False
        
        self.current_image = image
        self._update()
        print(f"[OK] 已加载: {os.path.basename(image_path)} ({image.shape[1]}x{image.shape[0]})")
        return True
    
    def save_mask(self, output_path):
        """保存当前mask"""
        if self.current_image is None:
            return False
        
        # 重新生成mask
        if self.blur_size > 0:
            blur_kernel = max(1, self.blur_size)
            if blur_kernel % 2 == 0:
                blur_kernel += 1
            blurred = cv2.GaussianBlur(self.current_image, (blur_kernel, blur_kernel), 0)
        else:
            blurred = self.current_image.copy()
        
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        
        lower1 = np.array(self.hsv_lower, dtype=np.uint8)
        upper1 = np.array(self.hsv_upper, dtype=np.uint8)
        lower2 = np.array(self.hsv_lower2, dtype=np.uint8)
        upper2 = np.array(self.hsv_upper2, dtype=np.uint8)
        
        mask1 = cv2.inRange(hsv, lower1, upper1)
        mask2 = cv2.inRange(hsv, lower2, upper2)
        mask = cv2.bitwise_or(mask1, mask2)
        
        if self.morph_size > 0:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (self.morph_size, self.morph_size))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        cv2.imwrite(output_path, mask)
        print(f"[OK] Mask已保存: {output_path}")
        return True
    
    def run(self):
        """运行调参器"""
        print("=== 快速mask调参工具 ===")
        print("使用滑动条调整参数，实时预览效果")
        print("按键说明:")
        print("  S - 保存mask")
        print("  Q - 退出")
        print("  1-9 - 切换图片")
        print()
        
        # 查找图片
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp']:
            image_files.extend(glob.glob(ext))
            image_files.extend(glob.glob(ext.upper()))
        
        if not image_files:
            print("[ERROR] 未找到图片文件")
            return False
        
        print(f"发现图片文件:")
        for i, file in enumerate(image_files[:9], 1):
            print(f"  {i}. {file}")
        print()
        
        # 加载第一张图片
        current_index = 0
        if not self.load_image(image_files[current_index]):
            return False
        
        while True:
            key = cv2.waitKey(30) & 0xFF
            
            if key == ord('q') or key == 27:
                break
            elif key == ord('s'):
                base_name = os.path.splitext(image_files[current_index])[0]
                self.save_mask(f"{base_name}_mask.png")
            elif ord('1') <= key <= ord('9'):
                img_idx = key - ord('1')
                if img_idx < len(image_files):
                    current_index = img_idx
                    self.load_image(image_files[current_index])
        
        cv2.destroyAllWindows()
        return True

def main():
    try:
        tuner = QuickMaskTuner()
        tuner.run()
        return 0
    except Exception as e:
        print(f"[ERROR] {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
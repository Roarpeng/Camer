#!/usr/bin/env python3
"""
红色检测参数调试工具
实时调整HSV参数和红色比例阈值
"""

import cv2
import numpy as np
import os
import sys
from typing import List, Tuple

class RedDetectionTuner:
    """红色检测参数调试器"""
    
    def __init__(self, mask_file: str = "mask.png"):
        self.mask_file = mask_file
        self.mask_image = None
        self.light_points_template = []
        
        # 红色检测参数 - 初始值
        self.h_min1 = 0
        self.s_min1 = 30
        self.v_min1 = 30
        self.h_max1 = 25
        self.s_max1 = 255
        self.v_max1 = 255
        
        self.h_min2 = 155
        self.s_min2 = 30
        self.v_min2 = 30
        self.h_max2 = 180
        self.s_max2 = 255
        self.v_max2 = 255
        
        self.red_ratio_threshold = 10  # 百分比
        
        if not self._load_mask():
            raise ValueError(f"无法加载mask文件: {mask_file}")
        
        self._create_trackbars()
    
    def _load_mask(self) -> bool:
        """加载mask图片并识别光点"""
        if not os.path.exists(self.mask_file):
            print(f"[ERROR] Mask文件不存在: {self.mask_file}")
            return False
        
        mask_img = cv2.imread(self.mask_file, cv2.IMREAD_GRAYSCALE)
        if mask_img is None:
            print(f"[ERROR] 无法读取mask文件: {self.mask_file}")
            return False
        
        print(f"[OK] 加载mask文件: {self.mask_file}")
        
        # 缩放mask到1080p分辨率
        target_width, target_height = 1920, 1080
        if mask_img.shape != (target_height, target_width):
            mask_img = cv2.resize(mask_img, (target_width, target_height), interpolation=cv2.INTER_NEAREST)
        
        self.mask_image = mask_img
        
        # 识别光点
        binary_mask = (mask_img > 200).astype(np.uint8) * 255
        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        self.light_points_template = []
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if area >= 10:
                self.light_points_template.append(contour)
        
        print(f"识别到 {len(self.light_points_template)} 个光点区域")
        return len(self.light_points_template) > 0
    
    def _create_trackbars(self):
        """创建调节滑条"""
        cv2.namedWindow('Red Detection Tuner', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Red Detection Tuner', 960, 540)
        
        # HSV范围1的滑条
        cv2.createTrackbar('H_Min1', 'Red Detection Tuner', self.h_min1, 180, self._on_trackbar)
        cv2.createTrackbar('S_Min1', 'Red Detection Tuner', self.s_min1, 255, self._on_trackbar)
        cv2.createTrackbar('V_Min1', 'Red Detection Tuner', self.v_min1, 255, self._on_trackbar)
        cv2.createTrackbar('H_Max1', 'Red Detection Tuner', self.h_max1, 180, self._on_trackbar)
        cv2.createTrackbar('S_Max1', 'Red Detection Tuner', self.s_max1, 255, self._on_trackbar)
        cv2.createTrackbar('V_Max1', 'Red Detection Tuner', self.v_max1, 255, self._on_trackbar)
        
        # HSV范围2的滑条
        cv2.createTrackbar('H_Min2', 'Red Detection Tuner', self.h_min2, 180, self._on_trackbar)
        cv2.createTrackbar('S_Min2', 'Red Detection Tuner', self.s_min2, 255, self._on_trackbar)
        cv2.createTrackbar('V_Min2', 'Red Detection Tuner', self.v_min2, 255, self._on_trackbar)
        cv2.createTrackbar('H_Max2', 'Red Detection Tuner', self.h_max2, 180, self._on_trackbar)
        cv2.createTrackbar('S_Max2', 'Red Detection Tuner', self.s_max2, 255, self._on_trackbar)
        cv2.createTrackbar('V_Max2', 'Red Detection Tuner', self.v_max2, 255, self._on_trackbar)
        
        # 红色比例阈值
        cv2.createTrackbar('Red_Ratio_%', 'Red Detection Tuner', self.red_ratio_threshold, 100, self._on_trackbar)
    
    def _on_trackbar(self, val):
        """滑条回调函数"""
        # 更新参数
        self.h_min1 = cv2.getTrackbarPos('H_Min1', 'Red Detection Tuner')
        self.s_min1 = cv2.getTrackbarPos('S_Min1', 'Red Detection Tuner')
        self.v_min1 = cv2.getTrackbarPos('V_Min1', 'Red Detection Tuner')
        self.h_max1 = cv2.getTrackbarPos('H_Max1', 'Red Detection Tuner')
        self.s_max1 = cv2.getTrackbarPos('S_Max1', 'Red Detection Tuner')
        self.v_max1 = cv2.getTrackbarPos('V_Max1', 'Red Detection Tuner')
        
        self.h_min2 = cv2.getTrackbarPos('H_Min2', 'Red Detection Tuner')
        self.s_min2 = cv2.getTrackbarPos('S_Min2', 'Red Detection Tuner')
        self.v_min2 = cv2.getTrackbarPos('V_Min2', 'Red Detection Tuner')
        self.h_max2 = cv2.getTrackbarPos('H_Max2', 'Red Detection Tuner')
        self.s_max2 = cv2.getTrackbarPos('S_Max2', 'Red Detection Tuner')
        self.v_max2 = cv2.getTrackbarPos('V_Max2', 'Red Detection Tuner')
        
        self.red_ratio_threshold = cv2.getTrackbarPos('Red_Ratio_%', 'Red Detection Tuner')
    
    def _is_red_color(self, bgr_color: Tuple[int, int, int]) -> bool:
        """判断BGR颜色是否为红色"""
        bgr_pixel = np.uint8([[bgr_color]])
        hsv_pixel = cv2.cvtColor(bgr_pixel, cv2.COLOR_BGR2HSV)[0][0]
        
        # 使用当前滑条参数
        red_hsv_lower1 = np.array([self.h_min1, self.s_min1, self.v_min1])
        red_hsv_upper1 = np.array([self.h_max1, self.s_max1, self.v_max1])
        red_hsv_lower2 = np.array([self.h_min2, self.s_min2, self.v_min2])
        red_hsv_upper2 = np.array([self.h_max2, self.s_max2, self.v_max2])
        
        in_range1 = (red_hsv_lower1[0] <= hsv_pixel[0] <= red_hsv_upper1[0] and
                     red_hsv_lower1[1] <= hsv_pixel[1] <= red_hsv_upper1[1] and
                     red_hsv_lower1[2] <= hsv_pixel[2] <= red_hsv_upper1[2])
        
        in_range2 = (red_hsv_lower2[0] <= hsv_pixel[0] <= red_hsv_upper2[0] and
                     red_hsv_lower2[1] <= hsv_pixel[1] <= red_hsv_upper2[1] and
                     red_hsv_lower2[2] <= hsv_pixel[2] <= red_hsv_upper2[2])
        
        return in_range1 or in_range2
    
    def _check_light_point_red(self, frame: np.ndarray, contour: np.ndarray) -> Tuple[bool, float]:
        """检查光点区域是否为红色，返回是否为红色和红色比例"""
        # 创建光点区域的mask
        point_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        cv2.fillPoly(point_mask, [contour], 255)
        
        # 提取光点区域的像素
        masked_pixels = frame[point_mask > 0]
        
        if len(masked_pixels) == 0:
            return False, 0.0
        
        # 检查区域内红色像素的比例
        red_pixel_count = 0
        total_pixels = len(masked_pixels)
        
        # 采样检查
        sample_size = min(100, total_pixels)
        step = max(1, total_pixels // sample_size)
        
        for i in range(0, total_pixels, step):
            bgr_color = tuple(masked_pixels[i].astype(int))
            if self._is_red_color(bgr_color):
                red_pixel_count += 1
        
        red_ratio = (red_pixel_count / (total_pixels // step)) * 100  # 转换为百分比
        is_red = red_ratio > self.red_ratio_threshold
        
        return is_red, red_ratio
    
    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """处理帧并显示检测结果"""
        # 先将非mask区域黑化
        result = frame.copy()
        black_mask = self.mask_image <= 200
        result[black_mask] = [0, 0, 0]
        
        red_light_count = 0
        total_light_count = len(self.light_points_template)
        
        # 检测每个光点
        for i, contour in enumerate(self.light_points_template):
            is_red, red_ratio = self._check_light_point_red(frame, contour)
            
            if is_red:
                red_light_count += 1
                # 红色光点用红色轮廓
                cv2.drawContours(result, [contour], -1, (0, 0, 255), 2)
                
                # 计算中心点
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    center_x = int(M["m10"] / M["m00"])
                    center_y = int(M["m01"] / M["m00"])
                    
                    # 显示红色比例
                    cv2.putText(result, f"{red_ratio:.1f}%", 
                               (center_x - 20, center_y - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            else:
                # 非红色光点用灰色轮廓
                cv2.drawContours(result, [contour], -1, (128, 128, 128), 1)
                
                # 显示红色比例（如果有的话）
                if red_ratio > 0:
                    M = cv2.moments(contour)
                    if M["m00"] != 0:
                        center_x = int(M["m10"] / M["m00"])
                        center_y = int(M["m01"] / M["m00"])
                        
                        cv2.putText(result, f"{red_ratio:.1f}%", 
                                   (center_x - 20, center_y - 10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (128, 128, 128), 1)
        
        # 添加统计信息
        info_text = [
            f"Total Light Points: {total_light_count}",
            f"Red Light Points: {red_light_count}",
            f"HSV1: [{self.h_min1},{self.s_min1},{self.v_min1}]-[{self.h_max1},{self.s_max1},{self.v_max1}]",
            f"HSV2: [{self.h_min2},{self.s_min2},{self.v_min2}]-[{self.h_max2},{self.s_max2},{self.v_max2}]",
            f"Red Ratio Threshold: {self.red_ratio_threshold}%"
        ]
        
        for i, text in enumerate(info_text):
            color = (0, 255, 0) if red_light_count > 0 else (0, 255, 255)
            cv2.putText(result, text, (10, 30 + i * 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # 添加控制说明
        controls = [
            "Controls:",
            "S - Save Parameters",
            "R - Reset to Default",
            "Q - Quit"
        ]
        
        start_y = result.shape[0] - len(controls) * 20 - 10
        for i, text in enumerate(controls):
            cv2.putText(result, text, (10, start_y + i * 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        return result
    
    def save_parameters(self):
        """保存当前参数到文件"""
        params = {
            'red_hsv_lower1': [self.h_min1, self.s_min1, self.v_min1],
            'red_hsv_upper1': [self.h_max1, self.s_max1, self.v_max1],
            'red_hsv_lower2': [self.h_min2, self.s_min2, self.v_min2],
            'red_hsv_upper2': [self.h_max2, self.s_max2, self.v_max2],
            'red_ratio_threshold': self.red_ratio_threshold / 100.0
        }
        
        with open('red_detection_params.txt', 'w') as f:
            f.write("# 红色检测参数\n")
            f.write(f"red_hsv_lower1 = np.array({params['red_hsv_lower1']})\n")
            f.write(f"red_hsv_upper1 = np.array({params['red_hsv_upper1']})\n")
            f.write(f"red_hsv_lower2 = np.array({params['red_hsv_lower2']})\n")
            f.write(f"red_hsv_upper2 = np.array({params['red_hsv_upper2']})\n")
            f.write(f"red_ratio_threshold = {params['red_ratio_threshold']:.2f}\n")
        
        print(f"[OK] 参数已保存到 red_detection_params.txt")
        print(f"红色光点检测参数:")
        print(f"  HSV范围1: {params['red_hsv_lower1']} - {params['red_hsv_upper1']}")
        print(f"  HSV范围2: {params['red_hsv_lower2']} - {params['red_hsv_upper2']}")
        print(f"  红色比例阈值: {params['red_ratio_threshold']:.2f}")
    
    def reset_to_default(self):
        """重置为默认参数"""
        cv2.setTrackbarPos('H_Min1', 'Red Detection Tuner', 0)
        cv2.setTrackbarPos('S_Min1', 'Red Detection Tuner', 30)
        cv2.setTrackbarPos('V_Min1', 'Red Detection Tuner', 30)
        cv2.setTrackbarPos('H_Max1', 'Red Detection Tuner', 25)
        cv2.setTrackbarPos('S_Max1', 'Red Detection Tuner', 255)
        cv2.setTrackbarPos('V_Max1', 'Red Detection Tuner', 255)
        
        cv2.setTrackbarPos('H_Min2', 'Red Detection Tuner', 155)
        cv2.setTrackbarPos('S_Min2', 'Red Detection Tuner', 30)
        cv2.setTrackbarPos('V_Min2', 'Red Detection Tuner', 30)
        cv2.setTrackbarPos('H_Max2', 'Red Detection Tuner', 180)
        cv2.setTrackbarPos('S_Max2', 'Red Detection Tuner', 255)
        cv2.setTrackbarPos('V_Max2', 'Red Detection Tuner', 255)
        
        cv2.setTrackbarPos('Red_Ratio_%', 'Red Detection Tuner', 10)
        
        print("[INFO] 参数已重置为默认值")
    
    def run_camera_test(self, camera_id: int = 0):
        """运行摄像头测试"""
        print(f"\n=== 摄像头 {camera_id} 红色检测参数调试 ===")
        
        # 初始化摄像头
        cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print(f"[ERROR] 无法打开摄像头 {camera_id}")
            return False
        
        # 配置摄像头为1080p
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        cap.set(cv2.CAP_PROP_EXPOSURE, -4)
        
        print("[OK] 摄像头初始化成功")
        print("使用滑条调整红色检测参数")
        print("控制说明:")
        print("  S - 保存参数")
        print("  R - 重置为默认值")
        print("  Q - 退出")
        print()
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    continue
                
                # 处理帧并显示结果
                result = self.process_frame(frame)
                cv2.imshow('Red Detection Tuner', result)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:  # 'q' 或 ESC
                    break
                elif key == ord('s'):  # 's' 键
                    self.save_parameters()
                elif key == ord('r'):  # 'r' 键
                    self.reset_to_default()
        
        except KeyboardInterrupt:
            print("\n[INFO] 用户中断")
        
        finally:
            cap.release()
            cv2.destroyAllWindows()
        
        return True

def main():
    """主函数"""
    print("=== 红色检测参数调试工具 ===")
    print("实时调整HSV参数和红色比例阈值")
    print()
    
    # 检查mask文件
    mask_file = "mask.png"
    if not os.path.exists(mask_file):
        print(f"[ERROR] 未找到mask文件: {mask_file}")
        print("请确保mask.png文件存在于当前目录")
        return 1
    
    try:
        tuner = RedDetectionTuner(mask_file)
        
        # 摄像头测试
        camera_id = 0
        try:
            camera_input = input("请输入摄像头ID (默认0): ").strip()
            if camera_input:
                camera_id = int(camera_input)
        except ValueError:
            camera_id = 0
        
        tuner.run_camera_test(camera_id)
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] 程序错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
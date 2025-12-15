#!/usr/bin/env python3
"""
简化的mask检测测试
不需要MQTT连接，直接测试mask颜色变化检测
"""

import cv2
import numpy as np
import time
import os
from typing import List, Tuple

class SimpleMaskDetector:
    """简化的mask检测器"""
    
    def __init__(self, mask_file: str = "m.png"):
        self.mask_file = mask_file
        self.mask_points = []
        self.baseline_colors = {}
        self.baseline_established = False
        
        # 红色检测参数
        self.red_hsv_lower1 = np.array([0, 50, 50])
        self.red_hsv_upper1 = np.array([10, 255, 255])
        self.red_hsv_lower2 = np.array([170, 50, 50])
        self.red_hsv_upper2 = np.array([180, 255, 255])
        
        if not self._load_mask():
            raise ValueError(f"无法加载mask文件: {mask_file}")
    
    def _load_mask(self) -> bool:
        """加载并缩放mask"""
        if not os.path.exists(self.mask_file):
            return False
        
        mask_img = cv2.imread(self.mask_file, cv2.IMREAD_GRAYSCALE)
        if mask_img is None:
            return False
        
        print(f"[INFO] Mask原始尺寸: {mask_img.shape}")
        
        # 缩放到720p
        target_width, target_height = 1280, 720
        if mask_img.shape != (target_height, target_width):
            mask_img = cv2.resize(mask_img, (target_width, target_height), interpolation=cv2.INTER_NEAREST)
            print(f"[INFO] Mask缩放到: {mask_img.shape}")
        
        # 提取白色区域坐标
        white_pixels = np.where(mask_img > 200)
        self.mask_points = list(zip(white_pixels[1], white_pixels[0]))  # (x, y)
        
        print(f"[INFO] Mask检测点数: {len(self.mask_points)}")
        return len(self.mask_points) > 0
    
    def _is_red_color(self, bgr_color: Tuple[int, int, int]) -> bool:
        """判断BGR颜色是否为红色"""
        bgr_pixel = np.uint8([[bgr_color]])
        hsv_pixel = cv2.cvtColor(bgr_pixel, cv2.COLOR_BGR2HSV)[0][0]
        
        in_range1 = (self.red_hsv_lower1[0] <= hsv_pixel[0] <= self.red_hsv_upper1[0] and
                     self.red_hsv_lower1[1] <= hsv_pixel[1] <= self.red_hsv_upper1[1] and
                     self.red_hsv_lower1[2] <= hsv_pixel[2] <= self.red_hsv_upper1[2])
        
        in_range2 = (self.red_hsv_lower2[0] <= hsv_pixel[0] <= self.red_hsv_upper2[0] and
                     self.red_hsv_lower2[1] <= hsv_pixel[1] <= self.red_hsv_upper2[1] and
                     self.red_hsv_lower2[2] <= hsv_pixel[2] <= self.red_hsv_upper2[2])
        
        return in_range1 or in_range2
    
    def establish_baseline(self, frame: np.ndarray):
        """建立基线"""
        self.baseline_colors = {}
        
        for x, y in self.mask_points:
            if 0 <= y < frame.shape[0] and 0 <= x < frame.shape[1]:
                bgr_color = tuple(frame[y, x].astype(int))
                is_red = self._is_red_color(bgr_color)
                self.baseline_colors[(x, y)] = {
                    'color': bgr_color,
                    'is_red': is_red
                }
        
        self.baseline_established = True
        red_count = sum(1 for data in self.baseline_colors.values() if data['is_red'])
        print(f"[OK] 基线建立: 总点数={len(self.baseline_colors)}, 红色点数={red_count}")
    
    def detect_changes(self, frame: np.ndarray) -> int:
        """检测颜色变化"""
        if not self.baseline_established:
            return 0
        
        change_count = 0
        
        for x, y in self.mask_points:
            if 0 <= y < frame.shape[0] and 0 <= x < frame.shape[1]:
                current_bgr = tuple(frame[y, x].astype(int))
                current_is_red = self._is_red_color(current_bgr)
                
                baseline_data = self.baseline_colors.get((x, y))
                if baseline_data and baseline_data['is_red'] != current_is_red:
                    change_count += 1
        
        return change_count
    
    def run_test(self):
        """运行测试"""
        print("\n=== 简化Mask检测测试 ===")
        
        # 初始化摄像头
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print("[ERROR] 无法打开摄像头")
            return False
        
        # 配置摄像头
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        cap.set(cv2.CAP_PROP_EXPOSURE, -4)
        
        print("[OK] 摄像头初始化成功")
        print("控制说明:")
        print("  SPACE - 建立基线")
        print("  R - 重置基线")
        print("  Q - 退出")
        print()
        
        cv2.namedWindow('Mask Detection Test', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Mask Detection Test', 640, 360)
        
        frame_count = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    continue
                
                frame_count += 1
                
                # 检测变化
                change_count = 0
                if self.baseline_established:
                    change_count = self.detect_changes(frame)
                
                # 创建显示图像
                display = frame.copy()
                
                # 绘制mask点
                for i, (x, y) in enumerate(self.mask_points):
                    if i % 50 == 0:  # 只显示部分点以提高性能
                        if 0 <= y < frame.shape[0] and 0 <= x < frame.shape[1]:
                            cv2.circle(display, (x, y), 1, (0, 255, 255), -1)
                
                # 添加信息文本
                info_text = [
                    f"Frame: {frame_count}",
                    f"Mask Points: {len(self.mask_points)}",
                    f"Baseline: {'YES' if self.baseline_established else 'NO'}",
                    f"Changes: {change_count}"
                ]
                
                for i, text in enumerate(info_text):
                    color = (0, 255, 0) if self.baseline_established else (0, 0, 255)
                    cv2.putText(display, text, (10, 30 + i * 25),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                # 如果有变化，显示警告
                if change_count > 0:
                    cv2.putText(display, f"COLOR CHANGE DETECTED: {change_count} points", 
                               (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                
                cv2.imshow('Mask Detection Test', display)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:  # 'q' 或 ESC
                    break
                elif key == ord(' '):  # 空格键
                    self.establish_baseline(frame)
                elif key == ord('r'):  # 'r' 键
                    self.baseline_established = False
                    self.baseline_colors = {}
                    print("[INFO] 基线已重置")
                
                # 定期输出状态
                if frame_count % 100 == 0:
                    print(f"[INFO] 帧数: {frame_count}, 变化点数: {change_count}")
        
        except KeyboardInterrupt:
            print("\n[INFO] 用户中断")
        
        finally:
            cap.release()
            cv2.destroyAllWindows()
        
        return True

def main():
    """主函数"""
    if not os.path.exists("m.png"):
        print("[ERROR] 未找到mask文件: m.png")
        return 1
    
    try:
        detector = SimpleMaskDetector()
        detector.run_test()
        return 0
    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
#!/usr/bin/env python3
"""
Mask对齐可视化工具
实时显示摄像头画面和mask.png的对齐情况
调试阶段用于验证mask区域和红色光点检测
"""

import cv2
import numpy as np
import os
import sys
import time
from typing import List, Tuple, Dict

class MaskAlignmentVisualizer:
    """Mask对齐可视化器"""
    
    def __init__(self, mask_file: str = "mask.png"):
        self.mask_file = mask_file
        self.mask_image = None
        self.mask_points = []
        
        # 红色检测参数
        self.red_hsv_lower1 = np.array([0, 50, 50])
        self.red_hsv_upper1 = np.array([20, 255, 255])  # 扩大到20
        self.red_hsv_lower2 = np.array([160, 50, 50])   # 从160开始
        self.red_hsv_upper2 = np.array([180, 255, 255])
        
        # 基线数据
        self.baseline_red_points = []
        self.baseline_established = False
        
        # 显示模式
        self.show_mode = 0  # 0: 原图+mask黑化, 1: 只显示mask区域, 2: 红色检测结果, 3: 半透明叠加
        
        if not self._load_mask():
            raise ValueError(f"无法加载mask文件: {mask_file}")
    
    def _load_mask(self) -> bool:
        """加载mask图片"""
        if not os.path.exists(self.mask_file):
            print(f"[ERROR] Mask文件不存在: {self.mask_file}")
            return False
        
        mask_img = cv2.imread(self.mask_file, cv2.IMREAD_GRAYSCALE)
        if mask_img is None:
            print(f"[ERROR] 无法读取mask文件: {self.mask_file}")
            return False
        
        print(f"[OK] 加载mask文件: {self.mask_file}")
        print(f"Mask原始尺寸: {mask_img.shape}")
        
        # 缩放mask到1080p分辨率
        target_width, target_height = 1920, 1080
        if mask_img.shape != (target_height, target_width):
            print(f"缩放mask到1080p: ({target_height}, {target_width})")
            mask_img = cv2.resize(mask_img, (target_width, target_height), interpolation=cv2.INTER_NEAREST)
            print(f"Mask缩放后尺寸: {mask_img.shape}")
        
        self.mask_image = mask_img
        
        # 提取白色区域坐标
        white_pixels = np.where(mask_img > 200)
        self.mask_points = list(zip(white_pixels[1], white_pixels[0]))  # (x, y)
        
        print(f"检测点数: {len(self.mask_points)}")
        
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
    
    def _extract_red_points_in_mask(self, frame: np.ndarray) -> List[Tuple[int, int]]:
        """提取mask区域内的红色光点坐标"""
        red_points = []
        
        for x, y in self.mask_points:
            if 0 <= y < frame.shape[0] and 0 <= x < frame.shape[1]:
                bgr_color = tuple(frame[y, x].astype(int))
                if self._is_red_color(bgr_color):
                    red_points.append((x, y))
        
        return red_points
    
    def establish_baseline(self, frame: np.ndarray):
        """建立基线 - 只采集mask白色区域内的红色光点"""
        self.baseline_red_points = self._extract_red_points_in_mask(frame)
        self.baseline_established = True
        
        print(f"[OK] 基线建立完成，mask区域内红色光点数: {len(self.baseline_red_points)}")
    
    def create_overlay_display(self, frame: np.ndarray) -> np.ndarray:
        """创建叠加显示"""
        if self.show_mode == 0:
            # 模式0: 原图 + mask叠加 (非白色区域全黑处理)
            result = frame.copy()
            
            # 创建mask的反向mask (黑色区域)
            black_mask = self.mask_image <= 200  # 非白色区域
            
            # 将非白色区域设为全黑
            result[black_mask] = [0, 0, 0]
            
            # 绘制mask轮廓以突出边界
            mask_contours, _ = cv2.findContours(self.mask_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(result, mask_contours, -1, (0, 255, 255), 2)  # 黄色轮廓
            
            # 如果建立了基线，显示红色光点
            if self.baseline_established:
                current_red_points = self._extract_red_points_in_mask(frame)
                baseline_coords = set(self.baseline_red_points)
                current_coords = set(current_red_points)
                
                # 绘制基线红色点 (绿色)
                for x, y in self.baseline_red_points:
                    cv2.circle(result, (x, y), 3, (0, 255, 0), -1)
                
                # 绘制当前红色点 (蓝色)
                for x, y in current_red_points:
                    if (x, y) not in baseline_coords:
                        cv2.circle(result, (x, y), 3, (255, 0, 0), -1)  # 新出现的点
                
                # 绘制消失的点 (红色X)
                for x, y in self.baseline_red_points:
                    if (x, y) not in current_coords:
                        cv2.drawMarker(result, (x, y), (0, 0, 255), cv2.MARKER_TILTED_CROSS, 8, 2)
            
        elif self.show_mode == 1:
            # 模式1: 只显示mask区域
            result = np.zeros_like(frame)
            
            # 应用mask
            mask_3channel = cv2.cvtColor(self.mask_image, cv2.COLOR_GRAY2BGR)
            mask_normalized = mask_3channel / 255.0
            result = (frame * mask_normalized).astype(np.uint8)
            
        elif self.show_mode == 2:
            # 模式2: 红色检测结果
            result = frame.copy()
            
            # 创建红色检测mask
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            red_mask1 = cv2.inRange(hsv, self.red_hsv_lower1, self.red_hsv_upper1)
            red_mask2 = cv2.inRange(hsv, self.red_hsv_lower2, self.red_hsv_upper2)
            red_mask = cv2.bitwise_or(red_mask1, red_mask2)
            
            # 只在mask区域内显示红色检测结果
            combined_mask = cv2.bitwise_and(red_mask, self.mask_image)
            
            # 将检测结果叠加到原图
            result[combined_mask > 0] = [0, 0, 255]  # 红色高亮
            
        elif self.show_mode == 3:
            # 模式3: 半透明mask叠加
            result = frame.copy()
            
            # 创建半透明mask叠加
            mask_overlay = np.zeros_like(frame)
            mask_overlay[self.mask_image > 200] = [0, 255, 0]  # 绿色表示mask区域
            
            # 半透明叠加
            alpha = 0.3
            result = cv2.addWeighted(result, 1-alpha, mask_overlay, alpha, 0)
            
            # 绘制mask轮廓
            mask_contours, _ = cv2.findContours(self.mask_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(result, mask_contours, -1, (0, 255, 255), 2)  # 黄色轮廓
        
        return result
    
    def add_info_overlay(self, image: np.ndarray, frame_count: int) -> np.ndarray:
        """添加信息叠加"""
        result = image.copy()
        
        # 当前红色光点数
        current_red_count = 0
        if hasattr(self, '_current_frame'):
            current_red_points = self._extract_red_points_in_mask(self._current_frame)
            current_red_count = len(current_red_points)
        
        # 信息文本
        info_text = [
            f"Frame: {frame_count}",
            f"Mask Points: {len(self.mask_points)}",
            f"Show Mode: {self.show_mode} ({'Black Mask' if self.show_mode == 0 else 'Mask Only' if self.show_mode == 1 else 'Red Detection' if self.show_mode == 2 else 'Transparent'})",
            f"Baseline: {'YES' if self.baseline_established else 'NO'}",
            f"Baseline Red: {len(self.baseline_red_points) if self.baseline_established else 0}",
            f"Current Red: {current_red_count}",
        ]
        
        # 计算变化
        if self.baseline_established and hasattr(self, '_current_frame'):
            current_red_points = self._extract_red_points_in_mask(self._current_frame)
            baseline_coords = set(self.baseline_red_points)
            current_coords = set(current_red_points)
            
            disappeared = len(baseline_coords - current_coords)
            appeared = len(current_coords - baseline_coords)
            total_changes = disappeared + appeared
            
            info_text.extend([
                f"Disappeared: {disappeared}",
                f"Appeared: {appeared}",
                f"Total Changes: {total_changes}"
            ])
        
        # 绘制信息
        for i, text in enumerate(info_text):
            color = (0, 255, 0) if self.baseline_established else (0, 255, 255)
            cv2.putText(result, text, (10, 30 + i * 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # 控制说明
        controls = [
            "Controls:",
            "SPACE - Establish Baseline",
            "R - Reset Baseline", 
            "M - Change Display Mode",
            "  0: Black Mask (non-white areas black)",
            "  1: Mask Only",
            "  2: Red Detection",
            "  3: Transparent Overlay",
            "Q - Quit"
        ]
        
        start_y = result.shape[0] - len(controls) * 25 - 10
        for i, text in enumerate(controls):
            cv2.putText(result, text, (10, start_y + i * 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return result
    
    def run_camera_test(self, camera_id: int = 0):
        """运行摄像头测试"""
        print(f"\n=== 摄像头 {camera_id} Mask对齐可视化 ===")
        
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
        
        # 验证分辨率
        ret, test_frame = cap.read()
        if ret:
            actual_shape = test_frame.shape
            print(f"[INFO] 摄像头实际分辨率: {actual_shape}")
            if actual_shape[:2] != (1080, 1920):
                print(f"[WARNING] 分辨率不匹配！期望: (1080, 1920), 实际: {actual_shape[:2]}")
        
        print("[OK] 摄像头初始化成功")
        print("控制说明:")
        print("  SPACE - 建立基线 (采集mask区域内红色光点)")
        print("  R - 重置基线")
        print("  M - 切换显示模式")
        print("  Q - 退出")
        print()
        
        # 创建窗口 - 缩放显示以适应屏幕
        cv2.namedWindow('Mask Alignment Visualizer', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Mask Alignment Visualizer', 960, 540)  # 50%缩放显示
        
        frame_count = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    continue
                
                frame_count += 1
                self._current_frame = frame  # 保存当前帧用于信息显示
                
                # 创建显示图像
                display = self.create_overlay_display(frame)
                display = self.add_info_overlay(display, frame_count)
                
                cv2.imshow('Mask Alignment Visualizer', display)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:  # 'q' 或 ESC
                    break
                elif key == ord(' '):  # 空格键
                    self.establish_baseline(frame)
                elif key == ord('r'):  # 'r' 键
                    self.baseline_established = False
                    self.baseline_red_points = []
                    print("[INFO] 基线已重置")
                elif key == ord('m'):  # 'm' 键
                    self.show_mode = (self.show_mode + 1) % 4
                    mode_names = ["Black Mask", "Mask Only", "Red Detection", "Transparent"]
                    print(f"[INFO] 切换到显示模式: {self.show_mode} ({mode_names[self.show_mode]})")
                
                # 定期输出状态
                if frame_count % 100 == 0:
                    current_red_count = len(self._extract_red_points_in_mask(frame))
                    print(f"[INFO] 帧数: {frame_count}, 当前红色光点数: {current_red_count}")
        
        except KeyboardInterrupt:
            print("\n[INFO] 用户中断")
        
        finally:
            cap.release()
            cv2.destroyAllWindows()
        
        return True

def main():
    """主函数"""
    print("=== Mask对齐可视化工具 ===")
    print("实时显示摄像头画面和mask.png的对齐情况")
    print()
    
    # 检查mask文件
    mask_file = "mask.png"
    if not os.path.exists(mask_file):
        print(f"[ERROR] 未找到mask文件: {mask_file}")
        print("请确保mask.png文件存在于当前目录")
        return 1
    
    try:
        visualizer = MaskAlignmentVisualizer(mask_file)
        
        # 摄像头测试
        camera_id = 0
        try:
            camera_input = input("请输入摄像头ID (默认0): ").strip()
            if camera_input:
                camera_id = int(camera_input)
        except ValueError:
            camera_id = 0
        
        visualizer.run_camera_test(camera_id)
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] 程序错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
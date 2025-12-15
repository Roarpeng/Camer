#!/usr/bin/env python3
"""
mask检测可视化工具
实时显示mask区域内的颜色检测效果
"""

import cv2
import numpy as np
import os
import sys
import time
from typing import List, Tuple, Dict

class MaskDetectionVisualizer:
    """mask检测可视化器"""
    
    def __init__(self, mask_file: str = "m.png"):
        self.mask_file = mask_file
        self.mask_image = None
        self.mask_points = []
        
        # 红色检测参数
        self.red_hsv_lower1 = np.array([0, 50, 50])
        self.red_hsv_upper1 = np.array([10, 255, 255])
        self.red_hsv_lower2 = np.array([170, 50, 50])
        self.red_hsv_upper2 = np.array([180, 255, 255])
        
        # 基线数据
        self.baseline_colors = {}
        self.baseline_established = False
        
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
        
        # 缩放mask到720p分辨率
        target_width, target_height = 1280, 720
        if mask_img.shape != (target_height, target_width):
            print(f"缩放mask到目标尺寸: ({target_height}, {target_width})")
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
        print(f"[OK] 基线建立完成，红色点数: {red_count}/{len(self.baseline_colors)}")
    
    def visualize_detection(self, frame: np.ndarray) -> np.ndarray:
        """可视化检测结果"""
        result = frame.copy()
        
        if not self.baseline_established:
            # 显示mask区域
            for x, y in self.mask_points:
                if 0 <= y < frame.shape[0] and 0 <= x < frame.shape[1]:
                    cv2.circle(result, (x, y), 1, (255, 255, 255), -1)
            
            # 添加提示文本
            cv2.putText(result, "Press SPACE to establish baseline", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        else:
            # 显示检测结果
            red_count = 0
            changed_count = 0
            
            for x, y in self.mask_points:
                if 0 <= y < frame.shape[0] and 0 <= x < frame.shape[1]:
                    current_bgr = tuple(frame[y, x].astype(int))
                    current_is_red = self._is_red_color(current_bgr)
                    
                    baseline_data = self.baseline_colors.get((x, y))
                    if baseline_data:
                        baseline_is_red = baseline_data['is_red']
                        
                        # 检查变化
                        changed = baseline_is_red != current_is_red
                        
                        if current_is_red:
                            red_count += 1
                        
                        if changed:
                            changed_count += 1
                        
                        # 绘制点
                        if changed:
                            # 变化的点用红色标记
                            cv2.circle(result, (x, y), 2, (0, 0, 255), -1)
                        elif current_is_red:
                            # 当前红色点用绿色标记
                            cv2.circle(result, (x, y), 1, (0, 255, 0), -1)
                        elif baseline_is_red:
                            # 基线是红色但现在不是的点用蓝色标记
                            cv2.circle(result, (x, y), 1, (255, 0, 0), -1)
                        else:
                            # 普通点用白色标记
                            cv2.circle(result, (x, y), 1, (255, 255, 255), -1)
            
            # 添加统计信息
            cv2.putText(result, f"Red Points: {red_count}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(result, f"Changed Points: {changed_count}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(result, f"Total Mask Points: {len(self.mask_points)}", (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # 添加图例
            cv2.putText(result, "Legend:", (10, 130),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(result, "Red: Changed", (10, 150),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            cv2.putText(result, "Green: Current Red", (10, 170),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            cv2.putText(result, "Blue: Was Red", (10, 190),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
            cv2.putText(result, "White: Normal", (10, 210),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return result
    
    def run_camera_test(self, camera_id: int = 0):
        """运行摄像头测试"""
        print(f"\n=== 摄像头 {camera_id} mask检测可视化 ===")
        
        # 初始化摄像头
        cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print(f"[ERROR] 无法打开摄像头 {camera_id}")
            return False
        
        # 配置摄像头 - 使用分辨率匹配mask (1280x720)
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
        
        cv2.namedWindow('Mask Detection Visualizer', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Mask Detection Visualizer', 800, 600)
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    continue
                
                # 可视化检测
                result = self.visualize_detection(frame)
                
                cv2.imshow('Mask Detection Visualizer', result)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:  # 'q' 或 ESC
                    break
                elif key == ord(' '):  # 空格键
                    self.establish_baseline(frame)
                elif key == ord('r'):  # 'r' 键
                    self.baseline_established = False
                    self.baseline_colors = {}
                    print("[INFO] 基线已重置")
        
        except KeyboardInterrupt:
            print("\n[INFO] 用户中断")
        
        finally:
            cap.release()
            cv2.destroyAllWindows()
        
        return True
    
    def run_image_test(self, image_path: str):
        """运行图片测试"""
        print(f"\n=== 图片 {image_path} mask检测可视化 ===")
        
        # 读取图片
        image = cv2.imread(image_path)
        if image is None:
            print(f"[ERROR] 无法读取图片: {image_path}")
            return False
        
        print("[OK] 图片加载成功")
        print("控制说明:")
        print("  SPACE - 建立基线")
        print("  R - 重置基线")
        print("  Q - 退出")
        print()
        
        cv2.namedWindow('Mask Detection Visualizer', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Mask Detection Visualizer', 800, 600)
        
        try:
            while True:
                # 可视化检测
                result = self.visualize_detection(image)
                
                cv2.imshow('Mask Detection Visualizer', result)
                
                key = cv2.waitKey(30) & 0xFF
                if key == ord('q') or key == 27:  # 'q' 或 ESC
                    break
                elif key == ord(' '):  # 空格键
                    self.establish_baseline(image)
                elif key == ord('r'):  # 'r' 键
                    self.baseline_established = False
                    self.baseline_colors = {}
                    print("[INFO] 基线已重置")
        
        except KeyboardInterrupt:
            print("\n[INFO] 用户中断")
        
        finally:
            cv2.destroyAllWindows()
        
        return True

def main():
    """主函数"""
    print("=== Mask检测可视化工具 ===")
    print()
    
    # 检查mask文件
    mask_file = "m.png"
    if not os.path.exists(mask_file):
        print(f"[ERROR] 未找到mask文件: {mask_file}")
        print("请确保mask文件存在于当前目录")
        return 1
    
    try:
        visualizer = MaskDetectionVisualizer(mask_file)
        
        # 选择测试模式
        print("选择测试模式:")
        print("1. 摄像头实时测试")
        print("2. 图片测试")
        
        choice = input("请输入选择 (1 或 2): ").strip()
        
        if choice == "1":
            # 摄像头测试
            camera_id = 0
            try:
                camera_input = input("请输入摄像头ID (默认0): ").strip()
                if camera_input:
                    camera_id = int(camera_input)
            except ValueError:
                camera_id = 0
            
            visualizer.run_camera_test(camera_id)
        
        elif choice == "2":
            # 图片测试
            import glob
            image_files = []
            for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp']:
                image_files.extend(glob.glob(ext))
                image_files.extend(glob.glob(ext.upper()))
            
            if not image_files:
                print("[ERROR] 当前目录没有找到图片文件")
                return 1
            
            print("发现的图片文件:")
            for i, file in enumerate(image_files, 1):
                print(f"  {i}. {file}")
            
            try:
                img_choice = input("请输入图片编号: ").strip()
                img_index = int(img_choice) - 1
                if 0 <= img_index < len(image_files):
                    visualizer.run_image_test(image_files[img_index])
                else:
                    print("[ERROR] 无效的图片编号")
                    return 1
            except ValueError:
                print("[ERROR] 无效的输入")
                return 1
        
        else:
            print("[ERROR] 无效的选择")
            return 1
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] 程序错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
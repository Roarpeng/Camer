#!/usr/bin/env python3
"""
灰度摄像头红色检测工具
专门针对只能输出灰度图像的摄像头进行红色光点检测
"""

import cv2
import numpy as np
import os
import time

class GrayscaleRedDetector:
    """灰度摄像头红色检测器"""
    
    def __init__(self, mask_file: str = "mask.png"):
        self.mask_file = mask_file
        self.mask_image = None
        self.light_points_template = []
        
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
        
        # 缩放到640x480
        target_width, target_height = 640, 480
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
                self.light_points_template.append((i, contour))
        
        print(f"[INFO] 识别到 {len(self.light_points_template)} 个光点区域")
        return len(self.light_points_template) > 0
    
    def detect_red_by_brightness_change(self, baseline_frame: np.ndarray, current_frame: np.ndarray) -> int:
        """通过亮度变化检测红色光点
        
        原理：红色LED灯通常比周围环境更亮，当红色光点出现或消失时，
        该区域的亮度会发生显著变化
        """
        
        red_light_count = 0
        red_light_ids = []
        
        print("\n=== 基于亮度变化的红色检测 ===")
        
        for light_id, contour in self.light_points_template:
            # 创建光点区域mask
            point_mask = np.zeros(baseline_frame.shape[:2], dtype=np.uint8)
            cv2.fillPoly(point_mask, [contour], 255)
            
            # 提取基线和当前帧的光点区域
            baseline_region = baseline_frame[point_mask > 0]
            current_region = current_frame[point_mask > 0]
            
            if len(baseline_region) == 0 or len(current_region) == 0:
                continue
            
            # 计算亮度统计
            baseline_mean = np.mean(baseline_region)
            current_mean = np.mean(current_region)
            baseline_max = np.max(baseline_region)
            current_max = np.max(current_region)
            
            # 亮度变化
            brightness_change = current_mean - baseline_mean
            max_brightness_change = current_max - baseline_max
            
            # 检测红色光点的条件：
            # 1. 当前亮度显著高于基线（红色LED点亮）
            # 2. 最大亮度变化超过阈值
            is_red = (brightness_change > 15 and current_mean > 80) or \
                     (max_brightness_change > 30 and current_max > 120)
            
            print(f"光点 {light_id:2d}: "
                  f"基线亮度={baseline_mean:.1f}, "
                  f"当前亮度={current_mean:.1f}, "
                  f"变化={brightness_change:.1f}, "
                  f"最大亮度变化={max_brightness_change:.1f}, "
                  f"结果={'红色' if is_red else '非红色'}")
            
            if is_red:
                red_light_count += 1
                red_light_ids.append(light_id)
        
        print(f"检测结果: {red_light_count}/{len(self.light_points_template)} 个红色光点")
        if red_light_ids:
            print(f"红色光点ID: {red_light_ids}")
        
        return red_light_count
    
    def detect_red_by_absolute_brightness(self, frame: np.ndarray) -> int:
        """通过绝对亮度检测红色光点
        
        原理：红色LED灯通常比周围环境更亮，直接检测高亮度区域
        """
        
        red_light_count = 0
        red_light_ids = []
        
        print("\n=== 基于绝对亮度的红色检测 ===")
        
        for light_id, contour in self.light_points_template:
            # 创建光点区域mask
            point_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
            cv2.fillPoly(point_mask, [contour], 255)
            
            # 提取光点区域
            light_region = frame[point_mask > 0]
            
            if len(light_region) == 0:
                continue
            
            # 计算亮度统计
            mean_brightness = np.mean(light_region)
            max_brightness = np.max(light_region)
            brightness_std = np.std(light_region)
            
            # 检测红色光点的条件：
            # 1. 平均亮度超过阈值
            # 2. 最大亮度超过阈值
            # 3. 亮度标准差表明有亮点存在
            is_red = (mean_brightness > 100) or \
                     (max_brightness > 150) or \
                     (mean_brightness > 80 and brightness_std > 20)
            
            print(f"光点 {light_id:2d}: "
                  f"平均亮度={mean_brightness:.1f}, "
                  f"最大亮度={max_brightness:.1f}, "
                  f"标准差={brightness_std:.1f}, "
                  f"结果={'红色' if is_red else '非红色'}")
            
            if is_red:
                red_light_count += 1
                red_light_ids.append(light_id)
        
        print(f"检测结果: {red_light_count}/{len(self.light_points_template)} 个红色光点")
        if red_light_ids:
            print(f"红色光点ID: {red_light_ids}")
        
        return red_light_count
    
    def detect_red_by_edge_detection(self, frame: np.ndarray) -> int:
        """通过边缘检测找红色光点
        
        原理：LED灯通常有清晰的边缘，使用边缘检测找到明亮的圆形区域
        """
        
        red_light_count = 0
        red_light_ids = []
        
        print("\n=== 基于边缘检测的红色检测 ===")
        
        # 应用高斯模糊
        blurred = cv2.GaussianBlur(frame, (5, 5), 0)
        
        # Canny边缘检测
        edges = cv2.Canny(blurred, 50, 150)
        
        for light_id, contour in self.light_points_template:
            # 创建光点区域mask
            point_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
            cv2.fillPoly(point_mask, [contour], 255)
            
            # 提取光点区域的边缘
            light_edges = edges[point_mask > 0]
            light_region = frame[point_mask > 0]
            
            if len(light_edges) == 0 or len(light_region) == 0:
                continue
            
            # 计算边缘密度和亮度
            edge_density = np.sum(light_edges > 0) / len(light_edges)
            mean_brightness = np.mean(light_region)
            
            # 检测红色光点的条件：
            # 1. 有一定的边缘密度（表明有形状）
            # 2. 同时亮度较高
            is_red = (edge_density > 0.05 and mean_brightness > 80) or \
                     (edge_density > 0.02 and mean_brightness > 120)
            
            print(f"光点 {light_id:2d}: "
                  f"边缘密度={edge_density:.3f}, "
                  f"平均亮度={mean_brightness:.1f}, "
                  f"结果={'红色' if is_red else '非红色'}")
            
            if is_red:
                red_light_count += 1
                red_light_ids.append(light_id)
        
        print(f"检测结果: {red_light_count}/{len(self.light_points_template)} 个红色光点")
        if red_light_ids:
            print(f"红色光点ID: {red_light_ids}")
        
        return red_light_count
    
    def run_detection_test(self):
        """运行检测测试"""
        
        print("=== 灰度摄像头红色检测工具 ===")
        print("专门针对只能输出灰度图像的摄像头进行红色光点检测")
        print()
        
        # 初始化摄像头
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print("[ERROR] 无法打开摄像头")
            return False
        
        # 配置摄像头
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        cap.set(cv2.CAP_PROP_EXPOSURE, -5)
        cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.8)
        cap.set(cv2.CAP_PROP_CONTRAST, 0.85)
        cap.set(cv2.CAP_PROP_GAIN, 80)
        
        print("摄像头配置完成，预热中...")
        
        # 预热摄像头
        for i in range(10):
            ret, frame = cap.read()
            if ret and frame is not None:
                break
            time.sleep(0.1)
        
        if not ret or frame is None:
            print("[ERROR] 无法捕获帧")
            cap.release()
            return False
        
        # 转换为灰度图像（如果是彩色的话）
        if len(frame.shape) == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        print(f"捕获帧尺寸: {frame.shape}")
        print(f"图像平均亮度: {np.mean(frame):.1f}")
        
        # 保存基线帧
        baseline_frame = frame.copy()
        cv2.imwrite("grayscale_baseline.jpg", baseline_frame)
        print("基线帧已保存: grayscale_baseline.jpg")
        
        print("\n请在摄像头前放置红色LED灯或红色光源...")
        print("按任意键继续检测...")
        input()
        
        # 捕获当前帧
        ret, current_frame = cap.read()
        if ret and current_frame is not None:
            if len(current_frame.shape) == 3:
                current_frame = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
            
            cv2.imwrite("grayscale_current.jpg", current_frame)
            print("当前帧已保存: grayscale_current.jpg")
            
            # 运行三种检测方法
            print("\n" + "="*50)
            
            # 方法1: 亮度变化检测
            count1 = self.detect_red_by_brightness_change(baseline_frame, current_frame)
            
            # 方法2: 绝对亮度检测
            count2 = self.detect_red_by_absolute_brightness(current_frame)
            
            # 方法3: 边缘检测
            count3 = self.detect_red_by_edge_detection(current_frame)
            
            print("\n" + "="*50)
            print("=== 检测结果汇总 ===")
            print(f"亮度变化检测: {count1} 个红色光点")
            print(f"绝对亮度检测: {count2} 个红色光点")
            print(f"边缘检测方法: {count3} 个红色光点")
            
            # 创建可视化图像
            self._create_visualization(baseline_frame, current_frame)
        
        cap.release()
        return True
    
    def _create_visualization(self, baseline_frame: np.ndarray, current_frame: np.ndarray):
        """创建可视化图像"""
        
        # 创建对比图像
        comparison = np.zeros((480, 1280), dtype=np.uint8)
        
        # 左侧：基线帧
        comparison[:, :640] = baseline_frame
        
        # 右侧：当前帧
        comparison[:, 640:] = current_frame
        
        # 转换为彩色以便绘制彩色轮廓
        comparison_color = cv2.cvtColor(comparison, cv2.COLOR_GRAY2BGR)
        
        # 绘制光点轮廓
        for light_id, contour in self.light_points_template:
            # 左侧基线帧轮廓（蓝色）
            cv2.drawContours(comparison_color, [contour], -1, (255, 0, 0), 2)
            
            # 右侧当前帧轮廓（绿色）
            contour_shifted = contour.copy()
            contour_shifted[:, :, 0] += 640  # 向右偏移640像素
            cv2.drawContours(comparison_color, [contour_shifted], -1, (0, 255, 0), 2)
            
            # 添加光点ID
            M = cv2.moments(contour)
            if M["m00"] != 0:
                center_x = int(M["m10"] / M["m00"])
                center_y = int(M["m01"] / M["m00"])
                
                # 基线帧ID
                cv2.putText(comparison_color, str(light_id), (center_x-10, center_y+5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # 当前帧ID
                cv2.putText(comparison_color, str(light_id), (center_x+640-10, center_y+5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # 添加标签
        cv2.putText(comparison_color, "Baseline", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(comparison_color, "Current", (650, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # 添加分割线
        cv2.line(comparison_color, (640, 0), (640, 480), (0, 255, 255), 2)
        
        # 保存可视化图像
        cv2.imwrite("grayscale_detection_visualization.jpg", comparison_color)
        print("可视化图像已保存: grayscale_detection_visualization.jpg")

def main():
    """主函数"""
    
    if not os.path.exists("mask.png"):
        print("[ERROR] 未找到mask.png文件")
        return 1
    
    try:
        detector = GrayscaleRedDetector()
        detector.run_detection_test()
        return 0
        
    except Exception as e:
        print(f"[ERROR] 程序错误: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
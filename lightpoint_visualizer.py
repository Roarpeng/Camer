#!/usr/bin/env python3
"""
光点可视化工具
显示mask中识别的光点区域和红色检测效果
"""

import cv2
import numpy as np
import os
import sys
import time
from typing import List, Tuple, Dict
from dataclasses import dataclass

@dataclass
class LightPoint:
    """光点信息"""
    id: int
    center_x: int
    center_y: int
    area: int
    contour: np.ndarray
    baseline_is_red: bool = False
    current_is_red: bool = False
    changed: bool = False

class LightPointVisualizer:
    """光点可视化器"""
    
    def __init__(self, mask_file: str = "mask.png"):
        self.mask_file = mask_file
        self.mask_image = None
        self.light_points_template = []
        
        # 红色检测参数 - 更宽松的检测范围
        self.red_hsv_lower1 = np.array([0, 30, 30])      # 降低饱和度和亮度要求
        self.red_hsv_upper1 = np.array([25, 255, 255])   # 扩大色调范围
        self.red_hsv_lower2 = np.array([155, 30, 30])    # 扩大第二范围
        self.red_hsv_upper2 = np.array([180, 255, 255])
        
        # 基线数据
        self.baseline_red_points = []
        self.baseline_established = False
        
        # 显示模式
        self.show_mode = 0  # 0: 光点轮廓, 1: 光点编号, 2: 红色检测, 3: 变化对比
        
        if not self._load_mask():
            raise ValueError(f"无法加载mask文件: {mask_file}")
    
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
        print(f"Mask原始尺寸: {mask_img.shape}")
        
        # 缩放mask到1080p分辨率
        target_width, target_height = 1920, 1080
        if mask_img.shape != (target_height, target_width):
            print(f"缩放mask到1080p: ({target_height}, {target_width})")
            mask_img = cv2.resize(mask_img, (target_width, target_height), interpolation=cv2.INTER_NEAREST)
            print(f"Mask缩放后尺寸: {mask_img.shape}")
        
        self.mask_image = mask_img
        
        # 创建二值化mask
        binary_mask = (mask_img > 200).astype(np.uint8) * 255
        
        # 查找白色连通区域
        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 创建光点模板
        self.light_points_template = []
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if area < 10:  # 最小面积阈值
                continue
            
            # 计算中心点
            M = cv2.moments(contour)
            if M["m00"] != 0:
                center_x = int(M["m10"] / M["m00"])
                center_y = int(M["m01"] / M["m00"])
            else:
                x, y, w, h = cv2.boundingRect(contour)
                center_x = x + w // 2
                center_y = y + h // 2
            
            light_point = LightPoint(
                id=i,
                center_x=center_x,
                center_y=center_y,
                area=int(area),
                contour=contour
            )
            
            self.light_points_template.append(light_point)
        
        print(f"识别到 {len(self.light_points_template)} 个光点区域")
        
        if self.light_points_template:
            areas = [lp.area for lp in self.light_points_template]
            print(f"光点面积统计: 最小={min(areas)}, 最大={max(areas)}, 平均={sum(areas)/len(areas):.1f}")
        
        return len(self.light_points_template) > 0
    
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
    
    def _check_light_point_red(self, frame: np.ndarray, light_point: LightPoint) -> bool:
        """检查光点区域是否为红色"""
        # 创建光点区域的mask
        point_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        cv2.fillPoly(point_mask, [light_point.contour], 255)
        
        # 提取光点区域的像素
        masked_pixels = frame[point_mask > 0]
        
        if len(masked_pixels) == 0:
            return False
        
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
        
        red_ratio = red_pixel_count / (total_pixels // step)
        return red_ratio > 0.1  # 降低到10%的像素为红色就认为是红色光点
    
    def _extract_red_light_points(self, frame: np.ndarray) -> List[LightPoint]:
        """提取当前帧中的红色光点"""
        red_light_points = []
        
        for template_point in self.light_points_template:
            is_red = self._check_light_point_red(frame, template_point)
            
            if is_red:
                red_point = LightPoint(
                    id=template_point.id,
                    center_x=template_point.center_x,
                    center_y=template_point.center_y,
                    area=template_point.area,
                    contour=template_point.contour,
                    baseline_is_red=True,
                    current_is_red=True
                )
                red_light_points.append(red_point)
        
        return red_light_points
    
    def establish_baseline(self, frame: np.ndarray):
        """建立基线 - 采集红色光点"""
        self.baseline_red_points = self._extract_red_light_points(frame)
        self.baseline_established = True
        
        print(f"[OK] 基线建立完成，红色光点数: {len(self.baseline_red_points)}/{len(self.light_points_template)}")
    
    def create_overlay_display(self, frame: np.ndarray) -> np.ndarray:
        """创建叠加显示"""
        # 先将非mask区域黑化
        result = frame.copy()
        black_mask = self.mask_image <= 200
        result[black_mask] = [0, 0, 0]
        
        if self.show_mode == 0:
            # 模式0: 光点轮廓显示
            for i, light_point in enumerate(self.light_points_template):
                # 绘制光点轮廓
                cv2.drawContours(result, [light_point.contour], -1, (0, 255, 255), 2)  # 黄色轮廓
                
                # 绘制中心点
                cv2.circle(result, (light_point.center_x, light_point.center_y), 3, (255, 255, 255), -1)
            
        elif self.show_mode == 1:
            # 模式1: 光点编号显示
            for light_point in self.light_points_template:
                # 绘制光点轮廓
                cv2.drawContours(result, [light_point.contour], -1, (0, 255, 255), 1)
                
                # 绘制编号
                cv2.putText(result, str(light_point.id), 
                           (light_point.center_x - 10, light_point.center_y + 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        elif self.show_mode == 2:
            # 模式2: 红色检测结果
            current_red_points = self._extract_red_light_points(frame)
            
            # 绘制所有光点轮廓（灰色）
            for light_point in self.light_points_template:
                cv2.drawContours(result, [light_point.contour], -1, (128, 128, 128), 1)
            
            # 高亮红色光点
            for red_point in current_red_points:
                cv2.drawContours(result, [red_point.contour], -1, (0, 0, 255), 2)  # 红色轮廓
                cv2.circle(result, (red_point.center_x, red_point.center_y), 5, (0, 0, 255), -1)
        
        elif self.show_mode == 3:
            # 模式3: 变化对比（需要基线）
            if self.baseline_established:
                current_red_points = self._extract_red_light_points(frame)
                
                baseline_ids = {point.id for point in self.baseline_red_points}
                current_ids = {point.id for point in current_red_points}
                
                # 绘制所有光点轮廓（灰色）
                for light_point in self.light_points_template:
                    cv2.drawContours(result, [light_point.contour], -1, (128, 128, 128), 1)
                
                # 绘制基线红色光点（绿色）
                for red_point in self.baseline_red_points:
                    cv2.drawContours(result, [red_point.contour], -1, (0, 255, 0), 2)
                    cv2.circle(result, (red_point.center_x, red_point.center_y), 3, (0, 255, 0), -1)
                
                # 绘制当前红色光点（蓝色）
                for red_point in current_red_points:
                    if red_point.id not in baseline_ids:
                        cv2.drawContours(result, [red_point.contour], -1, (255, 0, 0), 2)
                        cv2.circle(result, (red_point.center_x, red_point.center_y), 3, (255, 0, 0), -1)
                
                # 标记消失的光点（红色X）
                for red_point in self.baseline_red_points:
                    if red_point.id not in current_ids:
                        cv2.drawMarker(result, (red_point.center_x, red_point.center_y), 
                                     (0, 0, 255), cv2.MARKER_TILTED_CROSS, 10, 2)
            else:
                # 未建立基线时显示所有光点
                for light_point in self.light_points_template:
                    cv2.drawContours(result, [light_point.contour], -1, (0, 255, 255), 1)
        
        return result
    
    def add_info_overlay(self, image: np.ndarray, frame_count: int) -> np.ndarray:
        """添加信息叠加"""
        result = image.copy()
        
        # 当前红色光点数
        current_red_count = 0
        if hasattr(self, '_current_frame'):
            current_red_points = self._extract_red_light_points(self._current_frame)
            current_red_count = len(current_red_points)
        
        # 信息文本
        info_text = [
            f"Frame: {frame_count}",
            f"Total Light Points: {len(self.light_points_template)}",
            f"Show Mode: {self.show_mode} ({'Contours' if self.show_mode == 0 else 'Numbers' if self.show_mode == 1 else 'Red Detection' if self.show_mode == 2 else 'Changes'})",
            f"Baseline: {'YES' if self.baseline_established else 'NO'}",
            f"Baseline Red: {len(self.baseline_red_points) if self.baseline_established else 0}",
            f"Current Red: {current_red_count}",
        ]
        
        # 计算变化
        if self.baseline_established and hasattr(self, '_current_frame'):
            current_red_points = self._extract_red_light_points(self._current_frame)
            baseline_ids = {point.id for point in self.baseline_red_points}
            current_ids = {point.id for point in current_red_points}
            
            disappeared = len(baseline_ids - current_ids)
            appeared = len(current_ids - baseline_ids)
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
            "  0: Light Point Contours",
            "  1: Light Point Numbers",
            "  2: Red Detection",
            "  3: Change Comparison",
            "Q - Quit"
        ]
        
        start_y = result.shape[0] - len(controls) * 20 - 10
        for i, text in enumerate(controls):
            cv2.putText(result, text, (10, start_y + i * 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        return result
    
    def run_camera_test(self, camera_id: int = 0):
        """运行摄像头测试"""
        print(f"\n=== 摄像头 {camera_id} 光点可视化 ===")
        
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
        print("  SPACE - 建立基线 (采集红色光点)")
        print("  R - 重置基线")
        print("  M - 切换显示模式")
        print("  Q - 退出")
        print()
        
        # 创建窗口
        cv2.namedWindow('Light Point Visualizer', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Light Point Visualizer', 960, 540)  # 50%缩放显示
        
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
                
                cv2.imshow('Light Point Visualizer', display)
                
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
                    mode_names = ["Contours", "Numbers", "Red Detection", "Changes"]
                    print(f"[INFO] 切换到显示模式: {self.show_mode} ({mode_names[self.show_mode]})")
                
                # 定期输出状态
                if frame_count % 100 == 0:
                    current_red_count = len(self._extract_red_light_points(frame))
                    print(f"[INFO] 帧数: {frame_count}, 当前红色光点数: {current_red_count}/{len(self.light_points_template)}")
        
        except KeyboardInterrupt:
            print("\n[INFO] 用户中断")
        
        finally:
            cap.release()
            cv2.destroyAllWindows()
        
        return True

def main():
    """主函数"""
    print("=== 光点可视化工具 ===")
    print("显示mask中识别的光点区域和红色检测效果")
    print()
    
    # 检查mask文件
    mask_file = "mask.png"
    if not os.path.exists(mask_file):
        print(f"[ERROR] 未找到mask文件: {mask_file}")
        print("请确保mask.png文件存在于当前目录")
        return 1
    
    try:
        visualizer = LightPointVisualizer(mask_file)
        
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
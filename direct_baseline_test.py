#!/usr/bin/env python3
"""
直接基线测试
绕过MQTT，直接测试基线建立功能
"""

import cv2
import numpy as np
import time
import logging
import sys
import os
from typing import List, Tuple
from dataclasses import dataclass

@dataclass
class LightPoint:
    """光点信息"""
    id: int
    center_x: int
    center_y: int
    area: int
    contour: np.ndarray

class DirectBaselineTester:
    """直接基线测试器"""
    
    def __init__(self, mask_file: str = "mask.png"):
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('direct_baseline_test.log', encoding='utf-8')
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        self.mask_file = mask_file
        self.mask_image = None
        self.light_points_template = []
        
        # 红色检测参数
        self.red_hsv_lower1 = np.array([0, 30, 30])
        self.red_hsv_upper1 = np.array([25, 255, 255])
        self.red_hsv_lower2 = np.array([155, 30, 30])
        self.red_hsv_upper2 = np.array([180, 255, 255])
        
        if not self._load_mask():
            raise ValueError(f"无法加载mask文件: {mask_file}")
    
    def _load_mask(self) -> bool:
        """加载mask图片"""
        if not os.path.exists(self.mask_file):
            self.logger.error(f"Mask文件不存在: {self.mask_file}")
            return False
        
        mask_img = cv2.imread(self.mask_file, cv2.IMREAD_GRAYSCALE)
        if mask_img is None:
            self.logger.error(f"无法读取mask文件: {self.mask_file}")
            return False
        
        # 缩放到640x480 (摄像头实际分辨率)
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
        
        self.logger.info(f"识别到 {len(self.light_points_template)} 个光点区域")
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
    
    def _check_light_point_red(self, frame: np.ndarray, light_point: LightPoint) -> Tuple[bool, float]:
        """检查光点区域是否为红色"""
        point_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        cv2.fillPoly(point_mask, [light_point.contour], 255)
        
        masked_pixels = frame[point_mask > 0]
        if len(masked_pixels) == 0:
            return False, 0.0
        
        red_pixel_count = 0
        total_pixels = len(masked_pixels)
        sample_size = min(100, total_pixels)
        step = max(1, total_pixels // sample_size)
        
        for i in range(0, total_pixels, step):
            bgr_color = tuple(masked_pixels[i].astype(int))
            if self._is_red_color(bgr_color):
                red_pixel_count += 1
        
        red_ratio = red_pixel_count / (total_pixels // step)
        return red_ratio > 0.1, red_ratio
    
    def test_single_camera(self, camera_id: int = 0) -> bool:
        """测试单个摄像头的基线建立"""
        self.logger.info(f"=== 测试摄像头 {camera_id} 基线建立 ===")
        
        # 初始化摄像头
        cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
        if not cap.isOpened():
            self.logger.error(f"无法打开摄像头 {camera_id}")
            return False
        
        # 配置摄像头为640x480
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        cap.set(cv2.CAP_PROP_EXPOSURE, -4)
        cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.6)
        cap.set(cv2.CAP_PROP_CONTRAST, 0.6)
        cap.set(cv2.CAP_PROP_SATURATION, 0.8)
        
        self.logger.info("摄像头配置完成，开始预热...")
        
        # 预热摄像头
        for i in range(10):
            ret, frame = cap.read()
            if ret and frame is not None:
                self.logger.info(f"预热帧 {i+1}: 成功，尺寸 {frame.shape}")
            else:
                self.logger.warning(f"预热帧 {i+1}: 失败")
            time.sleep(0.1)
        
        # 模拟MQTT触发后的延迟
        self.logger.info("模拟MQTT触发后0.1秒延迟...")
        time.sleep(0.1)
        
        # 捕获基线帧
        self.logger.info("捕获基线帧...")
        ret, frame = cap.read()
        
        if not ret or frame is None:
            self.logger.error("无法捕获基线帧")
            cap.release()
            return False
        
        self.logger.info(f"基线帧捕获成功: {frame.shape}")
        
        # 检测红色光点
        red_count = 0
        red_light_ids = []
        
        self.logger.info("开始检测红色光点...")
        
        for light_point in self.light_points_template:
            is_red, red_ratio = self._check_light_point_red(frame, light_point)
            
            self.logger.info(f"光点 {light_point.id:2d}: "
                           f"中心({light_point.center_x:4d},{light_point.center_y:4d}), "
                           f"红色比例={red_ratio:.3f}, "
                           f"结果={'红色' if is_red else '非红色'}")
            
            if is_red:
                red_count += 1
                red_light_ids.append(light_point.id)
        
        # 输出结果
        self.logger.info(f"=== 基线检测结果 ===")
        self.logger.info(f"总光点数: {len(self.light_points_template)}")
        self.logger.info(f"红色光点数: {red_count}")
        
        if red_count > 0:
            self.logger.info(f"红色光点ID: {red_light_ids}")
            self.logger.info("基线建立成功")
            success = True
        else:
            self.logger.error("基线建立失败：未检测到红色光点")
            success = False
        
        # 保存调试图像
        debug_image = frame.copy()
        
        # 将非mask区域黑化
        black_mask = self.mask_image <= 200
        debug_image[black_mask] = [0, 0, 0]
        
        # 绘制光点轮廓
        for light_point in self.light_points_template:
            color = (0, 0, 255) if light_point.id in red_light_ids else (128, 128, 128)
            cv2.drawContours(debug_image, [light_point.contour], -1, color, 2)
            
            # 添加光点ID
            cv2.putText(debug_image, str(light_point.id),
                       (light_point.center_x - 10, light_point.center_y + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # 保存调试图像
        debug_filename = f"direct_baseline_camera{camera_id}_{int(time.time())}.jpg"
        cv2.imwrite(debug_filename, debug_image)
        self.logger.info(f"调试图像已保存: {debug_filename}")
        
        cap.release()
        return success
    
    def test_all_cameras(self) -> None:
        """测试所有可用摄像头"""
        self.logger.info("=== 测试所有可用摄像头 ===")
        
        success_count = 0
        
        for camera_id in range(6):  # 测试0-5号摄像头
            try:
                self.logger.info(f"\n--- 测试摄像头 {camera_id} ---")
                
                if self.test_single_camera(camera_id):
                    success_count += 1
                    self.logger.info(f"摄像头 {camera_id}: 成功")
                else:
                    self.logger.error(f"摄像头 {camera_id}: 失败")
                
                time.sleep(1)  # 摄像头间隔
                
            except Exception as e:
                self.logger.error(f"摄像头 {camera_id} 测试错误: {e}")
        
        self.logger.info(f"\n=== 测试完成 ===")
        self.logger.info(f"成功的摄像头数: {success_count}/6")

def main():
    """主函数"""
    print("=== 直接基线测试 ===")
    print("绕过MQTT，直接测试基线建立功能")
    print()
    
    if not os.path.exists("mask.png"):
        print("[ERROR] 未找到mask.png文件")
        return 1
    
    try:
        tester = DirectBaselineTester()
        
        print("选择测试模式:")
        print("1. 测试单个摄像头 (摄像头0)")
        print("2. 测试所有摄像头 (0-5)")
        
        choice = input("请输入选择 (1 或 2): ").strip()
        
        if choice == "1":
            success = tester.test_single_camera(0)
            if success:
                print("\n[OK] 摄像头0基线测试成功")
            else:
                print("\n[ERROR] 摄像头0基线测试失败")
        
        elif choice == "2":
            tester.test_all_cameras()
        
        else:
            print("[ERROR] 无效选择")
            return 1
        
        print("\n详细日志已保存到 direct_baseline_test.log")
        return 0
        
    except Exception as e:
        print(f"[ERROR] 程序错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
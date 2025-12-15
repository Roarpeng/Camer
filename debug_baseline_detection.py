#!/usr/bin/env python3
"""
调试基线检测问题
专门用于诊断生产环境系统基线建立时无法检测到红色光点的问题
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

class BaselineDetectionDebugger:
    """基线检测调试器"""
    
    def __init__(self, mask_file: str = "mask.png"):
        self.mask_file = mask_file
        self.mask_image = None
        self.light_points_template = []
        
        # 红色检测参数 - 与生产环境完全一致
        self.red_hsv_lower1 = np.array([0, 30, 30])
        self.red_hsv_upper1 = np.array([25, 255, 255])
        self.red_hsv_lower2 = np.array([155, 30, 30])
        self.red_hsv_upper2 = np.array([180, 255, 255])
        
        # 设置日志
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('baseline_debug.log', encoding='utf-8')
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        if not self._load_mask():
            raise ValueError(f"无法加载mask文件: {mask_file}")
    
    def _load_mask(self) -> bool:
        """加载mask图片并识别光点"""
        if not os.path.exists(self.mask_file):
            self.logger.error(f"Mask文件不存在: {self.mask_file}")
            return False
        
        mask_img = cv2.imread(self.mask_file, cv2.IMREAD_GRAYSCALE)
        if mask_img is None:
            self.logger.error(f"无法读取mask文件: {self.mask_file}")
            return False
        
        self.logger.info(f"Mask原始尺寸: {mask_img.shape}")
        
        # 缩放到1080p分辨率
        target_width, target_height = 1920, 1080
        if mask_img.shape != (target_height, target_width):
            self.logger.info(f"缩放mask到1080p: ({target_height}, {target_width})")
            mask_img = cv2.resize(mask_img, (target_width, target_height), interpolation=cv2.INTER_NEAREST)
        
        self.mask_image = mask_img
        
        # 识别光点
        binary_mask = (mask_img > 200).astype(np.uint8) * 255
        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        self.light_points_template = []
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if area >= 10:
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
    
    def _check_light_point_red(self, frame: np.ndarray, light_point: LightPoint) -> Tuple[bool, float, int]:
        """检查光点区域是否为红色，返回详细信息"""
        # 创建光点区域的mask
        point_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        cv2.fillPoly(point_mask, [light_point.contour], 255)
        
        # 提取光点区域的像素
        masked_pixels = frame[point_mask > 0]
        
        if len(masked_pixels) == 0:
            return False, 0.0, 0
        
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
        is_red = red_ratio > 0.1
        
        return is_red, red_ratio, total_pixels
    
    def _extract_red_light_points_debug(self, frame: np.ndarray) -> List[LightPoint]:
        """提取红色光点并输出详细调试信息"""
        red_light_points = []
        
        self.logger.info(f"=== 开始红色光点检测 ===")
        self.logger.info(f"帧尺寸: {frame.shape}")
        self.logger.info(f"总光点数: {len(self.light_points_template)}")
        
        for template_point in self.light_points_template:
            is_red, red_ratio, pixel_count = self._check_light_point_red(frame, template_point)
            
            self.logger.info(f"光点 {template_point.id:2d}: "
                           f"中心({template_point.center_x:4d},{template_point.center_y:4d}), "
                           f"面积={template_point.area:5d}, "
                           f"像素数={pixel_count:5d}, "
                           f"红色比例={red_ratio:.3f}, "
                           f"结果={'红色' if is_red else '非红色'}")
            
            if is_red:
                red_point = LightPoint(
                    id=template_point.id,
                    center_x=template_point.center_x,
                    center_y=template_point.center_y,
                    area=template_point.area,
                    contour=template_point.contour
                )
                red_light_points.append(red_point)
        
        self.logger.info(f"=== 红色光点检测完成 ===")
        self.logger.info(f"检测到 {len(red_light_points)}/{len(self.light_points_template)} 个红色光点")
        
        if len(red_light_points) > 0:
            red_ids = [p.id for p in red_light_points]
            self.logger.info(f"红色光点ID: {red_ids}")
        else:
            self.logger.warning("未检测到任何红色光点！")
        
        return red_light_points
    
    def simulate_baseline_capture(self):
        """模拟基线捕获过程"""
        self.logger.info("=== 模拟基线捕获过程 ===")
        
        # 初始化摄像头
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            self.logger.error("无法打开摄像头")
            return False
        
        # 配置摄像头 - 与生产环境完全一致
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        cap.set(cv2.CAP_PROP_EXPOSURE, -4)  # 从config.yaml读取
        
        # 预热摄像头
        self.logger.info("预热摄像头...")
        for i in range(5):
            ret, frame = cap.read()
            if ret and frame is not None:
                self.logger.info(f"预热帧 {i+1}: 成功读取，尺寸 {frame.shape}")
            else:
                self.logger.warning(f"预热帧 {i+1}: 读取失败")
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
        
        # 执行红色光点检测
        red_light_points = self._extract_red_light_points_debug(frame)
        
        # 输出基线结果
        self.logger.info(f"=== 基线建立结果 ===")
        self.logger.info(f"基线红色光点数: {len(red_light_points)}")
        
        if len(red_light_points) == 0:
            self.logger.error("基线建立失败：未检测到红色光点")
            self.logger.info("可能的原因:")
            self.logger.info("1. 红色光源不够亮或不够红")
            self.logger.info("2. 光源不在mask定义的区域内")
            self.logger.info("3. 摄像头曝光设置不当")
            self.logger.info("4. 红色检测参数需要调整")
        else:
            self.logger.info("基线建立成功")
        
        # 保存调试图像
        debug_image = frame.copy()
        
        # 将非mask区域黑化
        black_mask = self.mask_image <= 200
        debug_image[black_mask] = [0, 0, 0]
        
        # 绘制光点轮廓
        for light_point in self.light_points_template:
            color = (0, 0, 255) if any(rp.id == light_point.id for rp in red_light_points) else (128, 128, 128)
            cv2.drawContours(debug_image, [light_point.contour], -1, color, 2)
            
            # 添加光点ID
            cv2.putText(debug_image, str(light_point.id),
                       (light_point.center_x - 10, light_point.center_y + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # 保存调试图像
        debug_filename = f"baseline_debug_{int(time.time())}.jpg"
        cv2.imwrite(debug_filename, debug_image)
        self.logger.info(f"调试图像已保存: {debug_filename}")
        
        cap.release()
        return len(red_light_points) > 0
    
    def run_continuous_test(self, duration: int = 30):
        """运行连续测试"""
        self.logger.info(f"=== 开始连续测试 ({duration}秒) ===")
        
        # 初始化摄像头
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            self.logger.error("无法打开摄像头")
            return False
        
        # 配置摄像头
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        cap.set(cv2.CAP_PROP_EXPOSURE, -4)
        
        start_time = time.time()
        frame_count = 0
        
        try:
            while time.time() - start_time < duration:
                ret, frame = cap.read()
                if not ret:
                    continue
                
                frame_count += 1
                
                # 每5秒检测一次
                if frame_count % 150 == 0:  # 30fps * 5秒
                    elapsed = time.time() - start_time
                    self.logger.info(f"\n=== 第 {elapsed:.0f} 秒检测 ===")
                    
                    red_light_points = self._extract_red_light_points_debug(frame)
                    self.logger.info(f"检测结果: {len(red_light_points)} 个红色光点")
        
        except KeyboardInterrupt:
            self.logger.info("用户中断测试")
        
        finally:
            cap.release()
        
        self.logger.info(f"连续测试完成，总帧数: {frame_count}")
        return True

def main():
    """主函数"""
    print("=== 基线检测调试工具 ===")
    print("专门用于诊断生产环境系统基线建立问题")
    print()
    
    if not os.path.exists("mask.png"):
        print("[ERROR] 未找到mask.png文件")
        return 1
    
    try:
        debugger = BaselineDetectionDebugger()
        
        print("选择测试模式:")
        print("1. 模拟基线捕获 (单次)")
        print("2. 连续测试 (30秒)")
        
        choice = input("请输入选择 (1 或 2): ").strip()
        
        if choice == "1":
            success = debugger.simulate_baseline_capture()
            if success:
                print("\n[OK] 基线捕获成功")
            else:
                print("\n[ERROR] 基线捕获失败")
        
        elif choice == "2":
            debugger.run_continuous_test(30)
        
        else:
            print("[ERROR] 无效选择")
            return 1
        
        print("\n详细日志已保存到 baseline_debug.log")
        return 0
        
    except Exception as e:
        print(f"[ERROR] 程序错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
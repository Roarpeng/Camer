#!/usr/bin/env python3
"""
测试生产环境系统的基线建立
模拟完整的MQTT触发和基线建立过程
"""

import cv2
import numpy as np
import time
import logging
import sys
import os
from typing import Dict, List, Optional, Tuple
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

@dataclass
class CameraLightPointState:
    """摄像头光点检测状态"""
    camera_id: int
    light_points: List[LightPoint] = None
    baseline_red_count: int = 0
    current_red_count: int = 0
    baseline_established: bool = False
    last_detection_time: float = 0.0
    detection_count: int = 0

class ProductionBaselineTester:
    """生产环境基线测试器"""
    
    def __init__(self, mask_file: str = "mask.png"):
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('production_baseline_test.log', encoding='utf-8')
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        self.mask_file = mask_file
        self.mask_image = None
        self.light_points_template = []
        
        # 系统状态
        self.running = False
        self.mqtt_triggered = False
        self.baseline_capture_time = 0.0
        
        # 摄像头状态
        self.cameras: List[Optional[cv2.VideoCapture]] = []
        self.camera_states: Dict[int, CameraLightPointState] = {}
        
        # 红色检测参数 - 与生产环境完全一致
        self.red_hsv_lower1 = np.array([0, 30, 30])
        self.red_hsv_upper1 = np.array([25, 255, 255])
        self.red_hsv_lower2 = np.array([155, 30, 30])
        self.red_hsv_upper2 = np.array([180, 255, 255])
        
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
        return red_ratio > 0.1
    
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
    
    def initialize_cameras(self) -> bool:
        """初始化摄像头 - 与生产环境完全一致"""
        self.logger.info("初始化 1 个摄像头...")
        
        self.cameras = [None] * 1
        
        try:
            self.logger.info("初始化摄像头 0...")
            
            # 使用DirectShow后端
            cap = None
            for attempt in range(3):
                try:
                    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                    if cap.isOpened():
                        break
                    if cap:
                        cap.release()
                    time.sleep(0.5)
                except Exception as e:
                    self.logger.warning(f"摄像头 0 初始化尝试 {attempt+1} 失败: {e}")
                    if cap:
                        cap.release()
                    cap = None
            
            if not cap or not cap.isOpened():
                self.logger.error("摄像头 0 无法打开")
                return False
            
            # 配置摄像头为1080p
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_FPS, 30)
            
            # 设置曝光参数 - 从config.yaml读取
            cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
            cap.set(cv2.CAP_PROP_EXPOSURE, -4)
            cap.set(cv2.CAP_PROP_BRIGHTNESS, 60 / 100.0)
            cap.set(cv2.CAP_PROP_CONTRAST, 60 / 100.0)
            cap.set(cv2.CAP_PROP_SATURATION, 80 / 100.0)
            
            # 预热摄像头
            for i in range(5):
                ret, frame = cap.read()
                if ret and frame is not None:
                    break
                time.sleep(0.1)
            
            if ret and frame is not None:
                actual_shape = frame.shape
                self.logger.info(f"摄像头 0 实际分辨率: {actual_shape}")
                
                self.cameras[0] = cap
                self.camera_states[0] = CameraLightPointState(0)
                self.logger.info("摄像头 0 初始化成功")
                return True
            else:
                self.logger.error("摄像头 0 无法读取帧")
                cap.release()
                return False
                
        except Exception as e:
            self.logger.error(f"摄像头 0 初始化失败: {e}")
            return False
    
    def simulate_mqtt_trigger(self):
        """模拟MQTT触发"""
        self.logger.info("[MQTT] 模拟接收changeState消息")
        self.logger.info("[MQTT] 基线建立条件满足，开始基线建立")
        
        self.mqtt_triggered = True
        self.baseline_capture_time = time.time() + 0.1
        
        # 重置摄像头状态
        for state in self.camera_states.values():
            state.baseline_established = False
            state.light_points = None
            state.baseline_red_count = 0
            state.current_red_count = 0
            state.detection_count = 0
    
    def capture_baseline(self) -> None:
        """捕获基线数据 - 与生产环境完全一致"""
        self.logger.info("开始捕获红色光点基线数据...")
        
        for camera_id, cap in enumerate(self.cameras):
            if cap is None or camera_id not in self.camera_states:
                continue
            
            try:
                # 捕获帧
                ret, frame = cap.read()
                if not ret or frame is None:
                    self.logger.warning(f"摄像头 {camera_id} 无法捕获基线帧")
                    continue
                
                self.logger.info(f"摄像头 {camera_id} 基线帧捕获成功: {frame.shape}")
                
                # 提取红色光点
                red_light_points = self._extract_red_light_points(frame)
                
                # 设置基线
                state = self.camera_states[camera_id]
                state.light_points = red_light_points
                state.baseline_red_count = len(red_light_points)
                state.current_red_count = len(red_light_points)
                state.baseline_established = True
                state.last_detection_time = time.time()
                
                self.logger.info(f"摄像头 {camera_id} 基线设置: 红色光点数={len(red_light_points)}/{len(self.light_points_template)}")
                
                if len(red_light_points) == 0:
                    self.logger.error(f"摄像头 {camera_id} 基线建立失败：未检测到红色光点")
                else:
                    red_ids = [p.id for p in red_light_points]
                    self.logger.info(f"摄像头 {camera_id} 红色光点ID: {red_ids}")
                
            except Exception as e:
                self.logger.error(f"摄像头 {camera_id} 基线捕获失败: {e}")
        
        self.logger.info("基线捕获完成")
    
    def run_test(self):
        """运行完整测试"""
        self.logger.info("=== 生产环境基线测试开始 ===")
        
        # 1. 初始化摄像头
        if not self.initialize_cameras():
            self.logger.error("摄像头初始化失败")
            return False
        
        # 2. 模拟MQTT触发
        self.simulate_mqtt_trigger()
        
        # 3. 等待基线捕获时间
        current_time = time.time()
        while current_time < self.baseline_capture_time:
            time.sleep(0.01)
            current_time = time.time()
        
        # 4. 执行基线捕获
        self.capture_baseline()
        
        # 5. 检查结果
        success = False
        for camera_id, state in self.camera_states.items():
            if state.baseline_established and state.baseline_red_count > 0:
                success = True
                self.logger.info(f"摄像头 {camera_id} 基线建立成功")
            else:
                self.logger.error(f"摄像头 {camera_id} 基线建立失败")
        
        # 6. 清理资源
        for cap in self.cameras:
            if cap is not None:
                cap.release()
        
        self.logger.info("=== 生产环境基线测试完成 ===")
        return success

def main():
    """主函数"""
    print("=== 生产环境基线测试 ===")
    print("模拟完整的MQTT触发和基线建立过程")
    print()
    
    if not os.path.exists("mask.png"):
        print("[ERROR] 未找到mask.png文件")
        return 1
    
    try:
        tester = ProductionBaselineTester()
        success = tester.run_test()
        
        if success:
            print("\n[OK] 生产环境基线测试成功")
        else:
            print("\n[ERROR] 生产环境基线测试失败")
            print("请检查 production_baseline_test.log 获取详细信息")
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"[ERROR] 程序错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
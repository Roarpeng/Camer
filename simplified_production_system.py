#!/usr/bin/env python3
"""
简化的生产环境系统
消除线程和时序问题，专注于红色光点检测
"""

import cv2
import numpy as np
import time
import logging
import sys
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from mqtt_camera_monitoring.config import ConfigManager
from mqtt_camera_monitoring.mqtt_client import MQTTClient

@dataclass
class LightPoint:
    """光点信息"""
    id: int
    center_x: int
    center_y: int
    area: int
    contour: np.ndarray

@dataclass
class CameraState:
    """摄像头状态"""
    camera_id: int
    baseline_red_count: int = 0
    current_red_count: int = 0
    baseline_established: bool = False

class SimplifiedProductionSystem:
    """简化的生产环境系统"""
    
    def __init__(self, config_file: str = "config.yaml", mask_file: str = "mask.png"):
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('simplified_production.log', encoding='utf-8')
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # 加载配置
        config_manager = ConfigManager(config_file)
        self.config = config_manager.load_config()
        
        # 加载mask
        self.mask_file = mask_file
        self.mask_image = None
        self.light_points_template = []
        
        if not self._load_mask():
            raise ValueError(f"无法加载mask文件: {mask_file}")
        
        # 摄像头和状态
        self.cameras: List[Optional[cv2.VideoCapture]] = []
        self.camera_states: Dict[int, CameraState] = {}
        
        # MQTT客户端
        self.mqtt_client: Optional[MQTTClient] = None
        
        # 红色检测参数
        self.red_hsv_lower1 = np.array([0, 30, 30])
        self.red_hsv_upper1 = np.array([25, 255, 255])
        self.red_hsv_lower2 = np.array([155, 30, 30])
        self.red_hsv_upper2 = np.array([180, 255, 255])
        
        self.logger.info(f"简化生产系统初始化完成，光点数: {len(self.light_points_template)}")
    
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
    
    def _check_light_point_red(self, frame: np.ndarray, light_point: LightPoint) -> bool:
        """检查光点区域是否为红色"""
        point_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        cv2.fillPoly(point_mask, [light_point.contour], 255)
        
        masked_pixels = frame[point_mask > 0]
        if len(masked_pixels) == 0:
            return False
        
        red_pixel_count = 0
        total_pixels = len(masked_pixels)
        sample_size = min(100, total_pixels)
        step = max(1, total_pixels // sample_size)
        
        for i in range(0, total_pixels, step):
            bgr_color = tuple(masked_pixels[i].astype(int))
            if self._is_red_color(bgr_color):
                red_pixel_count += 1
        
        red_ratio = red_pixel_count / (total_pixels // step)
        return red_ratio > 0.1
    
    def _extract_red_light_points(self, frame: np.ndarray) -> int:
        """提取红色光点数量"""
        red_count = 0
        
        for template_point in self.light_points_template:
            if self._check_light_point_red(frame, template_point):
                red_count += 1
        
        return red_count
    
    def initialize_cameras(self) -> bool:
        """初始化摄像头"""
        camera_count = min(self.config.cameras.count, 6)  # 最多6个摄像头
        self.logger.info(f"初始化 {camera_count} 个摄像头...")
        
        self.cameras = [None] * camera_count
        
        for camera_id in range(camera_count):
            try:
                if camera_id > 0:
                    time.sleep(0.3)
                
                self.logger.info(f"初始化摄像头 {camera_id}...")
                
                cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    self.logger.warning(f"摄像头 {camera_id} 无法打开")
                    continue
                
                # 配置摄像头为640x480
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
                cap.set(cv2.CAP_PROP_EXPOSURE, self.config.cameras.exposure)
                cap.set(cv2.CAP_PROP_BRIGHTNESS, self.config.cameras.brightness / 100.0)
                cap.set(cv2.CAP_PROP_CONTRAST, self.config.cameras.contrast / 100.0)
                cap.set(cv2.CAP_PROP_SATURATION, self.config.cameras.saturation / 100.0)
                
                # 预热摄像头
                for _ in range(5):
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        break
                    time.sleep(0.1)
                
                if ret and frame is not None:
                    self.cameras[camera_id] = cap
                    self.camera_states[camera_id] = CameraState(camera_id)
                    self.logger.info(f"摄像头 {camera_id} 初始化成功")
                else:
                    self.logger.warning(f"摄像头 {camera_id} 无法读取帧")
                    cap.release()
                    
            except Exception as e:
                self.logger.error(f"摄像头 {camera_id} 初始化失败: {e}")
        
        active_cameras = len([c for c in self.cameras if c is not None])
        self.logger.info(f"成功初始化 {active_cameras} 个摄像头")
        return active_cameras > 0
    
    def initialize_mqtt(self) -> bool:
        """初始化MQTT连接"""
        try:
            from copy import deepcopy
            mqtt_config = deepcopy(self.config.mqtt)
            mqtt_config.client_id = "receiver"
            self.mqtt_client = MQTTClient(mqtt_config)
            
            if self.mqtt_client.connect():
                self.mqtt_client.set_message_callback(self._handle_mqtt_message)
                self.logger.info("MQTT连接成功")
                return True
            else:
                self.logger.error("MQTT连接失败")
                return False
                
        except Exception as e:
            self.logger.error(f"MQTT初始化失败: {e}")
            return False
    
    def _handle_mqtt_message(self, message_data: Dict) -> None:
        """处理MQTT消息"""
        try:
            payload_data = message_data.get('payload', {})
            ones_count = payload_data.get('count_of_ones', 0)
            is_update = message_data.get('is_update', False)
            
            self.logger.info(f"收到MQTT消息: {ones_count} ones, 更新: {is_update}")
            
            # 检查基线建立条件
            if ones_count == 144:
                self.logger.info("检测到144个ones，跳过基线建立")
                return
            
            if ones_count == 0:
                self.logger.info("ones数量为0，跳过基线建立")
                return
            
            if not is_update:
                self.logger.info("changeState内容无更新，跳过基线建立")
                return
            
            # 满足条件，建立基线
            self.logger.info("基线建立条件满足，开始建立基线")
            self.establish_baseline()
            
        except Exception as e:
            self.logger.error(f"处理MQTT消息错误: {e}")
    
    def establish_baseline(self) -> None:
        """建立基线"""
        self.logger.info("=== 开始建立基线 ===")
        
        # 等待0.1秒
        time.sleep(0.1)
        
        for camera_id, cap in enumerate(self.cameras):
            if cap is None or camera_id not in self.camera_states:
                continue
            
            try:
                # 捕获帧
                ret, frame = cap.read()
                if not ret or frame is None:
                    self.logger.warning(f"摄像头 {camera_id} 无法捕获基线帧")
                    continue
                
                # 检测红色光点
                red_count = self._extract_red_light_points(frame)
                
                # 设置基线
                state = self.camera_states[camera_id]
                state.baseline_red_count = red_count
                state.current_red_count = red_count
                state.baseline_established = True
                
                self.logger.info(f"摄像头 {camera_id} 基线: {red_count}/{len(self.light_points_template)} 个红色光点")
                
            except Exception as e:
                self.logger.error(f"摄像头 {camera_id} 基线建立失败: {e}")
        
        self.logger.info("=== 基线建立完成 ===")
    
    def monitor_changes(self) -> None:
        """监控变化"""
        self.logger.info("开始监控光点变化...")
        
        while True:
            try:
                for camera_id, cap in enumerate(self.cameras):
                    if cap is None or camera_id not in self.camera_states:
                        continue
                    
                    state = self.camera_states[camera_id]
                    if not state.baseline_established:
                        continue
                    
                    # 捕获帧
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        continue
                    
                    # 检测当前红色光点
                    current_count = self._extract_red_light_points(frame)
                    state.current_red_count = current_count
                    
                    # 检查变化
                    count_diff = abs(current_count - state.baseline_red_count)
                    if count_diff >= 1:
                        self.logger.info(f"摄像头 {camera_id} 检测到变化: "
                                       f"基线={state.baseline_red_count}, "
                                       f"当前={current_count}, "
                                       f"差异={count_diff}")
                        
                        # 触发MQTT
                        self._trigger_mqtt()
                
                # 每5秒输出状态
                time.sleep(5)
                self._log_status()
                
            except KeyboardInterrupt:
                self.logger.info("用户中断")
                break
            except Exception as e:
                self.logger.error(f"监控错误: {e}")
                time.sleep(1)
    
    def _trigger_mqtt(self) -> None:
        """触发MQTT消息"""
        try:
            if self.mqtt_client and self.mqtt_client.client:
                result = self.mqtt_client.client.publish(
                    self.config.mqtt.publish_topic, 
                    payload=""
                )
                if result.rc == 0:
                    self.logger.info("MQTT触发消息发送成功")
                else:
                    self.logger.error(f"MQTT触发消息发送失败: {result.rc}")
        except Exception as e:
            self.logger.error(f"触发MQTT消息错误: {e}")
    
    def _log_status(self) -> None:
        """输出状态"""
        for camera_id, state in self.camera_states.items():
            if state.baseline_established:
                self.logger.info(f"摄像头 {camera_id}: "
                               f"基线={state.baseline_red_count}, "
                               f"当前={state.current_red_count}")
    
    def run(self) -> None:
        """运行系统"""
        try:
            # 初始化摄像头
            if not self.initialize_cameras():
                self.logger.error("摄像头初始化失败")
                return
            
            # 初始化MQTT
            if not self.initialize_mqtt():
                self.logger.warning("MQTT初始化失败，继续运行")
            
            # 开始监控
            self.monitor_changes()
            
        except Exception as e:
            self.logger.error(f"系统运行错误: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self) -> None:
        """清理资源"""
        for cap in self.cameras:
            if cap is not None:
                cap.release()
        
        if self.mqtt_client:
            self.mqtt_client.disconnect()

def main():
    """主函数"""
    print("=== 简化生产环境系统 ===")
    print("消除线程和时序问题的生产系统")
    print("按 Ctrl+C 退出")
    print()
    
    if not os.path.exists("mask.png"):
        print("[ERROR] 未找到mask.png文件")
        return 1
    
    try:
        system = SimplifiedProductionSystem()
        system.run()
        return 0
        
    except Exception as e:
        print(f"[ERROR] 系统错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
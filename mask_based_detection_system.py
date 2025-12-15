#!/usr/bin/env python3
"""
基于mask的颜色变化检测系统
使用mask图片定义检测区域，监控指定区域内的颜色变化
"""

import cv2
import numpy as np
import time
import threading
import logging
import sys
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from mqtt_camera_monitoring.config import ConfigManager
from mqtt_camera_monitoring.mqtt_client import MQTTClient

@dataclass
class MaskPoint:
    """mask区域内的检测点"""
    x: int
    y: int
    baseline_color: Tuple[int, int, int]  # BGR颜色
    baseline_is_red: bool
    current_color: Tuple[int, int, int]
    current_is_red: bool
    changed: bool = False

@dataclass
class CameraMaskState:
    """摄像头mask检测状态"""
    camera_id: int
    mask_points: List[MaskPoint] = None
    baseline_established: bool = False
    last_detection_time: float = 0.0
    detection_count: int = 0
    change_count: int = 0

class MaskBasedDetectionSystem:
    """基于mask的检测系统"""
    
    def __init__(self, config_file: str = "config.yaml", mask_file: str = "m.png"):
        self.logger = logging.getLogger(__name__)
        
        # 加载配置
        config_manager = ConfigManager(config_file)
        self.config = config_manager.load_config()
        
        # 加载mask图片
        self.mask_file = mask_file
        self.mask_image = None
        self.mask_points_coords = []
        
        if not self._load_mask():
            raise ValueError(f"无法加载mask文件: {mask_file}")
        
        # 系统状态
        self.running = False
        self.mqtt_triggered = False
        self.baseline_capture_time = 0.0
        
        # 摄像头和检测器
        self.cameras: List[Optional[cv2.VideoCapture]] = []
        self.camera_states: Dict[int, CameraMaskState] = {}
        
        # MQTT客户端
        self.mqtt_client: Optional[MQTTClient] = None
        
        # 线程控制
        self.detection_thread: Optional[threading.Thread] = None
        self.detection_lock = threading.Lock()
        
        # 红色检测参数
        self.red_hsv_lower1 = np.array([0, 50, 50])
        self.red_hsv_upper1 = np.array([10, 255, 255])
        self.red_hsv_lower2 = np.array([170, 50, 50])
        self.red_hsv_upper2 = np.array([180, 255, 255])
        
        self.logger.info(f"基于mask的检测系统初始化完成，mask点数: {len(self.mask_points_coords)}")
    
    def _load_mask(self) -> bool:
        """加载mask图片并提取白色区域坐标"""
        if not os.path.exists(self.mask_file):
            self.logger.error(f"Mask文件不存在: {self.mask_file}")
            return False
        
        # 读取mask图片
        mask_img = cv2.imread(self.mask_file, cv2.IMREAD_GRAYSCALE)
        if mask_img is None:
            self.logger.error(f"无法读取mask文件: {self.mask_file}")
            return False
        
        # 目标摄像头分辨率 (从配置获取)
        target_width = 1280
        target_height = 720
        
        # 如果mask尺寸与目标不匹配，进行缩放
        if mask_img.shape != (target_height, target_width):
            self.logger.info(f"Mask原始尺寸: {mask_img.shape}, 目标尺寸: ({target_height}, {target_width})")
            
            # 缩放mask到目标分辨率
            mask_img = cv2.resize(mask_img, (target_width, target_height), interpolation=cv2.INTER_NEAREST)
            self.logger.info(f"Mask已缩放到: {mask_img.shape}")
        
        self.mask_image = mask_img
        
        # 提取白色区域的坐标点
        white_pixels = np.where(mask_img > 200)  # 白色像素阈值
        self.mask_points_coords = list(zip(white_pixels[1], white_pixels[0]))  # (x, y)
        
        self.logger.info(f"最终Mask尺寸: {mask_img.shape}")
        self.logger.info(f"检测到 {len(self.mask_points_coords)} 个mask点")
        
        return len(self.mask_points_coords) > 0
    
    def _is_red_color(self, bgr_color: Tuple[int, int, int]) -> bool:
        """判断BGR颜色是否为红色"""
        # 转换为HSV
        bgr_pixel = np.uint8([[bgr_color]])
        hsv_pixel = cv2.cvtColor(bgr_pixel, cv2.COLOR_BGR2HSV)[0][0]
        
        # 检查是否在红色HSV范围内
        in_range1 = (self.red_hsv_lower1[0] <= hsv_pixel[0] <= self.red_hsv_upper1[0] and
                     self.red_hsv_lower1[1] <= hsv_pixel[1] <= self.red_hsv_upper1[1] and
                     self.red_hsv_lower1[2] <= hsv_pixel[2] <= self.red_hsv_upper1[2])
        
        in_range2 = (self.red_hsv_lower2[0] <= hsv_pixel[0] <= self.red_hsv_upper2[0] and
                     self.red_hsv_lower2[1] <= hsv_pixel[1] <= self.red_hsv_upper2[1] and
                     self.red_hsv_lower2[2] <= hsv_pixel[2] <= self.red_hsv_upper2[2])
        
        return in_range1 or in_range2
    
    def _extract_mask_colors(self, frame: np.ndarray) -> List[MaskPoint]:
        """提取mask区域内各点的颜色"""
        mask_points = []
        
        for x, y in self.mask_points_coords:
            # 检查坐标是否在图像范围内
            if 0 <= y < frame.shape[0] and 0 <= x < frame.shape[1]:
                # 获取该点的BGR颜色
                bgr_color = tuple(frame[y, x].astype(int))
                is_red = self._is_red_color(bgr_color)
                
                mask_point = MaskPoint(
                    x=x, y=y,
                    baseline_color=bgr_color,
                    baseline_is_red=is_red,
                    current_color=bgr_color,
                    current_is_red=is_red
                )
                mask_points.append(mask_point)
        
        return mask_points
    
    def _compare_colors(self, baseline_points: List[MaskPoint], frame: np.ndarray) -> int:
        """比较当前帧与基线的颜色变化"""
        change_count = 0
        
        for point in baseline_points:
            x, y = point.x, point.y
            
            # 检查坐标是否在图像范围内
            if 0 <= y < frame.shape[0] and 0 <= x < frame.shape[1]:
                # 获取当前颜色
                current_bgr = tuple(frame[y, x].astype(int))
                current_is_red = self._is_red_color(current_bgr)
                
                # 更新当前状态
                point.current_color = current_bgr
                point.current_is_red = current_is_red
                
                # 检查变化：基线是红色但现在不是红色，或者基线不是红色但现在是红色
                if point.baseline_is_red != current_is_red:
                    point.changed = True
                    change_count += 1
                else:
                    point.changed = False
        
        return change_count
    
    def initialize_cameras(self) -> bool:
        """初始化摄像头"""
        self.logger.info(f"初始化 {self.config.cameras.count} 个摄像头...")
        
        self.cameras = [None] * self.config.cameras.count
        
        for camera_id in range(self.config.cameras.count):
            try:
                # 延迟初始化避免冲突
                if camera_id > 0:
                    time.sleep(0.3)
                
                self.logger.info(f"初始化摄像头 {camera_id}...")
                
                # 使用DirectShow后端
                cap = None
                for attempt in range(3):
                    try:
                        cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
                        if cap.isOpened():
                            break
                        if cap:
                            cap.release()
                        time.sleep(0.5)
                    except Exception as e:
                        self.logger.warning(f"摄像头 {camera_id} 初始化尝试 {attempt+1} 失败: {e}")
                        if cap:
                            cap.release()
                        cap = None
                
                if not cap or not cap.isOpened():
                    self.logger.warning(f"摄像头 {camera_id} 无法打开")
                    if cap:
                        cap.release()
                    continue
                
                # 配置摄像头 - 使用720p分辨率 (1280x720)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                cap.set(cv2.CAP_PROP_FPS, 30)
                
                # 设置曝光参数
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
                    self.camera_states[camera_id] = CameraMaskState(camera_id)
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
            self.logger.info("初始化MQTT连接...")
            
            from copy import deepcopy
            mqtt_config = deepcopy(self.config.mqtt)
            mqtt_config.client_id = "receiver"
            self.mqtt_client = MQTTClient(mqtt_config)
            if self.mqtt_client.connect():
                self.mqtt_client.set_message_callback(self._handle_mqtt_message)
                self.logger.info(f"MQTT接收客户端连接成功 (Client ID: {mqtt_config.client_id})")
            else:
                self.logger.error("MQTT接收客户端连接失败")
                return False
            
            self.logger.info("MQTT初始化完成，使用单一receiver客户端")
            return True
            
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
            
            # 获取配置参数
            exclude_ones = getattr(self.config.red_light_detection, 'exclude_ones_count', 144)
            require_update = getattr(self.config.red_light_detection, 'require_content_update', True)
            
            # 优先检查排除条件
            if ones_count == exclude_ones:
                self.logger.info(f"检测到{exclude_ones}个ones，强制跳过基线建立")
                return
            
            # 检查其他基线建立条件
            should_establish_baseline = False
            reason = ""
            
            if ones_count == 0:
                reason = f"ones数量为0"
                self.logger.debug(f"{reason}，跳过基线建立")
            elif require_update and not is_update:
                reason = f"changeState内容无更新"
                self.logger.debug(f"{reason}，跳过基线建立")
            elif ones_count > 0 and (not require_update or is_update):
                should_establish_baseline = True
                reason = f"满足所有条件"
            
            if should_establish_baseline:
                self.logger.info(f"[OK] 基线建立条件满足: ones={ones_count}, 更新={is_update}, 开始基线建立")
                self.mqtt_triggered = True
                self.baseline_capture_time = time.time() + 0.1
                
                # 重置所有摄像头状态
                with self.detection_lock:
                    for state in self.camera_states.values():
                        state.baseline_established = False
                        state.mask_points = None
                        state.detection_count = 0
                        state.change_count = 0
            else:
                self.logger.info(f"[SKIP] 基线建立条件不满足: {reason}")
                
        except Exception as e:
            self.logger.error(f"处理MQTT消息错误: {e}")
    
    def capture_baseline(self) -> None:
        """捕获基线数据"""
        self.logger.info("开始捕获mask区域基线数据...")
        
        with self.detection_lock:
            for camera_id, cap in enumerate(self.cameras):
                if cap is None or camera_id not in self.camera_states:
                    continue
                
                try:
                    # 捕获帧
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        self.logger.warning(f"摄像头 {camera_id} 无法捕获基线帧")
                        continue
                    
                    # 提取mask区域的颜色信息
                    mask_points = self._extract_mask_colors(frame)
                    
                    # 统计红色点数量
                    red_count = sum(1 for point in mask_points if point.baseline_is_red)
                    
                    # 设置基线
                    state = self.camera_states[camera_id]
                    state.mask_points = mask_points
                    state.baseline_established = True
                    state.last_detection_time = time.time()
                    
                    self.logger.info(f"摄像头 {camera_id} 基线设置: mask点数={len(mask_points)}, 红色点数={red_count}")
                    
                except Exception as e:
                    self.logger.error(f"摄像头 {camera_id} 基线捕获失败: {e}")
        
        self.logger.info("基线捕获完成")
    
    def detect_and_compare(self) -> None:
        """检测并比较颜色变化"""
        current_time = time.time()
        
        with self.detection_lock:
            for camera_id, cap in enumerate(self.cameras):
                if cap is None or camera_id not in self.camera_states:
                    continue
                
                state = self.camera_states[camera_id]
                
                # 检查是否需要检测
                if not state.baseline_established or state.mask_points is None:
                    continue
                
                # 检查检测间隔（0.2秒）
                if current_time - state.last_detection_time < 0.2:
                    continue
                
                try:
                    # 捕获帧
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        continue
                    
                    # 比较颜色变化
                    change_count = self._compare_colors(state.mask_points, frame)
                    state.detection_count += 1
                    state.last_detection_time = current_time
                    state.change_count = change_count
                    
                    # 检查是否有颜色变化
                    if change_count > 0:
                        self.logger.info(f"摄像头 {camera_id} 检测到颜色变化: {change_count} 个点发生变化")
                        
                        # 触发MQTT消息
                        self._trigger_mqtt_message(camera_id, change_count)
                    
                    # 定期输出状态
                    if state.detection_count % 25 == 0:  # 每5秒输出一次
                        red_count = sum(1 for point in state.mask_points if point.current_is_red)
                        self.logger.info(f"摄像头 {camera_id} 状态: "
                                       f"mask点数={len(state.mask_points)}, "
                                       f"当前红色点数={red_count}, "
                                       f"变化点数={change_count}, "
                                       f"检测次数={state.detection_count}")
                    
                except Exception as e:
                    self.logger.error(f"摄像头 {camera_id} 检测失败: {e}")
    
    def _trigger_mqtt_message(self, camera_id: int, change_count: int) -> None:
        """触发MQTT消息"""
        try:
            if self.mqtt_client and self.mqtt_client.client:
                result = self.mqtt_client.client.publish(
                    self.config.mqtt.publish_topic, 
                    payload=""
                )
                
                if result.rc == 0:
                    self.logger.info(f"摄像头 {camera_id} 触发MQTT消息成功 (颜色变化点数: {change_count})")
                else:
                    self.logger.error(f"摄像头 {camera_id} 触发MQTT消息失败: {result.rc}")
            else:
                self.logger.error("MQTT客户端未连接，无法发送触发消息")
            
        except Exception as e:
            self.logger.error(f"触发MQTT消息错误: {e}")
    
    def detection_loop(self) -> None:
        """检测循环"""
        self.logger.info("开始mask颜色变化检测循环")
        
        while self.running:
            try:
                current_time = time.time()
                
                # 检查是否需要捕获基线
                if self.mqtt_triggered and current_time >= self.baseline_capture_time:
                    self.capture_baseline()
                    self.mqtt_triggered = False
                
                # 执行检测和比较
                self.detect_and_compare()
                
                # 短暂休眠
                time.sleep(0.05)  # 20 FPS检测频率
                
            except Exception as e:
                self.logger.error(f"检测循环错误: {e}")
                time.sleep(1)
        
        self.logger.info("检测循环结束")
    
    def start(self) -> bool:
        """启动系统"""
        try:
            self.logger.info("启动基于mask的颜色变化检测系统")
            
            # 初始化摄像头
            if not self.initialize_cameras():
                self.logger.error("摄像头初始化失败")
                return False
            
            # 初始化MQTT
            mqtt_ok = self.initialize_mqtt()
            if not mqtt_ok:
                self.logger.warning("MQTT初始化失败，继续运行检测功能")
            
            # 启动检测线程
            self.running = True
            self.detection_thread = threading.Thread(target=self.detection_loop, daemon=True)
            self.detection_thread.start()
            
            self.logger.info("基于mask的检测系统启动成功")
            return True
            
        except Exception as e:
            self.logger.error(f"系统启动失败: {e}")
            return False
    
    def stop(self) -> None:
        """停止系统"""
        try:
            self.logger.info("停止基于mask的检测系统")
            
            self.running = False
            
            # 等待检测线程结束
            if self.detection_thread and self.detection_thread.is_alive():
                self.detection_thread.join(timeout=2.0)
            
            # 释放摄像头
            for cap in self.cameras:
                if cap is not None:
                    cap.release()
            
            # 断开MQTT连接
            if self.mqtt_client:
                self.mqtt_client.disconnect()
            
            self.logger.info("基于mask的检测系统已停止")
            
        except Exception as e:
            self.logger.error(f"系统停止错误: {e}")
    
    def get_status(self) -> Dict:
        """获取系统状态"""
        with self.detection_lock:
            status = {
                'running': self.running,
                'mqtt_triggered': self.mqtt_triggered,
                'active_cameras': len([c for c in self.cameras if c is not None]),
                'mask_points_total': len(self.mask_points_coords),
                'camera_states': {}
            }
            
            for camera_id, state in self.camera_states.items():
                if state.mask_points:
                    red_count = sum(1 for point in state.mask_points if point.current_is_red)
                    changed_count = sum(1 for point in state.mask_points if point.changed)
                else:
                    red_count = 0
                    changed_count = 0
                
                status['camera_states'][camera_id] = {
                    'baseline_established': state.baseline_established,
                    'mask_points_count': len(state.mask_points) if state.mask_points else 0,
                    'current_red_count': red_count,
                    'changed_count': changed_count,
                    'detection_count': state.detection_count
                }
            
            return status

def setup_logging():
    """设置日志"""
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    file_handler = logging.FileHandler('mask_detection.log', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    logging.basicConfig(
        level=logging.INFO,
        handlers=[console_handler, file_handler]
    )

def main():
    """主函数"""
    print("=== 基于mask的颜色变化检测系统 ===")
    print("使用mask图片定义检测区域")
    print("监控mask区域内红色光点的颜色变化")
    print("按 Ctrl+C 退出")
    print()
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # 检查mask文件
    mask_file = "m.png"
    if not os.path.exists(mask_file):
        print(f"[ERROR] 未找到mask文件: {mask_file}")
        print("请确保mask文件存在于当前目录")
        return 1
    
    system = None
    
    try:
        # 创建检测系统
        system = MaskBasedDetectionSystem(mask_file=mask_file)
        
        # 启动系统
        if not system.start():
            logger.error("系统启动失败")
            return 1
        
        # 主循环 - 定期输出状态
        while True:
            time.sleep(10)  # 每10秒输出状态
            
            status = system.get_status()
            logger.info(f"系统状态: 运行={status['running']}, "
                       f"活跃摄像头={status['active_cameras']}, "
                       f"mask点数={status['mask_points_total']}, "
                       f"MQTT触发={status['mqtt_triggered']}")
            
            # 输出摄像头状态
            for camera_id, state in status['camera_states'].items():
                if state['baseline_established']:
                    logger.info(f"摄像头 {camera_id}: "
                               f"mask点数={state['mask_points_count']}, "
                               f"红色点数={state['current_red_count']}, "
                               f"变化点数={state['changed_count']}, "
                               f"检测次数={state['detection_count']}")
    
    except KeyboardInterrupt:
        logger.info("用户中断")
    except Exception as e:
        logger.error(f"系统错误: {e}")
        return 1
    finally:
        if system:
            system.stop()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
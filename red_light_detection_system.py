#!/usr/bin/env python3
"""
红光检测系统 - 纯检测模式，不显示画面
监控红光面积变化，触发MQTT消息
"""

import cv2
import numpy as np
import time
import threading
import logging
import sys
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from mqtt_camera_monitoring.config import ConfigManager
from mqtt_camera_monitoring.mqtt_client import MQTTClient
from mqtt_camera_monitoring.light_detector import RedLightDetector

@dataclass
class CameraDetectionState:
    """摄像头检测状态"""
    camera_id: int
    baseline_count: int = 0
    current_count: int = 0
    baseline_established: bool = False
    last_detection_time: float = 0.0
    detection_count: int = 0

class RedLightDetectionSystem:
    """红光检测系统"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.logger = logging.getLogger(__name__)
        
        # 加载配置
        config_manager = ConfigManager(config_file)
        self.config = config_manager.load_config()
        
        # 系统状态
        self.running = False
        self.mqtt_triggered = False
        self.baseline_capture_time = 0.0
        
        # 摄像头和检测器
        self.cameras: List[Optional[cv2.VideoCapture]] = []
        self.camera_states: Dict[int, CameraDetectionState] = {}
        self.light_detector = RedLightDetector(self.config.red_light_detection)
        
        # MQTT客户端 - 使用receiver作为client ID
        self.mqtt_client: Optional[MQTTClient] = None
        
        # 线程控制
        self.detection_thread: Optional[threading.Thread] = None
        self.detection_lock = threading.Lock()
        
        # 输出触发阈值信息
        threshold = getattr(self.config.red_light_detection, 'count_decrease_threshold', 3)
        self.logger.info(f"红光检测系统初始化完成 (触发阈值: 减少{threshold}个红光)")
        self.logger.info(f"触发条件: 红光数量减少 >= {threshold}个时发送MQTT消息")
    
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
                
                # 使用DirectShow后端，添加更多重试机制
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
                
                # 配置摄像头
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                cap.set(cv2.CAP_PROP_FPS, 30)
                
                # 设置曝光参数 - 优化红光检测
                cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # 关闭自动曝光
                cap.set(cv2.CAP_PROP_EXPOSURE, self.config.cameras.exposure)
                cap.set(cv2.CAP_PROP_BRIGHTNESS, self.config.cameras.brightness / 100.0)
                cap.set(cv2.CAP_PROP_CONTRAST, self.config.cameras.contrast / 100.0)
                cap.set(cv2.CAP_PROP_SATURATION, self.config.cameras.saturation / 100.0)
                
                # 设置增益和白平衡
                if hasattr(self.config.cameras, 'gain'):
                    cap.set(cv2.CAP_PROP_GAIN, self.config.cameras.gain)
                if hasattr(self.config.cameras, 'white_balance'):
                    cap.set(cv2.CAP_PROP_WHITE_BALANCE_BLUE_U, self.config.cameras.white_balance)
                
                # 预热摄像头
                for _ in range(5):
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        break
                    time.sleep(0.1)
                
                if ret and frame is not None:
                    self.cameras[camera_id] = cap
                    self.camera_states[camera_id] = CameraDetectionState(camera_id)
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
            
            # MQTT接收客户端 - 确保使用receiver作为client ID
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
            
            # 不使用TriggerPublisher，直接在主客户端发送触发消息
            # 这样确保只有一个"receiver"客户端连接
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
            
            # 检查是否满足基线建立条件
            if is_update and ones_count > 0:
                # 排除144个one的情况
                if ones_count == 144:
                    self.logger.info(f"检测到144个ones，跳过基线建立")
                    return
                
                self.logger.info(f"检测到changeState内容更新且ones={ones_count}，开始基线建立")
                self.mqtt_triggered = True
                self.baseline_capture_time = time.time() + 0.1  # 0.1秒后捕获基线
                
                # 重置所有摄像头状态
                with self.detection_lock:
                    for state in self.camera_states.values():
                        state.baseline_established = False
                        state.baseline_count = 0
                        state.current_count = 0
                        state.detection_count = 0
            else:
                # 记录不满足条件的情况
                if not is_update:
                    self.logger.debug(f"changeState内容无更新，跳过基线建立")
                elif ones_count == 0:
                    self.logger.debug(f"ones数量为0，跳过基线建立")
                
        except Exception as e:
            self.logger.error(f"处理MQTT消息错误: {e}")
    
    def capture_baseline(self) -> None:
        """捕获基线数据"""
        self.logger.info("开始捕获基线数据...")
        
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
                    
                    # 检测红光
                    detection = self.light_detector.detect_red_lights(frame)
                    
                    # 设置基线
                    state = self.camera_states[camera_id]
                    state.baseline_count = detection.count
                    state.baseline_established = True
                    state.last_detection_time = time.time()
                    
                    self.logger.info(f"摄像头 {camera_id} 基线设置: 数量={detection.count}")
                    
                except Exception as e:
                    self.logger.error(f"摄像头 {camera_id} 基线捕获失败: {e}")
        
        self.logger.info("基线捕获完成")
    
    def detect_and_compare(self) -> None:
        """检测并比较红光面积"""
        current_time = time.time()
        
        with self.detection_lock:
            for camera_id, cap in enumerate(self.cameras):
                if cap is None or camera_id not in self.camera_states:
                    continue
                
                state = self.camera_states[camera_id]
                
                # 检查是否需要检测
                if not state.baseline_established:
                    continue
                
                # 检查检测间隔（0.2秒）
                if current_time - state.last_detection_time < 0.2:
                    continue
                
                try:
                    # 捕获帧
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        continue
                    
                    # 检测红光
                    detection = self.light_detector.detect_red_lights(frame)
                    state.current_count = detection.count
                    state.detection_count += 1
                    state.last_detection_time = current_time
                    
                    # 检查红光数量是否减少达到阈值
                    count_change = state.current_count - state.baseline_count
                    decrease_threshold = getattr(self.config.red_light_detection, 'count_decrease_threshold', 3)
                    
                    if count_change <= -decrease_threshold:  # 减少达到阈值才触发
                        self.logger.info(f"摄像头 {camera_id} 检测到显著减少: "
                                       f"基线={state.baseline_count}, "
                                       f"当前={state.current_count}, "
                                       f"减少={abs(count_change)}个 (阈值: {decrease_threshold})")
                        
                        # 触发MQTT消息
                        self._trigger_mqtt_message(camera_id, count_change)
                    elif state.current_count != state.baseline_count:
                        # 记录变化但不触发
                        self.logger.debug(f"摄像头 {camera_id} 检测到轻微变化: "
                                        f"基线={state.baseline_count}, "
                                        f"当前={state.current_count}, "
                                        f"变化={count_change}个 (未达到触发阈值-{decrease_threshold})")
                    
                    # 定期输出状态
                    if state.detection_count % 25 == 0:  # 每5秒输出一次
                        self.logger.info(f"摄像头 {camera_id} 状态: "
                                       f"基线={state.baseline_count}, "
                                       f"当前={state.current_count}, "
                                       f"检测次数={state.detection_count}")
                    
                    # 如果检测到红光，输出更详细信息
                    if detection.count > 0 and state.detection_count % 10 == 0:
                        self.logger.info(f"摄像头 {camera_id} 检测详情: "
                                       f"红光数量={detection.count}, "
                                       f"总面积={detection.total_area:.2f}, "
                                       f"边界框数量={len(detection.bounding_boxes)}")
                    
                except Exception as e:
                    self.logger.error(f"摄像头 {camera_id} 检测失败: {e}")
    
    def _trigger_mqtt_message(self, camera_id: int, count_change: int) -> None:
        """触发MQTT消息"""
        try:
            if self.mqtt_client and self.mqtt_client.client:
                # 直接使用主MQTT客户端发送触发消息
                result = self.mqtt_client.client.publish(
                    self.config.mqtt.publish_topic, 
                    payload=""
                )
                
                if result.rc == 0:
                    self.logger.info(f"摄像头 {camera_id} 触发MQTT消息成功 (数量变化: {count_change:+d})")
                else:
                    self.logger.error(f"摄像头 {camera_id} 触发MQTT消息失败: {result.rc}")
            else:
                self.logger.error("MQTT客户端未连接，无法发送触发消息")
            
        except Exception as e:
            self.logger.error(f"触发MQTT消息错误: {e}")
    
    def detection_loop(self) -> None:
        """检测循环"""
        self.logger.info("开始检测循环")
        
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
            self.logger.info("启动红光检测系统")
            
            # 初始化摄像头
            if not self.initialize_cameras():
                self.logger.error("摄像头初始化失败")
                return False
            
            # 初始化MQTT (可选)
            mqtt_ok = self.initialize_mqtt()
            if not mqtt_ok:
                self.logger.warning("MQTT初始化失败，继续运行检测功能")
            
            # 启动检测线程
            self.running = True
            self.detection_thread = threading.Thread(target=self.detection_loop, daemon=True)
            self.detection_thread.start()
            
            self.logger.info("红光检测系统启动成功")
            return True
            
        except Exception as e:
            self.logger.error(f"系统启动失败: {e}")
            return False
    
    def stop(self) -> None:
        """停止系统"""
        try:
            self.logger.info("停止红光检测系统")
            
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
            
            self.logger.info("红光检测系统已停止")
            
        except Exception as e:
            self.logger.error(f"系统停止错误: {e}")
    
    def get_status(self) -> Dict:
        """获取系统状态"""
        with self.detection_lock:
            status = {
                'running': self.running,
                'mqtt_triggered': self.mqtt_triggered,
                'active_cameras': len([c for c in self.cameras if c is not None]),
                'camera_states': {}
            }
            
            for camera_id, state in self.camera_states.items():
                status['camera_states'][camera_id] = {
                    'baseline_established': state.baseline_established,
                    'baseline_count': state.baseline_count,
                    'current_count': state.current_count,
                    'detection_count': state.detection_count
                }
            
            return status

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('red_light_detection.log')
        ]
    )

def main():
    """主函数"""
    print("=== 红光检测系统 ===")
    print("纯检测模式，监控红光面积变化")
    print("等待changeState触发...")
    print("按 Ctrl+C 退出")
    print()
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    system = None
    
    try:
        # 创建检测系统
        system = RedLightDetectionSystem()
        
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
                       f"MQTT触发={status['mqtt_triggered']}")
            
            # 输出摄像头状态
            for camera_id, state in status['camera_states'].items():
                if state['baseline_established']:
                    logger.info(f"摄像头 {camera_id}: "
                               f"基线={state['baseline_count']}, "
                               f"当前={state['current_count']}, "
                               f"检测={state['detection_count']}")
    
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
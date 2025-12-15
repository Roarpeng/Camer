"""
增强主控制器 - 支持异步初始化和实时进度显示
"""

import logging
import time
import threading
import signal
import sys
from typing import Dict, Any, Optional, List
from .camera_manager import CameraFrame
from .config import SystemConfig
from .mqtt_client import MQTTClient
from .async_camera_manager import AsyncCameraManager
from .light_detector import RedLightDetector
from .trigger_publisher import TriggerPublisher
from .enhanced_lightweight_monitor import EnhancedLightweightMonitor


class EnhancedMainController:
    """增强主控制器 - 优化初始化速度和用户体验"""
    
    def __init__(self, config: SystemConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 系统状态
        self.running = False
        self.initialized = False
        self.shutdown_requested = False
        
        # 组件实例
        self.mqtt_client: Optional[MQTTClient] = None
        self.camera_manager: Optional[AsyncCameraManager] = None
        self.light_detector: Optional[RedLightDetector] = None
        self.trigger_publisher: Optional[TriggerPublisher] = None
        self.visual_monitor: Optional[EnhancedLightweightMonitor] = None
        
        # 线程管理
        self.main_loop_thread: Optional[threading.Thread] = None
        self.monitoring_active = False
        
        # 初始化状态
        self.mqtt_connected = False
        self.cameras_initialized = False
        self.active_camera_ids: List[int] = []
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        
        self.logger.info("EnhancedMainController initialized")
    
    def initialize_system(self) -> bool:
        """初始化系统 - 并行处理MQTT和摄像头"""
        try:
            self.logger.info("Initializing Enhanced MQTT Camera Monitoring System")
            
            # 首先创建视觉监控器
            self.logger.info("Initializing visual monitor...")
            self.visual_monitor = EnhancedLightweightMonitor(
                self.config.visual_monitor, 
                self.config.cameras.count
            )
            
            if not self.visual_monitor.create_windows():
                self.logger.error("Failed to create visual monitor")
                return False
            
            # 添加日志条目
            self.visual_monitor.add_log_entry("INFO", "系统启动中...")
            self.visual_monitor.add_log_entry("INFO", "创建显示窗口完成")
            
            # 并行初始化MQTT和摄像头
            mqtt_thread = threading.Thread(target=self._initialize_mqtt, daemon=True)
            camera_thread = threading.Thread(target=self._initialize_cameras, daemon=True)
            
            self.visual_monitor.add_log_entry("INFO", "开始并行初始化MQTT和摄像头...")
            
            mqtt_thread.start()
            camera_thread.start()
            
            # 等待MQTT连接完成（快速）
            mqtt_thread.join(timeout=10)
            
            # 摄像头初始化在后台继续进行
            self.visual_monitor.add_log_entry("INFO", f"MQTT连接: {'成功' if self.mqtt_connected else '失败'}")
            
            # 初始化其他组件
            self._initialize_other_components()
            
            # 等待摄像头初始化完成
            camera_thread.join(timeout=30)
            
            self.visual_monitor.add_log_entry("INFO", f"摄像头初始化: {'完成' if self.cameras_initialized else '超时'}")
            self.visual_monitor.add_log_entry("INFO", f"活跃摄像头: {len(self.active_camera_ids)}")
            
            self.initialized = True
            self.visual_monitor.add_log_entry("INFO", "系统初始化完成")
            
            return True
            
        except Exception as e:
            self.logger.error(f"System initialization failed: {e}")
            if self.visual_monitor:
                self.visual_monitor.add_log_entry("ERROR", f"系统初始化失败: {e}")
            return False
    
    def _initialize_mqtt(self) -> None:
        """初始化MQTT连接"""
        try:
            self.visual_monitor.add_log_entry("INFO", "连接MQTT服务器...")
            
            self.mqtt_client = MQTTClient(self.config.mqtt)
            if self.mqtt_client.connect():
                self.mqtt_client.set_message_callback(self._handle_mqtt_message)
                self.mqtt_connected = True
                self.visual_monitor.add_log_entry("INFO", "MQTT连接成功")
            else:
                self.visual_monitor.add_log_entry("ERROR", "MQTT连接失败")
                
        except Exception as e:
            self.logger.error(f"MQTT initialization failed: {e}")
            self.visual_monitor.add_log_entry("ERROR", f"MQTT初始化失败: {e}")
    
    def _initialize_cameras(self) -> None:
        """异步初始化摄像头"""
        try:
            self.visual_monitor.add_log_entry("INFO", "开始初始化摄像头...")
            
            # 创建异步摄像头管理器
            self.camera_manager = AsyncCameraManager(self.config.cameras)
            
            # 设置进度回调
            self.camera_manager.set_progress_callback(self._on_camera_progress)
            self.camera_manager.set_completion_callback(self._on_camera_completion)
            
            # 开始异步初始化
            self.camera_manager.initialize_cameras_async()
            
        except Exception as e:
            self.logger.error(f"Camera initialization failed: {e}")
            self.visual_monitor.add_log_entry("ERROR", f"摄像头初始化失败: {e}")
    
    def _on_camera_progress(self, current: int, total: int, status: str) -> None:
        """摄像头初始化进度回调"""
        self.visual_monitor.update_initialization_progress(current, total, status)
    
    def _on_camera_completion(self, active_cameras: List[int]) -> None:
        """摄像头初始化完成回调"""
        self.active_camera_ids = active_cameras
        self.cameras_initialized = True
        self.visual_monitor.add_log_entry("INFO", f"摄像头初始化完成，活跃摄像头: {active_cameras}")
        
        # 启动连续捕获
        if self.camera_manager:
            self.camera_manager.start_continuous_capture()
            self.visual_monitor.add_log_entry("INFO", "开始连续帧捕获")
    
    def _initialize_other_components(self) -> None:
        """初始化其他组件"""
        try:
            # 初始化红光检测器
            self.visual_monitor.add_log_entry("INFO", "初始化红光检测器...")
            self.light_detector = RedLightDetector(self.config.red_light_detection)
            
            # 初始化触发发布器
            if self.mqtt_connected:
                self.visual_monitor.add_log_entry("INFO", "初始化触发发布器...")
                self.trigger_publisher = TriggerPublisher(self.config.mqtt)
                if self.trigger_publisher.connect():
                    self.visual_monitor.add_log_entry("INFO", "触发发布器连接成功")
                else:
                    self.visual_monitor.add_log_entry("WARNING", "触发发布器连接失败")
            
        except Exception as e:
            self.logger.error(f"Other components initialization failed: {e}")
            self.visual_monitor.add_log_entry("ERROR", f"组件初始化失败: {e}")
    
    def start_monitoring(self) -> bool:
        """启动监控循环"""
        if not self.initialized:
            self.logger.error("System not initialized")
            return False
        
        try:
            self.running = True
            self.monitoring_active = True
            
            # 启动主监控线程
            self.main_loop_thread = threading.Thread(target=self._main_monitoring_loop, daemon=True)
            self.main_loop_thread.start()
            
            self.visual_monitor.add_log_entry("INFO", "监控循环已启动")
            self.logger.info("Main monitoring loop started")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start monitoring: {e}")
            self.visual_monitor.add_log_entry("ERROR", f"启动监控失败: {e}")
            return False
    
    def _main_monitoring_loop(self) -> None:
        """主监控循环"""
        self.logger.info("Starting main monitoring loop")
        
        frame_count = 0
        last_status_update = time.time()
        
        try:
            while self.running and not self.shutdown_requested:
                current_time = time.time()
                
                # 捕获摄像头帧
                if self.camera_manager and self.camera_manager.is_initialization_complete():
                    frames = self.camera_manager.capture_frames()
                    
                    # 调试：检查帧数据
                    valid_frames = sum(1 for f in frames if f and f.is_valid)
                    if frame_count % 50 == 0 and valid_frames > 0:  # 每5秒记录一次
                        self.visual_monitor.add_log_entry("DEBUG", f"捕获到 {valid_frames} 个有效帧")
                    
                    # 更新显示（包含红光检测）
                    if self.visual_monitor:
                        self._update_visual_display(frames)
                    
                    # 处理红光检测
                    if self.light_detector and frames:
                        self._process_light_detection(frames)
                    
                    frame_count += 1
                else:
                    # 摄像头未初始化完成时的调试信息
                    if frame_count % 50 == 0:
                        init_status = "完成" if (self.camera_manager and self.camera_manager.is_initialization_complete()) else "进行中"
                        self.visual_monitor.add_log_entry("DEBUG", f"摄像头初始化状态: {init_status}")
                
                # 定期状态更新
                if current_time - last_status_update > 10:  # 每10秒
                    active_cameras = len(self.active_camera_ids) if self.cameras_initialized else 0
                    self.visual_monitor.add_log_entry("INFO", 
                        f"运行状态: {frame_count}帧, {active_cameras}摄像头活跃")
                    last_status_update = current_time
                    frame_count = 0
                
                # 控制循环频率
                time.sleep(0.1)  # 10 FPS
                
        except Exception as e:
            self.logger.error(f"Error in main monitoring loop: {e}")
            self.visual_monitor.add_log_entry("ERROR", f"监控循环错误: {e}")
        finally:
            self.monitoring_active = False
            self.logger.info("Main monitoring loop ended")
    
    def _process_light_detection(self, frames: List[Any]) -> None:
        """处理红光检测"""
        try:
            # 简化的检测逻辑
            for camera_id, frame in enumerate(frames):
                if frame and frame.is_valid:
                    # 这里可以添加实际的红光检测逻辑
                    pass
                    
        except Exception as e:
            self.logger.error(f"Error in light detection: {e}")
    
    def _handle_mqtt_message(self, message_data: Dict[str, Any]) -> None:
        """处理MQTT消息"""
        try:
            # 从消息数据中提取信息
            topic = message_data.get('topic', 'unknown')
            payload_data = message_data.get('payload', {})
            is_update = message_data.get('is_update', False)
            
            # 获取ones计数
            ones_count = payload_data.get('count_of_ones', 0)
            
            self.logger.info(f"MQTT message received on topic '{topic}' with {ones_count} ones (update: {is_update})")
            
            # 添加到日志
            if self.visual_monitor:
                self.visual_monitor.add_log_entry("INFO", f"MQTT消息: {ones_count} ones", None)
            
            # 检查是否需要激活摄像头
            if ones_count > 0 and is_update:
                self.logger.info("MQTT message update detected, activating cameras")
                if self.camera_manager:
                    self.camera_manager.activate_cameras()
                self.logger.info("Cameras activated successfully")
                
                # 重置基线
                if self.light_detector:
                    self.light_detector.reset_baselines()
                    self.light_detector.start_baseline_establishment()
                    self.logger.info("Baseline establishment process started")
                    
        except Exception as e:
            self.logger.error(f"Error handling MQTT message: {e}")
            if self.visual_monitor:
                self.visual_monitor.add_log_entry("ERROR", f"MQTT消息处理错误: {e}")
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.visual_monitor.add_log_entry("INFO", f"接收到信号 {signum}，正在关闭系统...")
        self.shutdown_system()
    
    def shutdown_system(self) -> None:
        """关闭系统"""
        try:
            self.logger.info("Shutting down Enhanced MQTT Camera Monitoring System")
            self.visual_monitor.add_log_entry("INFO", "正在关闭系统...")
            
            self.running = False
            self.shutdown_requested = True
            
            # 停止摄像头捕获
            if self.camera_manager:
                self.logger.info("Stopping camera capture...")
                self.camera_manager.stop_continuous_capture()
            
            # 等待主循环结束
            if self.main_loop_thread and self.main_loop_thread.is_alive():
                self.main_loop_thread.join(timeout=2.0)
            
            # 关闭视觉监控器
            if self.visual_monitor:
                self.logger.info("Closing visual monitor...")
                self.visual_monitor.add_log_entry("INFO", "关闭显示窗口...")
                time.sleep(1)  # 让用户看到消息
                self.visual_monitor.close_windows()
            
            # 断开MQTT连接
            if self.mqtt_client:
                self.logger.info("Disconnecting MQTT client...")
                self.mqtt_client.disconnect()
            
            # 断开触发发布器
            if self.trigger_publisher:
                self.logger.info("Disconnecting trigger publisher...")
                self.trigger_publisher.disconnect()
            
            # 释放摄像头资源
            if self.camera_manager:
                self.logger.info("Releasing camera resources...")
                self.camera_manager.release_cameras()
            
            self.logger.info("System shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during system shutdown: {e}")
    
    def run(self) -> int:
        """运行系统"""
        try:
            # 初始化系统
            if not self.initialize_system():
                self.logger.error("System initialization failed")
                return 1
            
            # 启动监控
            if not self.start_monitoring():
                self.logger.error("Failed to start monitoring")
                return 1
            
            # 保持运行直到收到关闭信号
            try:
                while self.running and not self.shutdown_requested:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received")
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Unexpected error in main run: {e}")
            return 1
        finally:
            self.shutdown_system()
    
    def _update_visual_display(self, frames: List[Optional[CameraFrame]]) -> None:
        """更新视觉显示，包含红光检测结果"""
        if not self.visual_monitor:
            return
        
        try:
            # 执行红光检测
            detection_results = []
            for frame in frames:
                if frame and frame.is_valid and frame.frame is not None and self.light_detector:
                    try:
                        detection = self.light_detector.detect_red_lights(frame.frame)
                        detection_results.append(detection)
                    except Exception as e:
                        self.logger.error(f"Red light detection error: {e}")
                        detection_results.append(None)
                else:
                    detection_results.append(None)
            
            # 更新显示
            self.visual_monitor.update_display(frames, detection_results)
            
        except Exception as e:
            self.logger.error(f"Error updating visual display: {e}")
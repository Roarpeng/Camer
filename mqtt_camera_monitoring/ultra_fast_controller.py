"""
超快速主控制器 - 专注速度和稳定性
"""

import logging
import time
import threading
import signal
import sys
from typing import Dict, Any, Optional, List
from .config import SystemConfig
from .mqtt_client import MQTTClient
from .fast_camera_manager import FastCameraManager
from .light_detector import RedLightDetector
from .trigger_publisher import TriggerPublisher
from .enhanced_lightweight_monitor import EnhancedLightweightMonitor


class UltraFastController:
    """超快速主控制器 - 极致优化的性能"""
    
    def __init__(self, config: SystemConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 系统状态
        self.running = False
        self.initialized = False
        self.shutdown_requested = False
        
        # 组件实例
        self.mqtt_client: Optional[MQTTClient] = None
        self.camera_manager: Optional[FastCameraManager] = None
        self.light_detector: Optional[RedLightDetector] = None
        self.trigger_publisher: Optional[TriggerPublisher] = None
        self.visual_monitor: Optional[EnhancedLightweightMonitor] = None
        
        # 线程管理
        self.main_loop_thread: Optional[threading.Thread] = None
        self.monitoring_active = False
        
        # 快速初始化状态
        self.mqtt_connected = False
        self.cameras_initialized = False
        self.active_camera_ids: List[int] = []
        
        # 性能统计
        self.frame_count = 0
        self.last_stats_time = time.time()
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        
        self.logger.info("UltraFastController initialized")
    
    def initialize_system(self) -> bool:
        """超快速系统初始化"""
        try:
            self.logger.info("Initializing Ultra Fast MQTT Camera System")
            
            # 创建视觉监控器
            self.logger.info("Creating visual monitor...")
            self.visual_monitor = EnhancedLightweightMonitor(
                self.config.visual_monitor, 
                self.config.cameras.count
            )
            
            if not self.visual_monitor.create_windows():
                self.logger.error("Failed to create visual monitor")
                return False
            
            self.visual_monitor.add_log_entry("INFO", "🚀 超快速系统启动中...")
            self.visual_monitor.add_log_entry("INFO", "✅ 显示窗口创建完成")
            
            # 快速并行初始化
            self.visual_monitor.add_log_entry("INFO", "⚡ 开始超快速并行初始化...")
            
            # 启动MQTT连接（非阻塞）
            mqtt_thread = threading.Thread(target=self._quick_init_mqtt, daemon=True)
            mqtt_thread.start()
            
            # 启动摄像头初始化（非阻塞）
            self._quick_init_cameras()
            
            # 快速初始化其他组件
            self._quick_init_other_components()
            
            # 等待MQTT连接（最多2秒）
            mqtt_thread.join(timeout=2.0)
            
            self.visual_monitor.add_log_entry("INFO", f"📡 MQTT: {'✅连接' if self.mqtt_connected else '❌失败'}")
            
            self.initialized = True
            self.visual_monitor.add_log_entry("INFO", "🎉 超快速初始化完成！")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ultra fast initialization failed: {e}")
            if self.visual_monitor:
                self.visual_monitor.add_log_entry("ERROR", f"❌ 初始化失败: {e}")
            return False
    
    def _quick_init_mqtt(self) -> None:
        """快速MQTT初始化"""
        try:
            self.visual_monitor.add_log_entry("INFO", "📡 连接MQTT服务器...")
            
            self.mqtt_client = MQTTClient(self.config.mqtt)
            if self.mqtt_client.connect():
                self.mqtt_client.set_message_callback(self._handle_mqtt_message)
                self.mqtt_connected = True
                self.visual_monitor.add_log_entry("INFO", "📡 MQTT连接成功")
            else:
                self.visual_monitor.add_log_entry("WARNING", "📡 MQTT连接失败")
                
        except Exception as e:
            self.logger.error(f"Quick MQTT init failed: {e}")
            self.visual_monitor.add_log_entry("ERROR", f"📡 MQTT错误: {e}")
    
    def _quick_init_cameras(self) -> None:
        """快速摄像头初始化"""
        try:
            self.visual_monitor.add_log_entry("INFO", "📹 启动超快速摄像头初始化...")
            
            # 创建快速摄像头管理器
            self.camera_manager = FastCameraManager(self.config.cameras)
            
            # 设置回调
            self.camera_manager.set_progress_callback(self._on_camera_progress)
            self.camera_manager.set_completion_callback(self._on_camera_completion)
            
            # 开始超快速初始化
            self.camera_manager.initialize_cameras_async()
            
        except Exception as e:
            self.logger.error(f"Quick camera init failed: {e}")
            self.visual_monitor.add_log_entry("ERROR", f"📹 摄像头错误: {e}")
    
    def _on_camera_progress(self, current: int, total: int, status: str) -> None:
        """摄像头进度回调"""
        self.visual_monitor.update_initialization_progress(current, total, status)
    
    def _on_camera_completion(self, active_cameras: List[int]) -> None:
        """摄像头完成回调"""
        self.active_camera_ids = active_cameras
        self.cameras_initialized = True
        
        # 立即启动连续捕获
        if self.camera_manager:
            self.camera_manager.start_continuous_capture()
        
        self.visual_monitor.add_log_entry("INFO", f"📹 摄像头就绪: {len(active_cameras)}个 {active_cameras}")
        self.visual_monitor.add_log_entry("INFO", "🎬 开始连续帧捕获")
    
    def _quick_init_other_components(self) -> None:
        """快速初始化其他组件"""
        try:
            # 快速初始化红光检测器
            self.visual_monitor.add_log_entry("INFO", "🔍 初始化检测器...")
            self.light_detector = RedLightDetector(self.config.red_light_detection)
            
            # 快速初始化触发发布器（如果MQTT可用）
            if self.mqtt_connected:
                self.visual_monitor.add_log_entry("INFO", "📤 初始化发布器...")
                self.trigger_publisher = TriggerPublisher(self.config.mqtt)
                if self.trigger_publisher.connect():
                    self.visual_monitor.add_log_entry("INFO", "📤 发布器就绪")
                else:
                    self.visual_monitor.add_log_entry("WARNING", "📤 发布器失败")
            
        except Exception as e:
            self.logger.error(f"Quick other components init failed: {e}")
            self.visual_monitor.add_log_entry("ERROR", f"🔧 组件错误: {e}")
    
    def start_monitoring(self) -> bool:
        """启动超快速监控"""
        if not self.initialized:
            self.logger.error("System not initialized")
            return False
        
        try:
            self.running = True
            self.monitoring_active = True
            
            # 启动高性能监控线程
            self.main_loop_thread = threading.Thread(target=self._ultra_fast_loop, daemon=True)
            self.main_loop_thread.start()
            
            self.visual_monitor.add_log_entry("INFO", "🚀 超快速监控已启动")
            self.logger.info("Ultra fast monitoring loop started")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start ultra fast monitoring: {e}")
            self.visual_monitor.add_log_entry("ERROR", f"🚀 启动失败: {e}")
            return False
    
    def _ultra_fast_loop(self) -> None:
        """超快速主监控循环"""
        self.logger.info("Starting ultra fast monitoring loop")
        
        last_status_update = time.time()
        last_stats_update = time.time()
        
        try:
            while self.running and not self.shutdown_requested:
                current_time = time.time()
                
                # 高频率帧捕获和显示
                if self.camera_manager and self.camera_manager.is_initialization_complete():
                    frames = self.camera_manager.capture_frames()
                    
                    # 快速更新显示
                    if self.visual_monitor:
                        self.visual_monitor.update_display(frames)
                    
                    # 快速红光检测
                    if self.light_detector and frames:
                        self._fast_light_detection(frames)
                    
                    self.frame_count += 1
                
                # 性能统计（每5秒）
                if current_time - last_stats_update > 5:
                    self._update_performance_stats()
                    last_stats_update = current_time
                
                # 状态更新（每10秒）
                if current_time - last_status_update > 10:
                    active_cameras = len(self.active_camera_ids) if self.cameras_initialized else 0
                    fps = self.frame_count / (current_time - self.last_stats_time) if current_time > self.last_stats_time else 0
                    
                    self.visual_monitor.add_log_entry("INFO", 
                        f"📊 运行状态: {active_cameras}摄像头, {fps:.1f}FPS")
                    
                    last_status_update = current_time
                    self.frame_count = 0
                    self.last_stats_time = current_time
                
                # 高频率循环 - 20 FPS
                time.sleep(0.05)
                
        except Exception as e:
            self.logger.error(f"Error in ultra fast loop: {e}")
            self.visual_monitor.add_log_entry("ERROR", f"🔄 循环错误: {e}")
        finally:
            self.monitoring_active = False
            self.logger.info("Ultra fast monitoring loop ended")
    
    def _update_performance_stats(self) -> None:
        """更新性能统计"""
        try:
            if self.camera_manager:
                stats = self.camera_manager.get_camera_stats()
                unstable_cameras = [cid for cid, stat in stats.items() if stat.get('status') == 'UNSTABLE']
                
                if unstable_cameras:
                    self.visual_monitor.add_log_entry("WARNING", 
                        f"⚠️ 不稳定摄像头: {unstable_cameras}")
                
        except Exception as e:
            self.logger.error(f"Error updating performance stats: {e}")
    
    def _fast_light_detection(self, frames: List[Any]) -> None:
        """快速红光检测"""
        try:
            # 简化的快速检测
            valid_frames = sum(1 for f in frames if f and f.is_valid)
            if valid_frames > 0:
                # 这里可以添加实际的快速检测逻辑
                pass
                
        except Exception as e:
            self.logger.error(f"Error in fast light detection: {e}")
    
    def _handle_mqtt_message(self, topic: str, payload: str) -> None:
        """快速MQTT消息处理"""
        try:
            ones_count = payload.count('1') if payload else 0
            self.logger.info(f"MQTT message: {ones_count} ones")
            
            # 快速日志记录
            self.visual_monitor.add_log_entry("INFO", f"📨 MQTT: {ones_count} ones")
            
            # 快速摄像头激活
            if ones_count > 0:
                if self.camera_manager:
                    self.camera_manager.activate_cameras()
                
                if self.light_detector:
                    self.light_detector.reset_all_baselines()
                    self.light_detector.start_baseline_establishment()
                    
        except Exception as e:
            self.logger.error(f"Error handling MQTT message: {e}")
            self.visual_monitor.add_log_entry("ERROR", f"📨 MQTT错误: {e}")
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.visual_monitor.add_log_entry("INFO", f"🛑 接收到信号 {signum}，正在关闭...")
        self.shutdown_system()
    
    def shutdown_system(self) -> None:
        """快速关闭系统"""
        try:
            self.logger.info("Shutting down Ultra Fast System")
            self.visual_monitor.add_log_entry("INFO", "🛑 正在快速关闭系统...")
            
            self.running = False
            self.shutdown_requested = True
            
            # 快速停止摄像头
            if self.camera_manager:
                self.camera_manager.stop_continuous_capture()
            
            # 等待主循环结束
            if self.main_loop_thread and self.main_loop_thread.is_alive():
                self.main_loop_thread.join(timeout=1.0)
            
            # 快速关闭组件
            if self.visual_monitor:
                self.visual_monitor.add_log_entry("INFO", "🖥️ 关闭显示...")
                time.sleep(0.5)  # 短暂延迟让用户看到消息
                self.visual_monitor.close_windows()
            
            if self.mqtt_client:
                self.mqtt_client.disconnect()
            
            if self.trigger_publisher:
                self.trigger_publisher.disconnect()
            
            if self.camera_manager:
                self.camera_manager.release_cameras()
            
            self.logger.info("Ultra fast system shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during ultra fast shutdown: {e}")
    
    def run(self) -> int:
        """运行超快速系统"""
        try:
            # 超快速初始化
            if not self.initialize_system():
                self.logger.error("Ultra fast initialization failed")
                return 1
            
            # 启动超快速监控
            if not self.start_monitoring():
                self.logger.error("Failed to start ultra fast monitoring")
                return 1
            
            # 保持运行
            try:
                while self.running and not self.shutdown_requested:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received")
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Unexpected error in ultra fast run: {e}")
            return 1
        finally:
            self.shutdown_system()
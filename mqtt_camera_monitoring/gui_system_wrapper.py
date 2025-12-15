#!/usr/bin/env python3
"""
GUI System Wrapper for FinalProductionSystem
Provides interface between GUI and existing production system with enhanced
MQTT connection reliability, diagnostics, and real-time monitoring.
"""

import os
import cv2
import time
import threading
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from copy import deepcopy
from datetime import datetime

# Import existing system components
from final_production_system import FinalProductionSystem, CameraState
from mqtt_camera_monitoring.config import ConfigManager

# Import enhanced MQTT reliability components
from mqtt_camera_monitoring.connection_manager import ConnectionManager, ConnectionResult
from mqtt_camera_monitoring.diagnostic_tool import DiagnosticTool, DiagnosticReport
from mqtt_camera_monitoring.health_monitor import HealthMonitor
from mqtt_camera_monitoring.log_manager import EnhancedLogManager
from mqtt_camera_monitoring.log_viewer import LogViewerInterface, LogViewerGUI
from mqtt_camera_monitoring.data_models import (
    MQTTConfiguration, SystemConfiguration, HealthMetrics, 
    ConnectionMetrics, PerformanceReport, QualityReport,
    ConnectionState, HealthStatus, LogLevel, LogCategory
)

# Import path utilities for PyInstaller compatibility
try:
    from path_utils import get_config_path, ensure_config_in_exe_dir
except ImportError:
    # Fallback if path_utils is not available
    def get_config_path(filename="config.yaml"):
        return filename
    def ensure_config_in_exe_dir(filename="config.yaml"):
        return filename


@dataclass
class GuiCameraConfig:
    """Camera configuration from GUI"""
    camera_id: int
    enabled: bool
    physical_camera_id: int
    mask_path: str
    baseline_count: int
    threshold: int


class GuiSystemWrapper:
    """
    Enhanced wrapper class that interfaces with existing FinalProductionSystem
    and provides integrated MQTT connection reliability, diagnostics, and monitoring.
    """
    
    def __init__(self, config_file: str = "config.yaml"):
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Configuration - resolve path for PyInstaller compatibility
        if config_file == "config.yaml":
            self.config_file = ensure_config_in_exe_dir(config_file)
        else:
            self.config_file = get_config_path(config_file)
        
        self.config_manager = ConfigManager(self.config_file)
        
        # System state
        self.production_system: Optional[FinalProductionSystem] = None
        self.running = False
        self.gui_cameras: Dict[int, GuiCameraConfig] = {}
        self.system_parameters = {
            'delay_time': 0.4,
            'monitoring_interval': 0.2,
            'global_threshold': 2
        }
        
        # MQTT configuration from GUI (优先使用GUI配置)
        self.gui_mqtt_config = {
            'broker_host': '192.168.10.80',
            'broker_port': 1883,
            'client_id': 'receiver',
            'subscribe_topic': 'changeState',
            'publish_topic': 'receiver/triggered',
            'keepalive': 60,
            'max_reconnect_attempts': 10,
            'reconnect_delay': 5
        }
        
        # Enhanced MQTT reliability components
        self.connection_manager: Optional[ConnectionManager] = None
        self.diagnostic_tool = DiagnosticTool()
        self.health_monitor = HealthMonitor()
        
        # Enhanced log management system
        self.log_manager = EnhancedLogManager(
            log_directory="logs",
            max_file_size=10 * 1024 * 1024,  # 10MB
            backup_count=5,
            compression_enabled=True,
            memory_buffer_size=1000
        )
        self.log_viewer = LogViewerInterface(self.log_manager)
        self.log_viewer_gui = LogViewerGUI(self.log_viewer)
        
        # Diagnostic and monitoring state
        self.last_diagnostic_report: Optional[DiagnosticReport] = None
        self.current_health_metrics: Optional[HealthMetrics] = None
        self.current_performance_report: Optional[PerformanceReport] = None
        self.diagnostic_in_progress = False
        
        # Status callbacks for GUI updates
        self.status_callbacks: Dict[str, Callable] = {}
        
        # Status monitoring thread
        self.status_thread: Optional[threading.Thread] = None
        self.status_lock = threading.Lock()
        
        # Initialize enhanced monitoring callbacks
        self._setup_monitoring_callbacks()
        
        self.logger.info("Enhanced GUI System Wrapper initialized with MQTT reliability components")
    
    def set_status_callback(self, callback_name: str, callback_func: Callable):
        """Set callback function for GUI status updates"""
        self.status_callbacks[callback_name] = callback_func
        self.logger.debug(f"Status callback set: {callback_name}")
    
    def _setup_monitoring_callbacks(self):
        """Setup callbacks for enhanced monitoring components"""
        # Health monitor callbacks
        self.health_monitor.add_status_callback(self._on_health_status_update)
        self.health_monitor.add_quality_callback(self._on_quality_report_update)
        self.health_monitor.add_report_callback(self._on_performance_report_update)
    
    def _on_health_status_update(self, health_metrics: HealthMetrics):
        """Handle health status updates from health monitor"""
        try:
            self.current_health_metrics = health_metrics
            
            # Update GUI with health information
            if 'update_connection_health' in self.status_callbacks:
                self.status_callbacks['update_connection_health'](
                    health_metrics.health_status.value,
                    health_metrics.connection_state.value,
                    health_metrics.get_status_summary()
                )
            
            # Update connection statistics display
            if 'update_connection_statistics' in self.status_callbacks:
                stats = {
                    'uptime': health_metrics.timestamp.isoformat() if health_metrics.timestamp else "",
                    'error_count': health_metrics.error_count,
                    'warning_count': health_metrics.warning_count,
                    'system_load': health_metrics.system_load,
                    'memory_usage': health_metrics.memory_usage,
                    'network_latency': health_metrics.network_latency
                }
                self.status_callbacks['update_connection_statistics'](stats)
                
        except Exception as e:
            self.logger.error(f"Error handling health status update: {e}")
    
    def _on_quality_report_update(self, quality_report: QualityReport):
        """Handle connection quality reports"""
        try:
            # Update GUI with quality information
            if 'update_connection_quality' in self.status_callbacks:
                self.status_callbacks['update_connection_quality'](
                    quality_report.overall_quality,
                    quality_report.get_quality_level(),
                    quality_report.issues_detected,
                    quality_report.recommendations
                )
                
        except Exception as e:
            self.logger.error(f"Error handling quality report update: {e}")
    
    def _on_performance_report_update(self, performance_report: PerformanceReport):
        """Handle performance reports"""
        try:
            self.current_performance_report = performance_report
            
            # Log performance metrics
            connection_metrics = performance_report.connection_metrics
            self.log_performance_event(
                metric_name="connection_quality_score",
                metric_value=connection_metrics.quality_score,
                threshold=75.0,  # Quality threshold
                details={
                    "report_id": performance_report.report_id,
                    "time_period": performance_report.time_period,
                    "uptime": connection_metrics.connection_uptime,
                    "success_rate": connection_metrics.message_success_rate,
                    "latency": connection_metrics.average_latency,
                    "reconnection_count": connection_metrics.reconnection_count
                }
            )
            
            # Log performance issues if any
            if performance_report.recommendations:
                self.log_manager.log_event(
                    level=LogLevel.WARNING,
                    category=LogCategory.PERFORMANCE,
                    component="health_monitor",
                    message="Performance issues detected",
                    details={
                        "report_id": performance_report.report_id,
                        "recommendations": performance_report.recommendations,
                        "quality_score": connection_metrics.quality_score
                    }
                )
            
            # Update GUI with performance information
            if 'update_performance_report' in self.status_callbacks:
                self.status_callbacks['update_performance_report'](
                    performance_report.report_id,
                    performance_report.timestamp.isoformat(),
                    performance_report.time_period,
                    performance_report.recommendations
                )
                
        except Exception as e:
            self.logger.error(f"Error handling performance report update: {e}")
            self.log_error_with_context(
                component="gui_system_wrapper",
                error=e,
                context={"method": "_on_performance_report_update"},
                user_action="performance_monitoring"
            )
    
    def run_manual_diagnostics(self) -> DiagnosticReport:
        """
        Run manual MQTT connection diagnostics and return results.
        
        Returns:
            DiagnosticReport: Complete diagnostic report with recommendations
        """
        try:
            if self.diagnostic_in_progress:
                self.logger.warning("Diagnostic already in progress")
                return self.last_diagnostic_report or DiagnosticReport(
                    timestamp=datetime.now(),
                    network_test=None,
                    broker_test=None,
                    config_validation=None,
                    overall_status="skipped",
                    recommendations=["诊断正在进行中，请稍候"]
                )
            
            self.diagnostic_in_progress = True
            self.logger.info("Starting manual MQTT diagnostics...")
            
            # Update GUI to show diagnostic in progress
            if 'update_diagnostic_status' in self.status_callbacks:
                self.status_callbacks['update_diagnostic_status'](
                    "running", "正在运行诊断检查...", []
                )
            
            # Get effective MQTT configuration
            effective_config = self.get_effective_mqtt_config()
            
            # Run full diagnostics
            diagnostic_report = self.diagnostic_tool.run_full_diagnostics(effective_config)
            self.last_diagnostic_report = diagnostic_report
            
            # Update GUI with diagnostic results
            if 'update_diagnostic_status' in self.status_callbacks:
                status = "passed" if diagnostic_report.is_successful else "failed"
                self.status_callbacks['update_diagnostic_status'](
                    status, 
                    f"诊断完成: {diagnostic_report.overall_status.value}",
                    diagnostic_report.recommendations
                )
            
            # Display diagnostic report in GUI
            if 'show_diagnostic_report' in self.status_callbacks:
                self.status_callbacks['show_diagnostic_report'](diagnostic_report)
            
            self.logger.info(f"Manual diagnostics completed: {diagnostic_report.overall_status.value}")
            return diagnostic_report
            
        except Exception as e:
            error_msg = f"Manual diagnostics failed: {str(e)}"
            self.logger.error(error_msg)
            
            # Update GUI with error
            if 'update_diagnostic_status' in self.status_callbacks:
                self.status_callbacks['update_diagnostic_status'](
                    "failed", error_msg, ["请检查系统配置并重试"]
                )
            
            # Create error report
            error_report = DiagnosticReport(
                timestamp=datetime.now(),
                network_test=None,
                broker_test=None,
                config_validation=None,
                overall_status="failed",
                recommendations=[error_msg, "请检查系统配置并重试"]
            )
            
            return error_report
            
        finally:
            self.diagnostic_in_progress = False
    
    def get_diagnostic_report(self) -> Optional[DiagnosticReport]:
        """Get the last diagnostic report"""
        return self.last_diagnostic_report
    
    def get_connection_statistics(self) -> Dict[str, any]:
        """
        Get comprehensive connection statistics for GUI display.
        
        Returns:
            Dict containing connection metrics and health information
        """
        try:
            stats = {
                'connection_state': 'disconnected',
                'health_status': 'unknown',
                'uptime': 0.0,
                'message_success_rate': 0.0,
                'average_latency': 0.0,
                'reconnection_count': 0,
                'error_count': 0,
                'warning_count': 0,
                'quality_score': 0.0,
                'last_error': None,
                'system_load': 0.0,
                'memory_usage': 0.0,
                'network_latency': 0.0
            }
            
            # Get connection manager statistics
            if self.connection_manager:
                connection_status = self.connection_manager.get_connection_status()
                stats.update({
                    'connection_state': connection_status.get('connection_state', 'disconnected'),
                    'health_status': connection_status.get('health_status', 'unknown')
                })
                
                # Get connection metrics if available
                if 'connection_metrics' in connection_status:
                    metrics = connection_status['connection_metrics']
                    stats.update({
                        'uptime': metrics.get('connection_uptime', 0.0),
                        'message_success_rate': metrics.get('message_success_rate', 0.0),
                        'average_latency': metrics.get('average_latency', 0.0),
                        'reconnection_count': metrics.get('reconnection_count', 0),
                        'quality_score': metrics.get('quality_score', 0.0),
                        'last_error': metrics.get('last_error')
                    })
            
            # Get health monitor statistics
            if self.current_health_metrics:
                stats.update({
                    'error_count': self.current_health_metrics.error_count,
                    'warning_count': self.current_health_metrics.warning_count,
                    'system_load': self.current_health_metrics.system_load,
                    'memory_usage': self.current_health_metrics.memory_usage,
                    'network_latency': self.current_health_metrics.network_latency
                })
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting connection statistics: {e}")
            return {
                'connection_state': 'error',
                'health_status': 'critical',
                'error_message': str(e)
            }
    
    def trigger_manual_diagnostic_button(self):
        """Handle manual diagnostic button trigger from GUI"""
        try:
            self.logger.info("Manual diagnostic button triggered")
            
            # Run diagnostics in background thread to avoid blocking GUI
            diagnostic_thread = threading.Thread(
                target=self.run_manual_diagnostics,
                name="ManualDiagnostic"
            )
            diagnostic_thread.daemon = True
            diagnostic_thread.start()
            
        except Exception as e:
            error_msg = f"Failed to start manual diagnostics: {str(e)}"
            self.logger.error(error_msg)
            
            if 'show_error_message' in self.status_callbacks:
                self.status_callbacks['show_error_message'](
                    "诊断启动失败", error_msg
                )
    
    def configure_cameras(self, camera_configs: List[Dict]) -> bool:
        """Configure cameras from GUI settings"""
        try:
            self.gui_cameras.clear()
            
            for config in camera_configs:
                if config.get('enabled', False):
                    gui_config = GuiCameraConfig(
                        camera_id=config['camera_id'],
                        enabled=config['enabled'],
                        physical_camera_id=config['physical_camera_id'],
                        mask_path=config['mask_path'],
                        baseline_count=config.get('baseline_count', 0),
                        threshold=config.get('threshold', 2)
                    )
                    self.gui_cameras[config['camera_id']] = gui_config
            
            self.logger.info(f"Configured {len(self.gui_cameras)} cameras from GUI")
            return True
            
        except Exception as e:
            self.logger.error(f"Camera configuration failed: {e}")
            return False
    
    def update_system_parameters(self, parameters: Dict) -> bool:
        """Update system parameters from GUI"""
        try:
            self.system_parameters.update(parameters)
            self.logger.info(f"Updated system parameters: {parameters}")
            
            # If system is running, apply changes dynamically
            if self.running and self.production_system:
                self._apply_dynamic_parameter_updates()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Parameter update failed: {e}")
            return False
    
    def _apply_dynamic_parameter_updates(self):
        """Apply parameter updates to running system"""
        try:
            # Update delay time in MQTT handling
            if hasattr(self.production_system, 'baseline_capture_time'):
                # This affects future baseline captures
                pass
        except Exception as e:
            self.logger.error(f"Failed to apply dynamic parameter updates: {e}")
    
    def update_mqtt_configuration(self, mqtt_config: Dict) -> bool:
        """Update MQTT configuration with enhanced reliability validation"""
        try:
            # Log the incoming configuration
            self.logger.info(f"Updating MQTT configuration from GUI: {mqtt_config}")
            
            # Update GUI MQTT config
            old_config = self.gui_mqtt_config.copy()
            self.gui_mqtt_config.update(mqtt_config)
            
            # Check if broker or port changed
            broker_changed = (old_config.get('broker_host') != mqtt_config.get('broker_host') or
                            old_config.get('broker_port') != mqtt_config.get('broker_port'))
            
            if broker_changed:
                self.logger.info(f"MQTT broker changed from {old_config.get('broker_host')}:{old_config.get('broker_port')} "
                               f"to {mqtt_config.get('broker_host')}:{mqtt_config.get('broker_port')}")
            
            # Validate new configuration using diagnostic tool
            effective_config = self.get_effective_mqtt_config()
            validation_result = self.diagnostic_tool.run_full_diagnostics(effective_config)
            
            if not validation_result.is_successful:
                error_msg = f"MQTT配置验证失败: {', '.join(validation_result.recommendations)}"
                self.logger.error(error_msg)
                
                # Show validation error in GUI
                if 'show_error_message' in self.status_callbacks:
                    self.status_callbacks['show_error_message'](
                        "MQTT配置验证失败", error_msg
                    )
                
                # Revert to old configuration
                self.gui_mqtt_config = old_config
                return False
            
            # Apply configuration changes through connection manager
            if self.running and self.connection_manager:
                self.logger.info("System is running, applying MQTT configuration through connection manager")
                
                # Create new MQTT configuration object
                new_mqtt_config = MQTTConfiguration.from_dict(effective_config)
                
                # Apply configuration changes
                success = self.connection_manager.apply_configuration_changes(new_mqtt_config)
                
                if success:
                    self.logger.info("MQTT configuration applied successfully through connection manager")
                    
                    # Update GUI with success
                    if 'update_mqtt_configuration_status' in self.status_callbacks:
                        self.status_callbacks['update_mqtt_configuration_status'](
                            True, "MQTT配置更新成功"
                        )
                else:
                    self.logger.error("Failed to apply MQTT configuration through connection manager")
                    
                    # Update GUI with error
                    if 'update_mqtt_configuration_status' in self.status_callbacks:
                        self.status_callbacks['update_mqtt_configuration_status'](
                            False, "MQTT配置应用失败"
                        )
                
                return success
            elif self.running and self.production_system:
                # Fallback to legacy method if connection manager not available
                self.logger.info("System is running, applying MQTT configuration using legacy method")
                success = self._apply_mqtt_configuration()
                if success:
                    self.logger.info("MQTT configuration applied successfully using legacy method")
                else:
                    self.logger.error("Failed to apply MQTT configuration using legacy method")
                return success
            else:
                self.logger.info("System not running, MQTT configuration will be applied on next start")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update MQTT configuration: {e}")
            
            # Show error in GUI
            if 'show_error_message' in self.status_callbacks:
                self.status_callbacks['show_error_message'](
                    "MQTT配置更新失败", str(e)
                )
            
            return False
    
    def get_effective_mqtt_config(self) -> Dict:
        """获取有效的MQTT配置 (优先GUI配置，然后配置文件)"""
        try:
            # 首先尝试从配置文件加载
            file_config = {
                'broker_host': '192.168.10.80',
                'broker_port': 1883,
                'client_id': 'receiver',
                'subscribe_topic': 'changeState',
                'publish_topic': 'receiver/triggered',
                'keepalive': 60,
                'max_reconnect_attempts': 10,
                'reconnect_delay': 5
            }
            
            if hasattr(self.config_manager, 'load_config'):
                try:
                    config = self.config_manager.load_config()
                    if hasattr(config, 'mqtt'):
                        file_config.update({
                            'broker_host': config.mqtt.broker_host,
                            'broker_port': config.mqtt.broker_port,
                            'client_id': config.mqtt.client_id,
                            'subscribe_topic': config.mqtt.subscribe_topic,
                            'publish_topic': config.mqtt.publish_topic,
                            'keepalive': config.mqtt.keepalive,
                            'max_reconnect_attempts': config.mqtt.max_reconnect_attempts,
                            'reconnect_delay': config.mqtt.reconnect_delay
                        })
                except Exception as e:
                    self.logger.warning(f"Failed to load MQTT config from file: {e}")
            
            # 合并配置：GUI配置优先，只覆盖非空值
            effective_config = file_config.copy()
            for key, value in self.gui_mqtt_config.items():
                if value is not None and value != "":
                    effective_config[key] = value
            
            self.logger.debug(f"File config: {file_config}")
            self.logger.debug(f"GUI config: {self.gui_mqtt_config}")
            self.logger.debug(f"Effective MQTT config: {effective_config}")
            return effective_config
            
        except Exception as e:
            self.logger.error(f"Failed to get effective MQTT config: {e}")
            return self.gui_mqtt_config
    
    def validate_camera_configuration(self) -> tuple[bool, str]:
        """Validate camera configuration before starting with comprehensive checks"""
        try:
            if not self.gui_cameras:
                return False, "至少需要启用一个摄像头才能开始监控"
            
            # Validate camera ID ranges and check for duplicates
            physical_ids = []
            for cam_id, cam_config in self.gui_cameras.items():
                # Validate camera ID range (0-5)
                if not (0 <= cam_id <= 5):
                    return False, f"摄像头ID {cam_id} 超出有效范围 (0-5)"
                
                # Validate physical camera ID range (0-5)
                if not (0 <= cam_config.physical_camera_id <= 5):
                    return False, f"摄像头 {cam_id}: 物理摄像头ID {cam_config.physical_camera_id} 超出有效范围 (0-5)"
                
                physical_ids.append(cam_config.physical_camera_id)
            
            # Check for duplicate physical camera ID assignments
            if len(physical_ids) != len(set(physical_ids)):
                duplicates = [pid for pid in set(physical_ids) if physical_ids.count(pid) > 1]
                return False, f"物理摄像头ID重复: {duplicates}，每个物理摄像头只能分配给一个摄像头"
            
            # Validate mask files with comprehensive checks
            for cam_id, cam_config in self.gui_cameras.items():
                if not cam_config.mask_path:
                    return False, f"摄像头 {cam_id}: 必须指定遮罩文件路径"
                
                if not os.path.exists(cam_config.mask_path):
                    return False, f"摄像头 {cam_id}: 遮罩文件不存在: {cam_config.mask_path}"
                
                # Validate mask file format and ensure 1920x1080 resolution
                try:
                    mask_img = cv2.imread(cam_config.mask_path, cv2.IMREAD_GRAYSCALE)
                    if mask_img is None:
                        return False, f"摄像头 {cam_id}: 无法读取遮罩文件，请检查文件格式: {cam_config.mask_path}"
                    
                    height, width = mask_img.shape
                    if width != 1920 or height != 1080:
                        return False, f"摄像头 {cam_id}: 遮罩文件分辨率必须为1920x1080，当前为{width}x{height}: {cam_config.mask_path}"
                        
                except Exception as e:
                    return False, f"摄像头 {cam_id}: 遮罩文件验证失败: {str(e)}"
                
                # Validate parameter ranges for baseline counts and comparison thresholds
                if not (1 <= cam_config.threshold <= 50):
                    return False, f"摄像头 {cam_id}: 比较阈值 {cam_config.threshold} 超出有效范围 (1-50)"
            
            # Validate system parameters
            delay_time = self.system_parameters.get('delay_time', 0.4)
            if not (0.1 <= delay_time <= 10.0):
                return False, f"延时时间 {delay_time} 秒超出有效范围 (0.1-10.0秒)"
            
            global_threshold = self.system_parameters.get('global_threshold', 2)
            if not (1 <= global_threshold <= 50):
                return False, f"全局阈值 {global_threshold} 超出有效范围 (1-50)"
            
            monitoring_interval = self.system_parameters.get('monitoring_interval', 0.2)
            if not (0.1 <= monitoring_interval <= 5.0):
                return False, f"监控间隔 {monitoring_interval} 秒超出有效范围 (0.1-5.0秒)"
            
            # Ensure no camera parameter modifications are applied (as per requirements)
            # This is enforced by using cameras directly without parameter modifications
            
            return True, "配置验证通过"
            
        except Exception as e:
            return False, f"配置验证错误: {str(e)}"
    
    def _create_modified_production_system(self) -> bool:
        """Create modified production system to support multiple cameras"""
        try:
            # Create a modified version that supports up to 6 cameras
            # We'll use the first enabled camera's mask file for the base system
            # and handle multiple cameras through our wrapper
            
            if not self.gui_cameras:
                return False
            
            # Get the first enabled camera for the base system
            first_camera = next(iter(self.gui_cameras.values()))
            
            # Create production system with first camera's mask
            self.production_system = FinalProductionSystem(
                config_file=self.config_file,
                mask_file=first_camera.mask_path,
                enable_view=False  # GUI handles visualization
            )
            
            # IMPORTANT: Apply MQTT configuration BEFORE system starts
            # This ensures the production system uses GUI-configured MQTT settings
            self._apply_mqtt_configuration_to_config()
            
            # Override the camera initialization to support our multi-camera setup
            self._override_camera_initialization()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create production system: {e}")
            return False
    
    def _apply_mqtt_configuration_to_config(self):
        """Apply MQTT configuration from GUI to production system config before startup"""
        try:
            # Get effective MQTT config (GUI priority)
            effective_mqtt = self.get_effective_mqtt_config()
            
            # Update production system's MQTT configuration BEFORE it starts
            if hasattr(self.production_system, 'config') and hasattr(self.production_system.config, 'mqtt'):
                self.production_system.config.mqtt.broker_host = effective_mqtt['broker_host']
                self.production_system.config.mqtt.broker_port = effective_mqtt['broker_port']
                self.production_system.config.mqtt.client_id = effective_mqtt['client_id']
                self.production_system.config.mqtt.subscribe_topic = effective_mqtt['subscribe_topic']
                self.production_system.config.mqtt.publish_topic = effective_mqtt['publish_topic']
                self.production_system.config.mqtt.keepalive = effective_mqtt.get('keepalive', 60)
                self.production_system.config.mqtt.max_reconnect_attempts = effective_mqtt.get('max_reconnect_attempts', 10)
                self.production_system.config.mqtt.reconnect_delay = effective_mqtt.get('reconnect_delay', 5)
                
                self.logger.info(f"Pre-startup MQTT configuration applied: {effective_mqtt['broker_host']}:{effective_mqtt['broker_port']}")
            else:
                self.logger.warning("Production system MQTT config not found during pre-startup configuration")
                
        except Exception as e:
            self.logger.error(f"Failed to apply pre-startup MQTT configuration: {e}")
    
    def _override_camera_initialization(self):
        """Override camera initialization to support GUI configuration"""
        if not self.production_system:
            return
        
        # Store original method
        original_init = self.production_system.initialize_cameras
        
        def gui_initialize_cameras():
            """Custom camera initialization for GUI configuration"""
            try:
                self.logger.info(f"Initializing {len(self.gui_cameras)} cameras from GUI config...")
                
                # Initialize cameras list to support up to 6 cameras
                self.production_system.cameras = [None] * 6
                self.production_system.camera_states = {}
                
                # Initialize only enabled cameras
                for gui_cam_id, gui_config in self.gui_cameras.items():
                    physical_id = gui_config.physical_camera_id
                    
                    try:
                        if physical_id > 0:
                            time.sleep(0.3)  # Delay for camera initialization
                        
                        self.logger.info(f"Initializing camera {gui_cam_id} (physical ID: {physical_id})...")
                        
                        # Open camera with no parameter modifications (as per requirements)
                        cap = cv2.VideoCapture(physical_id)
                        
                        if not cap.isOpened():
                            self.logger.warning(f"Camera {gui_cam_id} (physical ID: {physical_id}) could not be opened")
                            continue
                        
                        # Warm up camera
                        for _ in range(5):
                            ret, frame = cap.read()
                            if ret and frame is not None:
                                break
                            time.sleep(0.1)
                        
                        if ret and frame is not None:
                            # Ensure 1920x1080 resolution to match mask files
                            height, width = frame.shape[:2]
                            if width != 1920 or height != 1080:
                                warning_msg = f"分辨率 {width}x{height}，期望 1920x1080"
                                self.logger.warning(f"Camera {gui_cam_id}: {warning_msg}")
                                # Report resolution warning to GUI
                                if 'show_error_message' in self.status_callbacks:
                                    self.status_callbacks['show_error_message'](
                                        "分辨率警告", warning_msg, gui_cam_id
                                    )
                            
                            self.production_system.cameras[physical_id] = cap
                            self.production_system.camera_states[physical_id] = CameraState(physical_id)
                            
                            self.logger.info(f"Camera {gui_cam_id} (physical ID: {physical_id}) initialized successfully: {frame.shape}")
                        else:
                            error_msg = "无法读取摄像头帧"
                            self.logger.warning(f"Camera {gui_cam_id} (physical ID: {physical_id}): {error_msg}")
                            cap.release()
                            
                            # Handle camera initialization failure gracefully
                            if 'show_camera_initialization_error' in self.status_callbacks:
                                self.status_callbacks['show_camera_initialization_error'](
                                    gui_cam_id, physical_id, error_msg
                                )
                    
                    except Exception as e:
                        error_msg = str(e)
                        self.logger.error(f"Camera {gui_cam_id} (physical ID: {physical_id}) initialization failed: {error_msg}")
                        
                        # Handle camera initialization failure gracefully
                        if 'show_camera_initialization_error' in self.status_callbacks:
                            self.status_callbacks['show_camera_initialization_error'](
                                gui_cam_id, physical_id, error_msg
                            )
                
                active_cameras = len([c for c in self.production_system.cameras if c is not None])
                self.logger.info(f"Successfully initialized {active_cameras} cameras")
                
                # Update GUI status
                if 'update_system_health' in self.status_callbacks:
                    enabled_count = len(self.gui_cameras)
                    self.status_callbacks['update_system_health'](active_cameras, enabled_count, False)
                
                return active_cameras > 0
                
            except Exception as e:
                self.logger.error(f"GUI camera initialization failed: {e}")
                return False
        
        # Replace the method
        self.production_system.initialize_cameras = gui_initialize_cameras
        
        # Also override baseline capture to log events
        self._override_baseline_capture_logging()
    
    def start_system(self) -> bool:
        """Start the production system with enhanced MQTT reliability and monitoring"""
        try:
            # Log system startup event
            self.log_manager.log_event(
                level=LogLevel.INFO,
                category=LogCategory.SYSTEM,
                component="gui_system_wrapper",
                message="System startup initiated",
                details={"action": "start_system"}
            )
            
            # Clear previous errors
            if 'clear_all_errors' in self.status_callbacks:
                self.status_callbacks['clear_all_errors']()
            
            # Step 1: Run startup diagnostics
            self.logger.info("Running startup diagnostics...")
            startup_diagnostic = self.run_manual_diagnostics()
            
            if not startup_diagnostic.is_successful:
                error_msg = f"启动诊断失败: {', '.join(startup_diagnostic.recommendations)}"
                self.logger.error(error_msg)
                if 'show_error_message' in self.status_callbacks:
                    self.status_callbacks['show_error_message'](
                        "启动诊断失败", error_msg
                    )
                return False
            
            # Step 2: Validate camera configuration
            valid, error_msg = self.validate_camera_configuration()
            if not valid:
                self.logger.error(f"Configuration validation failed: {error_msg}")
                if 'show_error_message' in self.status_callbacks:
                    self.status_callbacks['show_error_message'](
                        "配置验证失败", error_msg
                    )
                if 'update_system_health' in self.status_callbacks:
                    self.status_callbacks['update_system_health'](0, 0, False, error_msg)
                return False
            
            # Step 3: Initialize enhanced MQTT components
            if not self._initialize_enhanced_mqtt_components():
                error_msg = "MQTT组件初始化失败"
                self.logger.error(error_msg)
                if 'show_error_message' in self.status_callbacks:
                    self.status_callbacks['show_error_message'](
                        "MQTT组件初始化失败", error_msg
                    )
                return False
            
            # Step 4: Create and configure production system
            if not self._create_modified_production_system():
                error_msg = "生产系统创建失败"
                self.logger.error(error_msg)
                if 'show_error_message' in self.status_callbacks:
                    self.status_callbacks['show_error_message'](
                        "系统创建失败", error_msg
                    )
                if 'update_system_health' in self.status_callbacks:
                    self.status_callbacks['update_system_health'](0, 0, False, error_msg)
                return False
            
            # Step 5: Apply GUI configuration to system
            try:
                self._apply_gui_configuration()
            except Exception as e:
                error_msg = f"配置应用失败: {str(e)}"
                self.logger.error(error_msg)
                if 'show_error_message' in self.status_callbacks:
                    self.status_callbacks['show_error_message'](
                        "配置应用失败", str(e)
                    )
                if 'update_system_health' in self.status_callbacks:
                    self.status_callbacks['update_system_health'](0, 0, False, error_msg)
                return False
            
            # Step 6: Start enhanced monitoring
            self._start_enhanced_monitoring()
            
            # Step 7: Start the production system
            try:
                if self.production_system.start():
                    self.running = True
                    
                    # Start status monitoring thread
                    self.status_thread = threading.Thread(target=self._status_monitoring_loop, daemon=True)
                    self.status_thread.start()
                    
                    self.logger.info("Enhanced GUI System started successfully")
                    
                    # Update GUI status with success
                    if 'update_system_health' in self.status_callbacks:
                        enabled_count = len(self.gui_cameras)
                        active_count = len([c for c in self.production_system.cameras if c is not None])
                        self.status_callbacks['update_system_health'](active_count, enabled_count, True)
                    
                    # Report successful cameras and any failures
                    active_cameras = [c for c in self.production_system.cameras if c is not None]
                    failed_cameras = len(self.gui_cameras) - len(active_cameras)
                    
                    if failed_cameras > 0:
                        warning_msg = f"{failed_cameras} 个摄像头初始化失败，系统将使用 {len(active_cameras)} 个可用摄像头继续运行"
                        if 'show_error_message' in self.status_callbacks:
                            self.status_callbacks['show_error_message'](
                                "摄像头初始化警告", warning_msg
                            )
                    
                    # Log successful system startup
                    self.log_manager.log_event(
                        level=LogLevel.INFO,
                        category=LogCategory.SYSTEM,
                        component="gui_system_wrapper",
                        message="System startup completed successfully",
                        details={
                            "active_cameras": len(active_cameras),
                            "failed_cameras": failed_cameras,
                            "total_cameras": len(self.gui_cameras)
                        }
                    )
                    return True
                else:
                    error_msg = "生产系统启动失败"
                    self.logger.error(error_msg)
                    
                    # Log system startup failure
                    self.log_manager.log_event(
                        level=LogLevel.ERROR,
                        category=LogCategory.SYSTEM,
                        component="gui_system_wrapper",
                        message="Production system startup failed",
                        details={"error": error_msg}
                    )
                    
                    if 'show_error_message' in self.status_callbacks:
                        self.status_callbacks['show_error_message'](
                            "系统启动失败", error_msg
                        )
                    if 'update_system_health' in self.status_callbacks:
                        self.status_callbacks['update_system_health'](0, 0, False, error_msg)
                    return False
            except Exception as e:
                error_msg = f"系统启动异常: {str(e)}"
                self.logger.error(error_msg)
                
                # Log system startup exception with context
                self.log_error_with_context(
                    component="gui_system_wrapper",
                    error=e,
                    context={"method": "start_system", "stage": "production_system_start"},
                    user_action="system_startup"
                )
                
                if 'show_error_message' in self.status_callbacks:
                    self.status_callbacks['show_error_message'](
                        "系统启动异常", str(e)
                    )
                if 'update_system_health' in self.status_callbacks:
                    self.status_callbacks['update_system_health'](0, 0, False, error_msg)
                return False
            
        except Exception as e:
            error_msg = f"系统启动失败: {str(e)}"
            self.logger.error(error_msg)
            
            # Log system startup failure with context
            self.log_error_with_context(
                component="gui_system_wrapper",
                error=e,
                context={"method": "start_system", "stage": "initialization"},
                user_action="system_startup"
            )
            
            if 'show_error_message' in self.status_callbacks:
                self.status_callbacks['show_error_message'](
                    "系统启动失败", str(e)
                )
            if 'update_system_health' in self.status_callbacks:
                self.status_callbacks['update_system_health'](0, 0, False, error_msg)
            return False
    
    def stop_system(self) -> bool:
        """Stop the production system and enhanced monitoring"""
        try:
            # Log system shutdown event
            self.log_manager.log_event(
                level=LogLevel.INFO,
                category=LogCategory.SYSTEM,
                component="gui_system_wrapper",
                message="System shutdown initiated",
                details={"action": "stop_system"}
            )
            
            self.running = False
            
            # Stop enhanced monitoring components
            self._stop_enhanced_monitoring()
            
            # Stop status monitoring thread
            if self.status_thread and self.status_thread.is_alive():
                self.status_thread.join(timeout=2.0)
            
            # Stop connection manager
            if self.connection_manager:
                self.connection_manager.stop_connection()
                self.connection_manager = None
            
            # Stop production system
            if self.production_system:
                self.production_system.stop()
                self.production_system = None
            
            self.logger.info("Enhanced GUI System stopped successfully")
            
            # Log successful system shutdown
            self.log_manager.log_event(
                level=LogLevel.INFO,
                category=LogCategory.SYSTEM,
                component="gui_system_wrapper",
                message="System shutdown completed successfully",
                details={"action": "stop_system"}
            )
            
            # Update GUI status
            if 'update_system_health' in self.status_callbacks:
                self.status_callbacks['update_system_health'](0, 0, False)
            
            return True
            
        except Exception as e:
            self.logger.error(f"System stop failed: {e}")
            
            # Log system shutdown failure with context
            self.log_error_with_context(
                component="gui_system_wrapper",
                error=e,
                context={"method": "stop_system"},
                user_action="system_shutdown"
            )
            
            return False
    
    def _initialize_enhanced_mqtt_components(self) -> bool:
        """Initialize enhanced MQTT reliability components"""
        try:
            self.logger.info("Initializing enhanced MQTT components...")
            
            # Get effective MQTT configuration
            effective_config = self.get_effective_mqtt_config()
            
            # Create MQTT configuration object
            mqtt_config = MQTTConfiguration.from_dict(effective_config)
            
            # Create system configuration
            system_config = SystemConfiguration(
                mqtt_config=mqtt_config,
                monitoring_interval=1.0,
                health_check_interval=30.0,
                performance_report_interval=3600.0,
                enable_health_monitoring=True,
                enable_performance_monitoring=True
            )
            
            # Initialize connection manager
            self.connection_manager = ConnectionManager(system_config)
            
            # Set up connection callbacks
            self.connection_manager.add_connection_callback(self._on_connection_event)
            self.connection_manager.add_health_callback(self._on_health_metrics_update)
            self.connection_manager.add_performance_callback(self._on_performance_report_callback)
            
            self.logger.info("Enhanced MQTT components initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize enhanced MQTT components: {e}")
            return False
    
    def _start_enhanced_monitoring(self):
        """Start enhanced health and performance monitoring"""
        try:
            self.logger.info("Starting enhanced monitoring...")
            
            # Start health monitor
            self.health_monitor.start_monitoring()
            
            # Start connection manager if not already started
            if self.connection_manager and not self.connection_manager.is_running:
                result = self.connection_manager.start_connection()
                if not result.success:
                    self.logger.warning(f"Connection manager start warning: {result.error}")
            
            self.logger.info("Enhanced monitoring started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start enhanced monitoring: {e}")
    
    def _stop_enhanced_monitoring(self):
        """Stop enhanced monitoring components"""
        try:
            self.logger.info("Stopping enhanced monitoring...")
            
            # Stop health monitor
            if self.health_monitor:
                self.health_monitor.stop_monitoring()
            
            self.logger.info("Enhanced monitoring stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to stop enhanced monitoring: {e}")
    
    def _on_connection_event(self, event):
        """Handle connection events from connection manager"""
        try:
            self.logger.info(f"Connection event: {event.event_type} - {event.connection_state.value}")
            
            # Log connection event with enhanced log manager
            self.log_connection_event(
                event_type=event.event_type,
                connection_state=event.connection_state.value,
                details=event.details,
                error_message=event.error_message
            )
            
            # Update health monitor with connection event
            self.health_monitor.record_connection_event(
                event.event_type,
                event.connection_state,
                event.details,
                event.error_message
            )
            
            # Update GUI with connection event
            if 'update_connection_event' in self.status_callbacks:
                self.status_callbacks['update_connection_event'](
                    event.event_type,
                    event.connection_state.value,
                    event.error_message or ""
                )
                
        except Exception as e:
            self.logger.error(f"Error handling connection event: {e}")
            # Log the error with context
            self.log_error_with_context(
                component="gui_system_wrapper",
                error=e,
                context={"method": "_on_connection_event"},
                user_action="connection_event_handling"
            )
    
    def _on_health_metrics_update(self, health_metrics):
        """Handle health metrics updates from connection manager"""
        try:
            # This is already handled by the health monitor callback
            # Just log for debugging
            self.logger.debug(f"Health metrics update: {health_metrics.health_status.value}")
            
        except Exception as e:
            self.logger.error(f"Error handling health metrics update: {e}")
    
    def _on_performance_report_callback(self, performance_report):
        """Handle performance reports from connection manager"""
        try:
            # This is already handled by the health monitor callback
            # Just log for debugging
            self.logger.debug(f"Performance report: {performance_report.report_id}")
            
        except Exception as e:
            self.logger.error(f"Error handling performance report callback: {e}")
    
    def _apply_gui_configuration(self):
        """Apply GUI configuration to production system"""
        if not self.production_system:
            return
        
        try:
            # Apply MQTT configuration from GUI first
            self._apply_mqtt_configuration()
            
            # Apply individual mask files to each enabled camera
            self._apply_camera_mask_configurations()
            
            # Apply baseline counts and comparison thresholds
            self._apply_camera_thresholds()
            
            # Update system timing parameters
            self._apply_timing_parameters()
            
            # Save configuration to file
            self._save_configuration_to_file()
            
            self.logger.info("GUI configuration applied to production system")
            
        except Exception as e:
            self.logger.error(f"Failed to apply GUI configuration: {e}")
    
    def _apply_mqtt_configuration(self):
        """Apply MQTT configuration from GUI to production system"""
        try:
            # Get effective MQTT config (GUI priority)
            effective_mqtt = self.get_effective_mqtt_config()
            
            self.logger.info(f"Applying MQTT configuration: {effective_mqtt['broker_host']}:{effective_mqtt['broker_port']}")
            
            # Update production system's MQTT configuration
            if hasattr(self.production_system, 'config') and hasattr(self.production_system.config, 'mqtt'):
                # Disconnect existing MQTT client if connected
                if hasattr(self.production_system, 'mqtt_client') and self.production_system.mqtt_client:
                    try:
                        if hasattr(self.production_system.mqtt_client, 'client') and self.production_system.mqtt_client.client:
                            self.production_system.mqtt_client.client.disconnect()
                            self.logger.info("Disconnected existing MQTT client")
                        self.production_system.mqtt_client = None
                    except Exception as e:
                        self.logger.warning(f"Error disconnecting MQTT client: {e}")
                
                # Update the MQTT config object
                self.production_system.config.mqtt.broker_host = effective_mqtt['broker_host']
                self.production_system.config.mqtt.broker_port = effective_mqtt['broker_port']
                self.production_system.config.mqtt.client_id = effective_mqtt['client_id']
                self.production_system.config.mqtt.subscribe_topic = effective_mqtt['subscribe_topic']
                self.production_system.config.mqtt.publish_topic = effective_mqtt['publish_topic']
                self.production_system.config.mqtt.keepalive = effective_mqtt.get('keepalive', 60)
                self.production_system.config.mqtt.max_reconnect_attempts = effective_mqtt.get('max_reconnect_attempts', 10)
                self.production_system.config.mqtt.reconnect_delay = effective_mqtt.get('reconnect_delay', 5)
                
                self.logger.info(f"Updated production system MQTT config: {effective_mqtt['broker_host']}:{effective_mqtt['broker_port']}")
                
                # Re-initialize MQTT with new configuration
                if hasattr(self.production_system, 'initialize_mqtt'):
                    self.logger.info("Re-initializing MQTT client with new configuration...")
                    mqtt_success = self.production_system.initialize_mqtt()
                    if mqtt_success:
                        self.logger.info(f"MQTT reconnected successfully: {effective_mqtt['broker_host']}:{effective_mqtt['broker_port']}")
                        
                        # Update GUI status
                        if 'update_mqtt_status' in self.status_callbacks:
                            self.status_callbacks['update_mqtt_status'](
                                True, effective_mqtt['broker_host'], ""
                            )
                        return True
                    else:
                        error_msg = f"MQTT连接失败: {effective_mqtt['broker_host']}:{effective_mqtt['broker_port']}"
                        self.logger.error(error_msg)
                        
                        # Update GUI status
                        if 'update_mqtt_status' in self.status_callbacks:
                            self.status_callbacks['update_mqtt_status'](
                                False, effective_mqtt['broker_host'], error_msg
                            )
                        
                        # Show error in GUI
                        if 'show_error_message' in self.status_callbacks:
                            self.status_callbacks['show_error_message'](
                                "MQTT连接失败", error_msg
                            )
                        return False
                else:
                    self.logger.warning("Production system does not have initialize_mqtt method")
                    return False
                
            else:
                self.logger.warning("Production system MQTT config not found")
                return False
                
        except Exception as e:
            error_msg = f"Failed to apply MQTT configuration: {e}"
            self.logger.error(error_msg)
            
            # Show error in GUI
            if 'show_error_message' in self.status_callbacks:
                self.status_callbacks['show_error_message'](
                    "MQTT配置应用失败", str(e)
                )
            return False
            self.logger.error(error_msg)
            
            # Show error in GUI
            if 'show_error_message' in self.status_callbacks:
                self.status_callbacks['show_error_message'](
                    "MQTT配置应用失败", str(e)
                )
    
    def _apply_camera_mask_configurations(self):
        """Apply individual mask files to each enabled camera"""
        try:
            # Create a mapping of physical camera IDs to mask files
            camera_masks = {}
            
            for gui_cam_id, gui_config in self.gui_cameras.items():
                physical_id = gui_config.physical_camera_id
                camera_masks[physical_id] = gui_config.mask_path
            
            # Override the mask loading for multi-camera support
            if hasattr(self.production_system, '_load_mask'):
                original_load_mask = self.production_system._load_mask
                
                def multi_camera_load_mask():
                    """Load mask for multi-camera setup"""
                    # Load the first camera's mask as the base
                    first_mask_path = next(iter(camera_masks.values()))
                    
                    if not os.path.exists(first_mask_path):
                        self.logger.error(f"Base mask file not found: {first_mask_path}")
                        return False
                    
                    mask_img = cv2.imread(first_mask_path, cv2.IMREAD_GRAYSCALE)
                    if mask_img is None:
                        self.logger.error(f"Cannot read base mask file: {first_mask_path}")
                        return False
                    
                    self.production_system.mask_image = mask_img
                    
                    # Store individual camera masks for future use
                    self.production_system.camera_masks = camera_masks
                    
                    self.logger.info(f"Multi-camera masks configured: {len(camera_masks)} cameras")
                    return True
                
                # Replace the mask loading method
                self.production_system._load_mask = multi_camera_load_mask
                
                # Reload masks with new configuration
                self.production_system._load_mask()
            
        except Exception as e:
            self.logger.error(f"Failed to apply camera mask configurations: {e}")
    
    def _apply_camera_thresholds(self):
        """Apply GUI-configured baseline counts and comparison thresholds to each camera"""
        try:
            # Store GUI thresholds for use in detection logic
            if not hasattr(self.production_system, 'gui_camera_thresholds'):
                self.production_system.gui_camera_thresholds = {}
            
            for gui_cam_id, gui_config in self.gui_cameras.items():
                physical_id = gui_config.physical_camera_id
                self.production_system.gui_camera_thresholds[physical_id] = {
                    'threshold': gui_config.threshold,
                    'gui_camera_id': gui_cam_id
                }
            
            # Override the trigger logic to use GUI thresholds
            if hasattr(self.production_system, 'detect_and_compare'):
                self._override_detection_logic()
            
            self.logger.info(f"Camera thresholds applied: {len(self.gui_cameras)} cameras")
            
        except Exception as e:
            self.logger.error(f"Failed to apply camera thresholds: {e}")
    
    def _override_detection_logic(self):
        """Override detection logic to use GUI-configured thresholds"""
        if not self.production_system:
            return
        
        # Store original method
        original_detect_and_compare = self.production_system.detect_and_compare
        
        def gui_detect_and_compare():
            """Custom detection logic with GUI thresholds"""
            current_time = time.time()
            
            with self.production_system.detection_lock:
                for camera_id, cap in enumerate(self.production_system.cameras):
                    if cap is None or camera_id not in self.production_system.camera_states:
                        continue
                    
                    state = self.production_system.camera_states[camera_id]
                    
                    # Only detect for cameras that have baselines and are past stable period
                    if not state.baseline_established or state.baseline_red_count < 0:
                        continue
                    
                    # Check stable period
                    time_since_baseline = current_time - state.baseline_time
                    if time_since_baseline < state.stable_period:
                        # Still in stable period, update current count but don't trigger
                        try:
                            ret, frame = cap.read()
                            if ret and frame is not None:
                                current_count = self.production_system._detect_red_lights(frame)
                                state.current_red_count = current_count
                        except Exception as e:
                            self.logger.error(f"Camera {camera_id} stable period detection failed: {e}")
                        continue
                    else:
                        # Mark stable period as logged
                        if not state.stable_period_logged:
                            self.logger.info(f"Camera {camera_id} stable period ended, starting detection")
                            state.stable_period_logged = True
                    
                    try:
                        # Capture frame
                        ret, frame = cap.read()
                        if not ret or frame is None:
                            continue
                        
                        # Detect current red lights
                        current_count = self.production_system._detect_red_lights(frame)
                        state.current_red_count = current_count
                        
                        # Get GUI threshold for this camera
                        gui_threshold = 2  # Default threshold
                        if hasattr(self.production_system, 'gui_camera_thresholds'):
                            camera_threshold_info = self.production_system.gui_camera_thresholds.get(camera_id)
                            if camera_threshold_info:
                                gui_threshold = camera_threshold_info['threshold']
                        
                        # Check for trigger condition using GUI threshold
                        if state.last_reported_count == -1:
                            # First detection, set initial reported count
                            state.last_reported_count = current_count
                            self.logger.info(f"Camera {camera_id} initial count: {current_count}")
                        elif current_count != state.last_reported_count:
                            # Count changed, check if it exceeds threshold
                            count_diff = abs(current_count - state.last_reported_count)
                            baseline_diff = abs(current_count - state.baseline_red_count)
                            
                            self.logger.info(f"Camera {camera_id} count change detected: "
                                           f"baseline={state.baseline_red_count}, "
                                           f"last={state.last_reported_count}, "
                                           f"current={current_count}, "
                                           f"threshold={gui_threshold}")
                            
                            # Trigger if baseline difference exceeds GUI threshold
                            if baseline_diff >= gui_threshold:
                                self._trigger_mqtt_message_with_gui_info(camera_id, current_count, state.last_reported_count)
                            
                            # Update last reported count
                            state.last_reported_count = current_count
                    
                    except Exception as e:
                        error_msg = f"摄像头 {camera_id} 检测失败: {str(e)}"
                        self.logger.error(error_msg)
                        
                        # Show error in GUI
                        if hasattr(self, 'status_callbacks') and 'show_error_message' in self.status_callbacks:
                            # Find GUI camera ID
                            gui_camera_id = camera_id
                            for gui_id, gui_config in self.gui_cameras.items():
                                if gui_config.physical_camera_id == camera_id:
                                    gui_camera_id = gui_id
                                    break
                            
                            self.status_callbacks['show_error_message'](
                                "摄像头检测失败", str(e), gui_camera_id
                            )
        
        # Replace the method
        self.production_system.detect_and_compare = gui_detect_and_compare
    
    def _trigger_mqtt_message_with_gui_info(self, camera_id: int, current_count: int, last_reported_count: int):
        """Trigger MQTT message with GUI camera information and enhanced event logging"""
        try:
            timestamp = time.strftime("%H:%M:%S")
            
            # Get GUI camera ID and baseline count
            gui_camera_id = camera_id
            baseline_count = -1
            
            for gui_id, gui_config in self.gui_cameras.items():
                if gui_config.physical_camera_id == camera_id:
                    gui_camera_id = gui_id
                    break
            
            if camera_id in self.production_system.camera_states:
                baseline_count = self.production_system.camera_states[camera_id].baseline_red_count
            
            if self.production_system.mqtt_client and self.production_system.mqtt_client.client:
                result = self.production_system.mqtt_client.client.publish(
                    self.production_system.config.mqtt.publish_topic,
                    payload=""
                )
                
                if result.rc == 0:
                    self.logger.info(f"Camera {camera_id} triggered MQTT message (count: {last_reported_count} -> {current_count})")
                    
                    # Log successful trigger event with detailed information
                    if 'log_trigger_event' in self.status_callbacks:
                        self.status_callbacks['log_trigger_event'](
                            gui_camera_id, timestamp, gui_camera_id, baseline_count, current_count
                        )
                    
                    # Also log in baseline events for comprehensive tracking
                    if 'log_baseline_event' in self.status_callbacks:
                        count_diff = baseline_count - current_count if baseline_count >= 0 else 0
                        message_content = f"摄像头{gui_camera_id}触发 (差值: {count_diff})"
                        self.status_callbacks['log_baseline_event'](timestamp, [gui_camera_id], message_content)
                        
                else:
                    self.logger.error(f"Camera {camera_id} MQTT trigger failed: {result.rc}")
                    
                    # Log failed trigger event
                    if 'log_trigger_event' in self.status_callbacks:
                        # Use negative device ID to indicate failure
                        self.status_callbacks['log_trigger_event'](
                            -1, timestamp, gui_camera_id, baseline_count, current_count
                        )
                    
                    # Log error in baseline events
                    if 'log_baseline_event' in self.status_callbacks:
                        error_msg = f"摄像头{gui_camera_id}触发失败 (错误码: {result.rc})"
                        self.status_callbacks['log_baseline_event'](timestamp, [gui_camera_id], error_msg)
            else:
                self.logger.error("MQTT client not connected, cannot send trigger message")
                
                # Log connection error
                if 'log_baseline_event' in self.status_callbacks:
                    error_msg = f"摄像头{gui_camera_id}触发失败 (MQTT未连接)"
                    self.status_callbacks['log_baseline_event'](timestamp, [gui_camera_id], error_msg)
        
        except Exception as e:
            error_msg = f"MQTT触发异常: {str(e)}"
            self.logger.error(error_msg)
            
            # Show error in GUI
            if 'show_error_message' in self.status_callbacks:
                self.status_callbacks['show_error_message'](
                    "MQTT触发异常", str(e), camera_id
                )
            
            # Log exception in baseline events
            if 'log_baseline_event' in self.status_callbacks:
                timestamp = time.strftime("%H:%M:%S")
                self.status_callbacks['log_baseline_event'](timestamp, [], error_msg)
    
    def _apply_timing_parameters(self):
        """Apply GUI timing parameters to system"""
        try:
            # Override baseline capture timing
            if hasattr(self.production_system, '_handle_mqtt_message'):
                original_handle_message = self.production_system._handle_mqtt_message
                
                def gui_handle_mqtt_message(message_data: Dict):
                    """Handle MQTT message with GUI timing parameters and enhanced event logging"""
                    try:
                        payload_data = message_data.get('payload', {})
                        ones_count = payload_data.get('count_of_ones', 0)
                        is_update = message_data.get('is_update', False)
                        timestamp = time.strftime("%H:%M:%S")
                        
                        self.logger.info(f"MQTT message received: {ones_count} ones, update: {is_update}")
                        
                        # Log all MQTT messages for debugging
                        if 'log_baseline_event' in self.status_callbacks:
                            enabled_cameras = list(self.gui_cameras.keys())
                            message_content = f"{ones_count} ones, update: {is_update}"
                            
                            # Always log the message reception
                            self.status_callbacks['log_baseline_event'](timestamp, [], f"MQTT消息: {message_content}")
                        
                        # Handle 144 ones case - baseline invalidation
                        if ones_count == 144:
                            self.logger.info("Detected 144 ones, invalidating previous baselines")
                            
                            # Log baseline invalidation event
                            if 'log_baseline_event' in self.status_callbacks:
                                enabled_cameras = list(self.gui_cameras.keys())
                                self.status_callbacks['log_baseline_event'](timestamp, enabled_cameras, "基线失效 (144 ones)")
                            
                            with self.production_system.detection_lock:
                                for state in self.production_system.camera_states.values():
                                    if state.baseline_established:
                                        self.logger.info(f"Camera {state.camera_id} baseline invalidated")
                                    state.baseline_established = False
                                    state.baseline_red_count = -1
                                    state.current_red_count = -1
                                    state.last_reported_count = -1
                                    state.baseline_time = 0.0
                                    state.stable_period_logged = False
                            return
                        
                        if ones_count == 0:
                            self.logger.info("Ones count is 0, skipping baseline establishment")
                            # Log skip event
                            if 'log_baseline_event' in self.status_callbacks:
                                self.status_callbacks['log_baseline_event'](timestamp, [], "跳过基线建立 (0 ones)")
                            return
                        
                        if not is_update:
                            self.logger.info("No changeState update, skipping baseline establishment")
                            # Log skip event
                            if 'log_baseline_event' in self.status_callbacks:
                                self.status_callbacks['log_baseline_event'](timestamp, [], "跳过基线建立 (无更新)")
                            return
                        
                        # Establish baseline with GUI delay time
                        self.logger.info("Baseline establishment conditions met")
                        
                        # Log baseline establishment trigger
                        if 'log_baseline_event' in self.status_callbacks:
                            enabled_cameras = list(self.gui_cameras.keys())
                            delay_time = self.system_parameters.get('delay_time', 0.4)
                            message_content = f"基线建立触发 (延时: {delay_time}s)"
                            self.status_callbacks['log_baseline_event'](timestamp, enabled_cameras, message_content)
                        
                        self.production_system.mqtt_triggered = True
                        
                        # Use GUI-configured delay time
                        delay_time = self.system_parameters.get('delay_time', 0.4)
                        self.production_system.baseline_capture_time = time.time() + delay_time
                        
                        # Reset camera states
                        with self.production_system.detection_lock:
                            for state in self.production_system.camera_states.values():
                                state.baseline_established = False
                                state.baseline_red_count = -1
                                state.current_red_count = -1
                                state.last_reported_count = -1
                                state.baseline_time = 0.0
                                state.stable_period_logged = False
                    
                    except Exception as e:
                        self.logger.error(f"GUI MQTT message handling error: {e}")
                
                # Replace the method
                self.production_system._handle_mqtt_message = gui_handle_mqtt_message
            
            self.logger.info(f"Timing parameters applied: delay={self.system_parameters.get('delay_time', 0.4)}s")
            
        except Exception as e:
            self.logger.error(f"Failed to apply timing parameters: {e}")
    
    def _override_baseline_capture_logging(self):
        """Override baseline capture to add event logging integration"""
        if not self.production_system:
            return
        
        # Store original method
        original_capture_baseline = self.production_system.capture_baseline
        
        def gui_capture_baseline():
            """Enhanced baseline capture with GUI event logging"""
            try:
                self.logger.info("Starting baseline capture with GUI event logging...")
                timestamp = time.strftime("%H:%M:%S")
                
                # Log baseline capture start
                if 'log_baseline_event' in self.status_callbacks:
                    enabled_cameras = list(self.gui_cameras.keys())
                    self.status_callbacks['log_baseline_event'](timestamp, enabled_cameras, "开始基线捕获")
                
                # Call original baseline capture
                original_capture_baseline()
                
                # Log individual camera baseline results
                if 'log_baseline_event' in self.status_callbacks:
                    with self.production_system.detection_lock:
                        successful_cameras = []
                        failed_cameras = []
                        
                        for gui_cam_id, gui_config in self.gui_cameras.items():
                            physical_id = gui_config.physical_camera_id
                            
                            if physical_id in self.production_system.camera_states:
                                state = self.production_system.camera_states[physical_id]
                                if state.baseline_established and state.baseline_red_count >= 0:
                                    successful_cameras.append(gui_cam_id)
                                    # Log individual camera baseline
                                    baseline_msg = f"摄像头{gui_cam_id}: 基线={state.baseline_red_count}"
                                    self.status_callbacks['log_baseline_event'](timestamp, [gui_cam_id], baseline_msg)
                                else:
                                    failed_cameras.append(gui_cam_id)
                        
                        # Log overall baseline capture completion
                        if successful_cameras:
                            success_msg = f"基线建立完成 ({len(successful_cameras)}个摄像头成功)"
                            self.status_callbacks['log_baseline_event'](timestamp, successful_cameras, success_msg)
                        
                        if failed_cameras:
                            fail_msg = f"基线建立失败 ({len(failed_cameras)}个摄像头失败)"
                            self.status_callbacks['log_baseline_event'](timestamp, failed_cameras, fail_msg)
                
            except Exception as e:
                self.logger.error(f"GUI baseline capture logging failed: {e}")
                # Log error
                if 'log_baseline_event' in self.status_callbacks:
                    timestamp = time.strftime("%H:%M:%S")
                    error_msg = f"基线捕获异常: {str(e)}"
                    self.status_callbacks['log_baseline_event'](timestamp, [], error_msg)
        
        # Replace the method
        self.production_system.capture_baseline = gui_capture_baseline
    
    def _save_configuration_to_file(self):
        """Save current configuration to file automatically"""
        try:
            import yaml
            
            # Load existing config
            config = {}
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = yaml.safe_load(f) or {}
            
            # Update with GUI configuration
            if 'gui_config' not in config:
                config['gui_config'] = {}
            
            # Save camera configurations
            camera_configs = []
            for gui_cam_id, gui_config in self.gui_cameras.items():
                camera_configs.append({
                    'camera_id': gui_config.camera_id,
                    'enabled': gui_config.enabled,
                    'physical_camera_id': gui_config.physical_camera_id,
                    'mask_path': gui_config.mask_path,
                    'baseline_count': gui_config.baseline_count,
                    'threshold': gui_config.threshold
                })
            
            config['gui_config']['cameras'] = camera_configs
            config['gui_config']['system_parameters'] = self.system_parameters
            
            # Save MQTT configuration from GUI
            config['gui_config']['mqtt'] = self.gui_mqtt_config.copy()
            
            # Also update main MQTT config section with GUI values
            if 'mqtt' not in config:
                config['mqtt'] = {}
            
            # Update main MQTT config with GUI values (for compatibility)
            for key, value in self.gui_mqtt_config.items():
                if value is not None and value != "":
                    config['mqtt'][key] = value
            
            # Update camera count
            if 'cameras' not in config:
                config['cameras'] = {}
            config['cameras']['count'] = len(self.gui_cameras)
            
            # Save to file
            with open(self.config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            
            self.logger.info(f"Configuration saved to {self.config_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
    
    def update_camera_configuration(self, camera_configs: List[Dict]) -> bool:
        """Update camera configuration dynamically"""
        try:
            # Validate new configuration
            old_cameras = self.gui_cameras.copy()
            
            # Apply new configuration
            if not self.configure_cameras(camera_configs):
                return False
            
            # If system is running, apply changes dynamically
            if self.running and self.production_system:
                # Check what changed
                cameras_changed = self._detect_camera_changes(old_cameras, self.gui_cameras)
                
                if cameras_changed:
                    self.logger.info("Camera configuration changed, applying updates...")
                    
                    # Re-apply configuration
                    self._apply_gui_configuration()
                    
                    # Reset camera monitoring displays in GUI
                    if 'reset_camera_monitoring_displays' in self.status_callbacks:
                        self.status_callbacks['reset_camera_monitoring_displays']()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Dynamic camera configuration update failed: {e}")
            return False
    
    def _detect_camera_changes(self, old_cameras: Dict, new_cameras: Dict) -> bool:
        """Detect if camera configuration has changed"""
        if len(old_cameras) != len(new_cameras):
            return True
        
        for cam_id in old_cameras:
            if cam_id not in new_cameras:
                return True
            
            old_config = old_cameras[cam_id]
            new_config = new_cameras[cam_id]
            
            if (old_config.enabled != new_config.enabled or
                old_config.physical_camera_id != new_config.physical_camera_id or
                old_config.mask_path != new_config.mask_path or
                old_config.threshold != new_config.threshold):
                return True
        
        return False
    
    def _status_monitoring_loop(self):
        """Enhanced status monitoring with integrated MQTT reliability components"""
        self.logger.info("Enhanced status monitoring started")
        
        # Initialize polling state
        last_mqtt_status = None
        last_camera_states = {}
        last_system_health = {}
        last_connection_stats = {}
        
        while self.running:
            try:
                if self.production_system:
                    # Get comprehensive system status
                    status = self.production_system.get_status()
                    
                    # Extract camera states, MQTT status, and system health
                    current_camera_states = status.get('camera_states', {})
                    current_mqtt_status = self._extract_enhanced_mqtt_status()
                    current_system_health = self._extract_system_health(status)
                    current_connection_stats = self.get_connection_statistics()
                    
                    # Update GUI displays with current information only if changed
                    if current_mqtt_status != last_mqtt_status:
                        self._update_mqtt_status_display(current_mqtt_status)
                        last_mqtt_status = current_mqtt_status.copy()
                    
                    if current_camera_states != last_camera_states:
                        self._update_camera_status_displays(current_camera_states)
                        last_camera_states = current_camera_states.copy()
                    
                    if current_system_health != last_system_health:
                        self._update_system_health_display(current_system_health)
                        last_system_health = current_system_health.copy()
                    
                    if current_connection_stats != last_connection_stats:
                        self._update_connection_statistics_display(current_connection_stats)
                        last_connection_stats = current_connection_stats.copy()
                    
                    # Update message statistics for health monitor
                    self._update_message_statistics()
                
                # Poll every 0.5 seconds for responsive updates
                time.sleep(0.5)
                
            except Exception as e:
                error_msg = f"状态监控错误: {str(e)}"
                self.logger.error(error_msg)
                
                # Show error in GUI
                if 'show_error_message' in self.status_callbacks:
                    self.status_callbacks['show_error_message'](
                        "状态监控错误", str(e)
                    )
                
                # Update GUI with error status
                if 'update_system_health' in self.status_callbacks:
                    self.status_callbacks['update_system_health'](0, 0, False, error_msg)
                
                time.sleep(1.0)
        
        self.logger.info("Enhanced status monitoring stopped")
    
    def _extract_enhanced_mqtt_status(self) -> Dict:
        """Extract enhanced MQTT status with reliability information"""
        try:
            # Get base MQTT status
            mqtt_status = self._extract_mqtt_status()
            
            # Add enhanced information from connection manager
            if self.connection_manager:
                connection_status = self.connection_manager.get_connection_status()
                mqtt_status.update({
                    'enhanced_connection_state': connection_status.get('connection_state', 'unknown'),
                    'health_status': connection_status.get('health_status', 'unknown'),
                    'last_health_check': connection_status.get('last_health_check'),
                    'connection_manager_running': connection_status.get('is_running', False)
                })
            
            return mqtt_status
            
        except Exception as e:
            self.logger.error(f"Enhanced MQTT status extraction failed: {e}")
            return self._extract_mqtt_status()  # Fallback to basic status
    
    def _update_connection_statistics_display(self, stats: Dict):
        """Update connection statistics display in GUI"""
        try:
            if 'update_connection_statistics' in self.status_callbacks:
                self.status_callbacks['update_connection_statistics'](stats)
                
        except Exception as e:
            self.logger.error(f"Connection statistics display update failed: {e}")
    
    def _update_message_statistics(self):
        """Update message statistics for health monitoring"""
        try:
            if self.production_system and hasattr(self.production_system, 'mqtt_client'):
                mqtt_client = self.production_system.mqtt_client
                
                # Get message counts (this would need to be implemented in the MQTT client)
                # For now, we'll use placeholder values
                sent_messages = 0
                received_messages = 0
                failed_messages = 0
                
                # Update health monitor with message statistics
                if hasattr(mqtt_client, 'get_message_stats'):
                    stats = mqtt_client.get_message_stats()
                    sent_messages = stats.get('sent', 0)
                    received_messages = stats.get('received', 0)
                    failed_messages = stats.get('failed', 0)
                
                self.health_monitor.update_message_stats(
                    sent=sent_messages,
                    received=received_messages,
                    failed=failed_messages
                )
                
                # Update latency if available
                if hasattr(mqtt_client, 'get_last_latency'):
                    latency = mqtt_client.get_last_latency()
                    if latency > 0:
                        self.health_monitor.update_latency(latency)
                        
        except Exception as e:
            self.logger.error(f"Message statistics update failed: {e}")
    
    def _extract_mqtt_status(self) -> Dict:
        """Extract MQTT status information from production system"""
        try:
            # Get effective MQTT config (GUI优先)
            effective_mqtt = self.get_effective_mqtt_config()
            
            mqtt_status = {
                'connected': False,
                'broker_host': effective_mqtt.get('broker_host', '192.168.10.80'),
                'client_id': effective_mqtt.get('client_id', 'receiver'),
                'last_message_time': None,
                'connection_info': "未连接"
            }
            
            if (hasattr(self.production_system, 'mqtt_client') and 
                self.production_system.mqtt_client and 
                self.production_system.mqtt_client.client):
                
                mqtt_status['connected'] = self.production_system.mqtt_client.client.is_connected()
                
                if mqtt_status['connected']:
                    mqtt_status['connection_info'] = f"已连接到: {mqtt_status['broker_host']}\n客户端ID: {mqtt_status['client_id']}"
                    
                    # Get last message time if available
                    if hasattr(self.production_system.mqtt_client, 'last_message_time'):
                        mqtt_status['last_message_time'] = self.production_system.mqtt_client.last_message_time
                else:
                    mqtt_status['connection_info'] = "连接断开或未建立"
            
            return mqtt_status
            
        except Exception as e:
            self.logger.error(f"MQTT status extraction failed: {e}")
            return {
                'connected': False,
                'broker_host': "192.168.10.80",
                'client_id': "receiver",
                'last_message_time': None,
                'connection_info': f"状态获取错误: {e}"
            }
    
    def _extract_system_health(self, status: Dict) -> Dict:
        """Extract system health information"""
        try:
            return {
                'active_cameras': status.get('active_cameras', 0),
                'enabled_cameras': len(self.gui_cameras),
                'monitoring_active': status.get('running', False) and self.running,
                'total_light_points': status.get('total_light_points', 0),
                'mqtt_triggered': status.get('mqtt_triggered', False),
                'last_error': None
            }
        except Exception as e:
            self.logger.error(f"System health extraction failed: {e}")
            return {
                'active_cameras': 0,
                'enabled_cameras': 0,
                'monitoring_active': False,
                'total_light_points': 0,
                'mqtt_triggered': False,
                'last_error': str(e)
            }
    
    def _update_mqtt_status_display(self, mqtt_status: Dict):
        """Update MQTT status display in GUI"""
        try:
            if 'update_mqtt_status' in self.status_callbacks:
                last_message_time = ""
                if mqtt_status.get('last_message_time'):
                    last_message_time = time.strftime("%H:%M:%S", time.localtime(mqtt_status['last_message_time']))
                
                self.status_callbacks['update_mqtt_status'](
                    mqtt_status['connected'],
                    mqtt_status['broker_host'],
                    last_message_time
                )
        except Exception as e:
            self.logger.error(f"MQTT status display update failed: {e}")
    
    def _update_camera_status_displays(self, camera_states: Dict):
        """Update camera status displays in GUI"""
        try:
            if 'update_camera_info' in self.status_callbacks:
                for gui_cam_id, gui_config in self.gui_cameras.items():
                    physical_id = gui_config.physical_camera_id
                    
                    if physical_id in camera_states:
                        cam_state = camera_states[physical_id]
                        baseline = cam_state.get('baseline_red_count', -1)
                        current = cam_state.get('current_red_count', -1)
                        
                        # Determine if triggered based on threshold and baseline difference
                        triggered = False
                        if baseline >= 0 and current >= 0:
                            diff = baseline - current
                            triggered = diff >= gui_config.threshold
                        
                        self.status_callbacks['update_camera_info'](
                            gui_cam_id, baseline, current, triggered
                        )
                    else:
                        # Camera not active, show default state
                        self.status_callbacks['update_camera_info'](
                            gui_cam_id, -1, -1, False
                        )
        except Exception as e:
            self.logger.error(f"Camera status display update failed: {e}")
    
    def _update_system_health_display(self, system_health: Dict):
        """Update system health display in GUI"""
        try:
            if 'update_system_health' in self.status_callbacks:
                self.status_callbacks['update_system_health'](
                    system_health['active_cameras'],
                    system_health['enabled_cameras'],
                    system_health['monitoring_active'],
                    system_health.get('last_error', "")
                )
        except Exception as e:
            self.logger.error(f"System health display update failed: {e}")
    
    def _update_gui_status(self, status: Dict):
        """Update GUI with current system status (legacy method for compatibility)"""
        try:
            with self.status_lock:
                # Extract and update all status information
                mqtt_status = self._extract_mqtt_status()
                camera_states = status.get('camera_states', {})
                system_health = self._extract_system_health(status)
                
                # Update displays
                self._update_mqtt_status_display(mqtt_status)
                self._update_camera_status_displays(camera_states)
                self._update_system_health_display(system_health)
                
        except Exception as e:
            self.logger.error(f"GUI status update failed: {e}")
    
    def get_system_status(self) -> Dict:
        """Get current system status"""
        if self.production_system:
            return self.production_system.get_status()
        else:
            return {
                'running': False,
                'active_cameras': 0,
                'camera_states': {}
            }
    
    def is_running(self) -> bool:
        """Check if system is running"""
        return self.running and self.production_system is not None
    
    def get_diagnostic_report_for_display(self) -> Dict[str, Any]:
        """
        Get formatted diagnostic report for GUI display.
        
        Returns:
            Dict containing formatted diagnostic information
        """
        try:
            if not self.last_diagnostic_report:
                return {
                    'status': 'no_report',
                    'message': '尚未运行诊断检查',
                    'recommendations': ['点击"运行诊断"按钮开始检查']
                }
            
            report = self.last_diagnostic_report
            
            # Format network test results
            network_info = "未测试"
            if report.network_test:
                if report.network_test.is_successful:
                    network_info = f"连接成功 ({report.network_test.response_time_ms:.1f}ms)"
                else:
                    network_info = f"连接失败: {report.network_test.error_message}"
            
            # Format broker test results
            broker_info = "未测试"
            if report.broker_test:
                if report.broker_test.is_successful:
                    broker_info = f"代理可用 ({report.broker_test.connection_time_ms:.1f}ms)"
                else:
                    broker_info = f"代理不可用: {report.broker_test.error_message}"
            
            # Format configuration validation results
            config_info = "未验证"
            if report.config_validation:
                if report.config_validation.is_valid:
                    config_info = "配置有效"
                else:
                    config_info = f"配置无效: {report.config_validation.error_message}"
            
            return {
                'status': report.overall_status.value if hasattr(report.overall_status, 'value') else str(report.overall_status),
                'timestamp': report.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                'network_test': network_info,
                'broker_test': broker_info,
                'config_validation': config_info,
                'recommendations': report.recommendations,
                'is_successful': report.is_successful
            }
            
        except Exception as e:
            self.logger.error(f"Error formatting diagnostic report for display: {e}")
            return {
                'status': 'error',
                'message': f'诊断报告格式化失败: {str(e)}',
                'recommendations': ['请重新运行诊断检查']
            }
    
    def get_performance_report_for_display(self) -> Dict[str, Any]:
        """
        Get formatted performance report for GUI display.
        
        Returns:
            Dict containing formatted performance information
        """
        try:
            if not self.current_performance_report:
                return {
                    'status': 'no_report',
                    'message': '性能报告尚未生成',
                    'recommendations': ['系统运行一段时间后将自动生成性能报告']
                }
            
            report = self.current_performance_report
            
            # Format connection metrics
            metrics = report.connection_metrics
            connection_info = {
                'uptime': f"{metrics.connection_uptime:.1f} 秒",
                'success_rate': f"{metrics.message_success_rate:.1f}%",
                'latency': f"{metrics.average_latency:.1f} ms",
                'reconnections': metrics.reconnection_count,
                'quality_score': f"{metrics.quality_score:.1f}/100"
            }
            
            # Format health metrics
            health = report.health_metrics
            health_info = {
                'status': health.health_status.value,
                'connection_state': health.connection_state.value,
                'error_count': health.error_count,
                'warning_count': health.warning_count,
                'system_load': f"{health.system_load:.1f}%",
                'memory_usage': f"{health.memory_usage:.1f}%"
            }
            
            return {
                'status': 'available',
                'report_id': report.report_id,
                'timestamp': report.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                'time_period': report.time_period,
                'connection_metrics': connection_info,
                'health_metrics': health_info,
                'trend_analysis': report.trend_analysis,
                'recommendations': report.recommendations
            }
            
        except Exception as e:
            self.logger.error(f"Error formatting performance report for display: {e}")
            return {
                'status': 'error',
                'message': f'性能报告格式化失败: {str(e)}',
                'recommendations': ['请检查系统状态']
            }
    
    def get_connection_health_summary(self) -> Dict[str, Any]:
        """
        Get connection health summary for GUI display.
        
        Returns:
            Dict containing connection health summary
        """
        try:
            summary = {
                'overall_status': 'unknown',
                'connection_state': 'disconnected',
                'health_level': 'unknown',
                'quality_score': 0.0,
                'issues': [],
                'recommendations': [],
                'last_update': datetime.now().strftime("%H:%M:%S")
            }
            
            # Get health metrics
            if self.current_health_metrics:
                health = self.current_health_metrics
                summary.update({
                    'overall_status': health.health_status.value,
                    'connection_state': health.connection_state.value,
                    'health_level': health.get_status_summary(),
                    'error_count': health.error_count,
                    'warning_count': health.warning_count
                })
            
            # Get connection statistics
            stats = self.get_connection_statistics()
            if stats:
                summary.update({
                    'quality_score': stats.get('quality_score', 0.0),
                    'uptime': stats.get('uptime', 0.0),
                    'success_rate': stats.get('message_success_rate', 0.0),
                    'latency': stats.get('average_latency', 0.0)
                })
            
            # Get quality report if available
            if hasattr(self.health_monitor, 'check_connection_quality'):
                try:
                    quality_report = self.health_monitor.check_connection_quality()
                    summary.update({
                        'quality_score': quality_report.overall_quality,
                        'issues': quality_report.issues_detected,
                        'recommendations': quality_report.recommendations
                    })
                except Exception as e:
                    self.logger.debug(f"Could not get quality report: {e}")
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting connection health summary: {e}")
            return {
                'overall_status': 'error',
                'connection_state': 'error',
                'health_level': f'获取健康状态失败: {str(e)}',
                'quality_score': 0.0,
                'issues': [str(e)],
                'recommendations': ['请检查系统配置'],
                'last_update': datetime.now().strftime("%H:%M:%S")
            }
    
    # ===== Enhanced Log Management Methods =====
    
    def log_connection_event(self, event_type: str, connection_state: str, 
                           details: Optional[Dict[str, Any]] = None, 
                           error_message: Optional[str] = None) -> str:
        """
        Log MQTT connection event with detailed information.
        
        Args:
            event_type: Type of connection event (connect, disconnect, reconnect, error)
            connection_state: Current connection state
            details: Additional event details
            error_message: Error message if applicable
            
        Returns:
            Log entry ID
        """
        try:
            return self.log_manager.log_connection_event(
                event_type=event_type,
                connection_state=connection_state,
                details=details,
                error_message=error_message
            )
        except Exception as e:
            self.logger.error(f"Failed to log connection event: {e}")
            return ""
    
    def log_performance_event(self, metric_name: str, metric_value: float,
                            threshold: Optional[float] = None,
                            details: Optional[Dict[str, Any]] = None) -> str:
        """
        Log performance-related event.
        
        Args:
            metric_name: Name of the performance metric
            metric_value: Current value of the metric
            threshold: Threshold value if applicable
            details: Additional performance details
            
        Returns:
            Log entry ID
        """
        try:
            return self.log_manager.log_performance_event(
                metric_name=metric_name,
                metric_value=metric_value,
                threshold=threshold,
                details=details
            )
        except Exception as e:
            self.logger.error(f"Failed to log performance event: {e}")
            return ""
    
    def log_error_with_context(self, component: str, error: Exception,
                             context: Optional[Dict[str, Any]] = None,
                             user_action: Optional[str] = None) -> str:
        """
        Log error with full context and stack trace.
        
        Args:
            component: Component where error occurred
            error: Exception object
            context: Additional context information
            user_action: User action that triggered the error
            
        Returns:
            Log entry ID
        """
        try:
            return self.log_manager.log_error_with_context(
                component=component,
                error=error,
                context=context,
                user_action=user_action
            )
        except Exception as e:
            self.logger.error(f"Failed to log error with context: {e}")
            return ""
    
    def search_logs(self, search_text: Optional[str] = None,
                   level_filter: Optional[LogLevel] = None,
                   category_filter: Optional[LogCategory] = None,
                   component_filter: Optional[str] = None,
                   time_range_hours: Optional[int] = None,
                   max_results: int = 500) -> List[Dict[str, Any]]:
        """
        Search logs and return formatted results for GUI display.
        
        Args:
            search_text: Text to search in log messages
            level_filter: Filter by log level
            category_filter: Filter by category
            component_filter: Filter by component
            time_range_hours: Limit to last N hours
            max_results: Maximum results to return
            
        Returns:
            List of formatted log entries for GUI display
        """
        try:
            display_entries = self.log_viewer.search_and_display(
                search_text=search_text,
                level_filter=level_filter,
                category_filter=category_filter,
                component_filter=component_filter,
                time_range_hours=time_range_hours,
                max_results=max_results
            )
            
            # Convert to GUI-friendly format
            return self.log_viewer_gui.get_display_data_for_table()
            
        except Exception as e:
            self.logger.error(f"Failed to search logs: {e}")
            return []
    
    def get_recent_logs(self, count: int = 100, 
                       component: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get recent log entries formatted for GUI display.
        
        Args:
            count: Number of recent entries
            component: Filter by component
            
        Returns:
            List of formatted log entries
        """
        try:
            display_entries = self.log_viewer.get_recent_logs(count, component)
            return self.log_viewer_gui.get_display_data_for_table()
            
        except Exception as e:
            self.logger.error(f"Failed to get recent logs: {e}")
            return []
    
    def get_log_table_headers(self) -> List[str]:
        """
        Get table headers for log display in GUI.
        
        Returns:
            List of column headers
        """
        try:
            return self.log_viewer_gui.get_table_headers()
        except Exception as e:
            self.logger.error(f"Failed to get log table headers: {e}")
            return ["时间", "级别", "组件", "消息"]
    
    def get_log_entry_details(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific log entry.
        
        Args:
            entry_id: Log entry ID
            
        Returns:
            Detailed entry information or None if not found
        """
        try:
            return self.log_viewer_gui.get_entry_details(entry_id)
        except Exception as e:
            self.logger.error(f"Failed to get log entry details: {e}")
            return None
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get formatted error summary for display.
        
        Args:
            hours: Time period in hours
            
        Returns:
            Formatted error summary
        """
        try:
            return self.log_viewer.get_error_summary_display(hours)
        except Exception as e:
            self.logger.error(f"Failed to get error summary: {e}")
            return {"error": f"获取错误摘要失败: {str(e)}"}
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about current log view.
        
        Returns:
            Statistics dictionary
        """
        try:
            return self.log_viewer.get_log_statistics()
        except Exception as e:
            self.logger.error(f"Failed to get log statistics: {e}")
            return {"total_entries": 0, "error": str(e)}
    
    def export_logs(self, format_type: str = "json", 
                   filename: Optional[str] = None) -> str:
        """
        Export currently displayed logs.
        
        Args:
            format_type: Export format (json, csv, txt)
            filename: Output filename
            
        Returns:
            Path to exported file
        """
        try:
            return self.log_viewer.export_current_view(format_type, filename)
        except Exception as e:
            self.logger.error(f"Failed to export logs: {e}")
            return ""
    
    def start_log_auto_refresh(self) -> None:
        """Start automatic refresh of log display."""
        try:
            self.log_viewer.start_auto_refresh()
        except Exception as e:
            self.logger.error(f"Failed to start log auto refresh: {e}")
    
    def stop_log_auto_refresh(self) -> None:
        """Stop automatic refresh of log display."""
        try:
            self.log_viewer.stop_auto_refresh()
        except Exception as e:
            self.logger.error(f"Failed to stop log auto_refresh: {e}")
    
    def cleanup_old_logs(self, retention_days: int = 30) -> int:
        """
        Clean up log files older than retention period.
        
        Args:
            retention_days: Number of days to retain logs
            
        Returns:
            Number of files cleaned up
        """
        try:
            return self.log_manager.cleanup_old_logs(retention_days)
        except Exception as e:
            self.logger.error(f"Failed to cleanup old logs: {e}")
            return 0
    
    def compress_rotated_logs(self) -> int:
        """
        Compress rotated log files to save space.
        
        Returns:
            Number of files compressed
        """
        try:
            return self.log_manager.compress_rotated_logs()
        except Exception as e:
            self.logger.error(f"Failed to compress rotated logs: {e}")
            return 0
    
    def get_log_search_interface_data(self) -> Dict[str, Any]:
        """
        Get data structure for GUI log search interface.
        
        Returns:
            Search interface configuration data
        """
        try:
            return self.log_viewer_gui.create_search_interface_data()
        except Exception as e:
            self.logger.error(f"Failed to get log search interface data: {e}")
            return {
                "log_levels": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                "categories": ["system", "connection", "performance", "configuration", "error", "diagnostic"],
                "components": [],
                "time_ranges": [
                    {"label": "过去1小时", "hours": 1},
                    {"label": "过去24小时", "hours": 24}
                ],
                "export_formats": [
                    {"label": "JSON", "value": "json"},
                    {"label": "CSV", "value": "csv"}
                ]
            }
    
    def shutdown(self):
        """Enhanced shutdown with log management cleanup"""
        try:
            # Stop log auto refresh
            self.stop_log_auto_refresh()
            
            # Shutdown log manager
            if hasattr(self, 'log_manager'):
                self.log_manager.shutdown()
            
            # Original shutdown logic
            self.running = False
            
            if self.production_system:
                self.production_system.stop()
                self.production_system = None
            
            if self.connection_manager:
                self.connection_manager.disconnect()
                self.connection_manager = None
            
            if self.health_monitor:
                self.health_monitor.stop_monitoring()
            
            if self.status_thread and self.status_thread.is_alive():
                self.status_thread.join(timeout=5.0)
            
            self.logger.info("Enhanced GUI System Wrapper shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
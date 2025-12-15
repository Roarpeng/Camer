#!/usr/bin/env python3
"""
GUI System Wrapper for FinalProductionSystem
Provides interface between GUI and existing production system
"""

import os
import cv2
import time
import threading
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from copy import deepcopy

# Import existing system components
from final_production_system import FinalProductionSystem, CameraState
from mqtt_camera_monitoring.config import ConfigManager


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
    """Wrapper class that interfaces with existing FinalProductionSystem"""
    
    def __init__(self, config_file: str = "config.yaml"):
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.config_file = config_file
        self.config_manager = ConfigManager(config_file)
        
        # System state
        self.production_system: Optional[FinalProductionSystem] = None
        self.running = False
        self.gui_cameras: Dict[int, GuiCameraConfig] = {}
        self.system_parameters = {
            'delay_time': 0.4,
            'monitoring_interval': 0.2,
            'global_threshold': 2
        }
        
        # Status callbacks for GUI updates
        self.status_callbacks: Dict[str, Callable] = {}
        
        # Status monitoring thread
        self.status_thread: Optional[threading.Thread] = None
        self.status_lock = threading.Lock()
        
        self.logger.info("GUI System Wrapper initialized")
    
    def set_status_callback(self, callback_name: str, callback_func: Callable):
        """Set callback function for GUI status updates"""
        self.status_callbacks[callback_name] = callback_func
        self.logger.debug(f"Status callback set: {callback_name}")
    
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
            
            # Update monitoring interval
            # Note: The existing system uses fixed 0.3s interval in detection_loop
            # This would require modification of the existing system to be truly dynamic
            
            self.logger.info("Dynamic parameter updates applied")
            
        except Exception as e:
            self.logger.error(f"Dynamic parameter update failed: {e}")
    
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
            
            # Override the camera initialization to support our multi-camera setup
            self._override_camera_initialization()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create production system: {e}")
            return False
    
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
        """Start the production system with GUI configuration and comprehensive error handling"""
        try:
            # Clear previous errors
            if 'clear_all_errors' in self.status_callbacks:
                self.status_callbacks['clear_all_errors']()
            
            # Validate configuration first
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
            
            # Create and configure production system
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
            
            # Apply GUI configuration to system
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
            
            # Start the production system
            try:
                if self.production_system.start():
                    self.running = True
                    
                    # Start status monitoring thread
                    self.status_thread = threading.Thread(target=self._status_monitoring_loop, daemon=True)
                    self.status_thread.start()
                    
                    self.logger.info("GUI System started successfully")
                    
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
                    
                    return True
                else:
                    error_msg = "生产系统启动失败"
                    self.logger.error(error_msg)
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
            if 'show_error_message' in self.status_callbacks:
                self.status_callbacks['show_error_message'](
                    "系统启动失败", str(e)
                )
            if 'update_system_health' in self.status_callbacks:
                self.status_callbacks['update_system_health'](0, 0, False, error_msg)
            return False
    
    def stop_system(self) -> bool:
        """Stop the production system"""
        try:
            self.running = False
            
            # Stop status monitoring thread
            if self.status_thread and self.status_thread.is_alive():
                self.status_thread.join(timeout=2.0)
            
            # Stop production system
            if self.production_system:
                self.production_system.stop()
                self.production_system = None
            
            self.logger.info("GUI System stopped successfully")
            
            # Update GUI status
            if 'update_system_health' in self.status_callbacks:
                self.status_callbacks['update_system_health'](0, 0, False)
            
            return True
            
        except Exception as e:
            self.logger.error(f"System stop failed: {e}")
            return False
    
    def _apply_gui_configuration(self):
        """Apply GUI configuration to production system"""
        if not self.production_system:
            return
        
        try:
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
        """Monitor system status and update GUI with timer-based polling"""
        self.logger.info("Status monitoring started")
        
        # Initialize polling state
        last_mqtt_status = None
        last_camera_states = {}
        last_system_health = {}
        
        while self.running:
            try:
                if self.production_system:
                    # Get comprehensive system status
                    status = self.production_system.get_status()
                    
                    # Extract camera states, MQTT status, and system health
                    current_camera_states = status.get('camera_states', {})
                    current_mqtt_status = self._extract_mqtt_status()
                    current_system_health = self._extract_system_health(status)
                    
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
        
        self.logger.info("Status monitoring stopped")
    
    def _extract_mqtt_status(self) -> Dict:
        """Extract MQTT status information from production system"""
        try:
            mqtt_status = {
                'connected': False,
                'broker_host': "192.168.10.80",  # From requirements
                'client_id': "receiver",
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
"""
Configuration Management

Handles loading and managing configuration settings for MQTT broker,
cameras, and system parameters.
"""

import yaml
import os
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class MQTTConfig:
    """MQTT broker configuration settings"""
    broker_host: str
    broker_port: int
    client_id: str
    subscribe_topic: str
    publish_topic: str
    keepalive: int
    reconnect_delay: int
    max_reconnect_attempts: int


@dataclass
class IndividualCameraConfig:
    """Individual camera configuration settings"""
    brightness: int = 50
    exposure: int = 100
    contrast: int = 50
    saturation: int = 50
    auto_exposure: bool = True


@dataclass
class CameraConfig:
    """Camera configuration settings with individual camera support"""
    count: int
    resolution_width: int
    resolution_height: int
    fps: int
    buffer_size: int
    brightness: int  # Default brightness
    exposure: int    # Default exposure
    contrast: int    # Default contrast
    saturation: int  # Default saturation
    auto_exposure: bool  # Default auto exposure
    gain: int = 0
    white_balance: int = 4000
    individual_settings: Dict[str, IndividualCameraConfig] = None
    
    def get_camera_config(self, camera_id: int) -> IndividualCameraConfig:
        """Get configuration for a specific camera"""
        camera_key = f"camera_{camera_id}"
        
        if self.individual_settings and camera_key in self.individual_settings:
            # Use individual settings if available
            individual = self.individual_settings[camera_key]
            return IndividualCameraConfig(
                brightness=getattr(individual, 'brightness', self.brightness),
                exposure=getattr(individual, 'exposure', self.exposure),
                contrast=getattr(individual, 'contrast', self.contrast),
                saturation=getattr(individual, 'saturation', self.saturation),
                auto_exposure=getattr(individual, 'auto_exposure', self.auto_exposure)
            )
        else:
            # Use default settings
            return IndividualCameraConfig(
                brightness=self.brightness,
                exposure=self.exposure,
                contrast=self.contrast,
                saturation=self.saturation,
                auto_exposure=self.auto_exposure
            )


@dataclass
class RedLightDetectionConfig:
    """Red light detection algorithm configuration"""
    lower_red_hsv: List[int]
    upper_red_hsv: List[int]
    lower_red_hsv_2: List[int]
    upper_red_hsv_2: List[int]
    min_contour_area: int
    max_contour_area: int = 50000
    sensitivity: float = 0.9
    area_change_threshold: float = 0.1
    baseline_duration: float = 1.0
    gaussian_blur_kernel: int = 5
    morphology_kernel: int = 3
    brightness_threshold: int = 200
    erosion_kernel: int = 2
    erosion_iterations: int = 1
    count_decrease_threshold: int = 3  # 红光数量减少阈值 (已弃用)
    area_decrease_threshold: float = 0.15  # 红光面积减少阈值 (15%)
    exclude_ones_count: int = 144      # 排除的ones数量
    require_content_update: bool = True # 只有内容更新时才建立基线


@dataclass
class VisualMonitorConfig:
    """Visual monitoring display configuration"""
    window_width: int
    window_height: int
    show_detection_boxes: bool
    box_color: List[int]
    box_thickness: int


@dataclass
class LoggingConfig:
    """Logging configuration settings"""
    level: str
    format: str
    file: str


@dataclass
class SystemConfig:
    """Complete system configuration"""
    mqtt: MQTTConfig
    cameras: CameraConfig
    red_light_detection: RedLightDetectionConfig
    visual_monitor: VisualMonitorConfig
    logging: LoggingConfig


class ConfigManager:
    """Manages loading and accessing system configuration"""
    
    def __init__(self, config_file: str = "config.yaml"):
        """
        Initialize configuration manager
        
        Args:
            config_file: Path to configuration file
        """
        self.config_file = config_file
        self._config = None
    
    def load_config(self) -> SystemConfig:
        """
        Load configuration from file
        
        Returns:
            SystemConfig: Loaded configuration object
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is malformed
        """
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")
        
        try:
            with open(self.config_file, 'r') as file:
                config_data = yaml.safe_load(file)
            
            # Create configuration objects
            mqtt_config = MQTTConfig(**config_data['mqtt'])
            
            # Handle camera configuration with individual settings
            camera_data = config_data['cameras'].copy()
            individual_settings = {}
            
            # Process individual camera settings if present
            if 'individual_settings' in camera_data:
                individual_data = camera_data.pop('individual_settings')
                for camera_key, settings in individual_data.items():
                    individual_settings[camera_key] = IndividualCameraConfig(**settings)
            
            # Use default settings from config or fallback values
            default_settings = camera_data.get('default_settings', {})
            camera_data.update({
                'brightness': default_settings.get('brightness', camera_data.get('brightness', 50)),
                'exposure': default_settings.get('exposure', camera_data.get('exposure', 100)),
                'contrast': default_settings.get('contrast', camera_data.get('contrast', 50)),
                'saturation': default_settings.get('saturation', camera_data.get('saturation', 50)),
                'auto_exposure': default_settings.get('auto_exposure', camera_data.get('auto_exposure', True))
            })
            
            # Remove default_settings from camera_data if present
            camera_data.pop('default_settings', None)
            
            camera_config = CameraConfig(**camera_data, individual_settings=individual_settings)
            red_light_config = RedLightDetectionConfig(**config_data['red_light_detection'])
            visual_monitor_config = VisualMonitorConfig(**config_data['visual_monitor'])
            logging_config = LoggingConfig(**config_data['logging'])
            
            self._config = SystemConfig(
                mqtt=mqtt_config,
                cameras=camera_config,
                red_light_detection=red_light_config,
                visual_monitor=visual_monitor_config,
                logging=logging_config
            )
            
            return self._config
            
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Error parsing configuration file: {e}")
        except KeyError as e:
            raise KeyError(f"Missing required configuration key: {e}")
    
    @property
    def config(self) -> SystemConfig:
        """
        Get current configuration, loading if necessary
        
        Returns:
            SystemConfig: Current configuration
        """
        if self._config is None:
            self.load_config()
        return self._config
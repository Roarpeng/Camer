#!/usr/bin/env python3
"""
GUI Configuration Manager
Handles automatic saving and loading of GUI configuration with real-time persistence
"""

import os
import yaml
import time
import threading
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from copy import deepcopy

from mqtt_camera_monitoring.config import ConfigManager


@dataclass
class GuiCameraConfig:
    """GUI camera configuration"""
    camera_id: int
    enabled: bool
    physical_camera_id: int
    mask_path: str
    baseline_count: int
    threshold: int


@dataclass
class GuiSystemParameters:
    """GUI system parameters"""
    delay_time: float
    monitoring_interval: float
    global_threshold: int


@dataclass
class GuiConfiguration:
    """Complete GUI configuration"""
    cameras: List[GuiCameraConfig]
    system_parameters: GuiSystemParameters
    last_updated: float


class GuiConfigManager:
    """Manages GUI configuration with automatic persistence"""
    
    def __init__(self, config_file: str = "config.yaml", auto_save: bool = True):
        """
        Initialize GUI configuration manager
        
        Args:
            config_file: Path to configuration file
            auto_save: Enable automatic saving on parameter changes
        """
        self.config_file = config_file
        self.auto_save = auto_save
        self.logger = logging.getLogger(__name__)
        
        # Configuration state
        self._gui_config: Optional[GuiConfiguration] = None
        self._config_lock = threading.Lock()
        self._save_pending = False
        self._last_save_time = 0.0
        
        # Auto-save settings
        self.save_delay = 1.0  # Delay before saving (seconds)
        self.save_thread: Optional[threading.Thread] = None
        self.save_stop_event = threading.Event()
        
        # Change callbacks
        self.change_callbacks: List[Callable[[GuiConfiguration], None]] = []
        
        # Base config manager
        self.base_config_manager = ConfigManager(config_file)
        
        # Start auto-save thread if enabled
        if self.auto_save:
            self._start_auto_save_thread()
        
        self.logger.info(f"GUI Config Manager initialized with auto-save: {auto_save}")
    
    def _start_auto_save_thread(self):
        """Start the auto-save background thread"""
        if self.save_thread is None or not self.save_thread.is_alive():
            self.save_stop_event.clear()
            self.save_thread = threading.Thread(target=self._auto_save_loop, daemon=True)
            self.save_thread.start()
            self.logger.debug("Auto-save thread started")
    
    def _auto_save_loop(self):
        """Auto-save loop that runs in background thread"""
        while not self.save_stop_event.wait(0.5):  # Check every 0.5 seconds
            try:
                current_time = time.time()
                
                with self._config_lock:
                    if (self._save_pending and 
                        current_time - self._last_save_time >= self.save_delay):
                        
                        self._save_to_file()
                        self._save_pending = False
                        self.logger.debug("Auto-save completed")
                        
            except Exception as e:
                self.logger.error(f"Auto-save error: {e}")
        
        self.logger.debug("Auto-save thread stopped")
    
    def load_gui_configuration(self) -> GuiConfiguration:
        """
        Load GUI configuration from file
        
        Returns:
            GuiConfiguration: Loaded GUI configuration
        """
        try:
            with self._config_lock:
                # Load base configuration
                if not os.path.exists(self.config_file):
                    self.logger.warning(f"Config file not found: {self.config_file}, creating default")
                    return self._create_default_configuration()
                
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f) or {}
                
                # Extract GUI configuration
                gui_data = config_data.get('gui_config', {})
                
                # Load camera configurations
                cameras = []
                camera_data = gui_data.get('cameras', [])
                
                # Ensure we have 6 camera configurations
                for i in range(6):
                    if i < len(camera_data):
                        cam_data = camera_data[i]
                        cameras.append(GuiCameraConfig(
                            camera_id=cam_data.get('camera_id', i),
                            enabled=cam_data.get('enabled', False),
                            physical_camera_id=cam_data.get('physical_camera_id', i),
                            mask_path=cam_data.get('mask_path', ''),
                            baseline_count=cam_data.get('baseline_count', 0),
                            threshold=cam_data.get('threshold', 2)
                        ))
                    else:
                        # Create default camera configuration
                        cameras.append(GuiCameraConfig(
                            camera_id=i,
                            enabled=False,
                            physical_camera_id=i,
                            mask_path='',
                            baseline_count=0,
                            threshold=2
                        ))
                
                # Load system parameters
                sys_params_data = gui_data.get('system_parameters', {})
                system_parameters = GuiSystemParameters(
                    delay_time=sys_params_data.get('delay_time', 0.4),
                    monitoring_interval=sys_params_data.get('monitoring_interval', 0.2),
                    global_threshold=sys_params_data.get('global_threshold', 2)
                )
                
                self._gui_config = GuiConfiguration(
                    cameras=cameras,
                    system_parameters=system_parameters,
                    last_updated=time.time()
                )
                
                self.logger.info("GUI configuration loaded successfully")
                return self._gui_config
                
        except Exception as e:
            self.logger.error(f"Failed to load GUI configuration: {e}")
            return self._create_default_configuration()
    
    def _create_default_configuration(self) -> GuiConfiguration:
        """Create default GUI configuration"""
        cameras = []
        for i in range(6):
            cameras.append(GuiCameraConfig(
                camera_id=i,
                enabled=False,
                physical_camera_id=i,
                mask_path='',
                baseline_count=0,
                threshold=2
            ))
        
        system_parameters = GuiSystemParameters(
            delay_time=0.4,
            monitoring_interval=0.2,
            global_threshold=2
        )
        
        config = GuiConfiguration(
            cameras=cameras,
            system_parameters=system_parameters,
            last_updated=time.time()
        )
        
        self._gui_config = config
        self.logger.info("Created default GUI configuration")
        return config
    
    def save_gui_configuration(self, config: GuiConfiguration, immediate: bool = False) -> bool:
        """
        Save GUI configuration to file
        
        Args:
            config: GUI configuration to save
            immediate: If True, save immediately; if False, schedule auto-save
            
        Returns:
            bool: True if save was successful or scheduled
        """
        try:
            with self._config_lock:
                self._gui_config = deepcopy(config)
                self._gui_config.last_updated = time.time()
                
                if immediate or not self.auto_save:
                    return self._save_to_file()
                else:
                    # Schedule auto-save
                    self._save_pending = True
                    self._last_save_time = time.time()
                    return True
                    
        except Exception as e:
            self.logger.error(f"Failed to save GUI configuration: {e}")
            return False
    
    def _save_to_file(self) -> bool:
        """Save configuration to file (internal method)"""
        try:
            # Load existing configuration
            config_data = {}
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f) or {}
            
            # Update GUI configuration section
            if 'gui_config' not in config_data:
                config_data['gui_config'] = {}
            
            # Convert camera configurations
            camera_configs = []
            for cam_config in self._gui_config.cameras:
                camera_configs.append(asdict(cam_config))
            
            config_data['gui_config']['cameras'] = camera_configs
            config_data['gui_config']['system_parameters'] = asdict(self._gui_config.system_parameters)
            config_data['gui_config']['last_updated'] = self._gui_config.last_updated
            
            # Update camera count in base configuration
            if 'cameras' not in config_data:
                config_data['cameras'] = {}
            
            enabled_count = sum(1 for cam in self._gui_config.cameras if cam.enabled)
            config_data['cameras']['count'] = max(1, enabled_count)  # At least 1 for base system
            
            # Write to file with backup
            backup_file = f"{self.config_file}.backup"
            if os.path.exists(self.config_file):
                os.rename(self.config_file, backup_file)
            
            try:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    yaml.dump(config_data, f, default_flow_style=False, indent=2, allow_unicode=True)
                
                # Remove backup on successful write
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                
                self.logger.debug(f"Configuration saved to {self.config_file}")
                
                # Notify change callbacks
                self._notify_change_callbacks()
                
                return True
                
            except Exception as e:
                # Restore backup on failure
                if os.path.exists(backup_file):
                    os.rename(backup_file, self.config_file)
                raise e
                
        except Exception as e:
            self.logger.error(f"Failed to save configuration to file: {e}")
            return False
    
    def update_camera_configuration(self, camera_configs: List[Dict[str, Any]]) -> bool:
        """
        Update camera configuration and auto-save
        
        Args:
            camera_configs: List of camera configuration dictionaries
            
        Returns:
            bool: True if update was successful
        """
        try:
            if self._gui_config is None:
                self.load_gui_configuration()
            
            # Update camera configurations
            for i, cam_data in enumerate(camera_configs):
                if i < len(self._gui_config.cameras):
                    cam_config = self._gui_config.cameras[i]
                    cam_config.camera_id = cam_data.get('camera_id', cam_config.camera_id)
                    cam_config.enabled = cam_data.get('enabled', cam_config.enabled)
                    cam_config.physical_camera_id = cam_data.get('physical_camera_id', cam_config.physical_camera_id)
                    cam_config.mask_path = cam_data.get('mask_path', cam_config.mask_path)
                    cam_config.baseline_count = cam_data.get('baseline_count', cam_config.baseline_count)
                    cam_config.threshold = cam_data.get('threshold', cam_config.threshold)
            
            # Save configuration
            return self.save_gui_configuration(self._gui_config)
            
        except Exception as e:
            self.logger.error(f"Failed to update camera configuration: {e}")
            return False
    
    def update_system_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Update system parameters and auto-save
        
        Args:
            parameters: Dictionary of system parameters
            
        Returns:
            bool: True if update was successful
        """
        try:
            if self._gui_config is None:
                self.load_gui_configuration()
            
            # Update system parameters
            sys_params = self._gui_config.system_parameters
            sys_params.delay_time = parameters.get('delay_time', sys_params.delay_time)
            sys_params.monitoring_interval = parameters.get('monitoring_interval', sys_params.monitoring_interval)
            sys_params.global_threshold = parameters.get('global_threshold', sys_params.global_threshold)
            
            # Save configuration
            return self.save_gui_configuration(self._gui_config)
            
        except Exception as e:
            self.logger.error(f"Failed to update system parameters: {e}")
            return False
    
    def get_gui_configuration(self) -> GuiConfiguration:
        """
        Get current GUI configuration
        
        Returns:
            GuiConfiguration: Current GUI configuration
        """
        if self._gui_config is None:
            return self.load_gui_configuration()
        return deepcopy(self._gui_config)
    
    def add_change_callback(self, callback: Callable[[GuiConfiguration], None]):
        """
        Add callback to be notified of configuration changes
        
        Args:
            callback: Function to call when configuration changes
        """
        self.change_callbacks.append(callback)
        self.logger.debug(f"Added configuration change callback: {callback.__name__}")
    
    def remove_change_callback(self, callback: Callable[[GuiConfiguration], None]):
        """
        Remove configuration change callback
        
        Args:
            callback: Function to remove from callbacks
        """
        if callback in self.change_callbacks:
            self.change_callbacks.remove(callback)
            self.logger.debug(f"Removed configuration change callback: {callback.__name__}")
    
    def _notify_change_callbacks(self):
        """Notify all change callbacks of configuration update"""
        if self._gui_config:
            for callback in self.change_callbacks:
                try:
                    callback(deepcopy(self._gui_config))
                except Exception as e:
                    self.logger.error(f"Configuration change callback error: {e}")
    
    def export_configuration(self, export_file: str) -> bool:
        """
        Export current configuration to a file
        
        Args:
            export_file: Path to export file
            
        Returns:
            bool: True if export was successful
        """
        try:
            if self._gui_config is None:
                self.load_gui_configuration()
            
            export_data = {
                'gui_config': {
                    'cameras': [asdict(cam) for cam in self._gui_config.cameras],
                    'system_parameters': asdict(self._gui_config.system_parameters),
                    'last_updated': self._gui_config.last_updated,
                    'exported_at': time.time()
                }
            }
            
            with open(export_file, 'w', encoding='utf-8') as f:
                yaml.dump(export_data, f, default_flow_style=False, indent=2, allow_unicode=True)
            
            self.logger.info(f"Configuration exported to {export_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export configuration: {e}")
            return False
    
    def import_configuration(self, import_file: str) -> bool:
        """
        Import configuration from a file
        
        Args:
            import_file: Path to import file
            
        Returns:
            bool: True if import was successful
        """
        try:
            if not os.path.exists(import_file):
                self.logger.error(f"Import file not found: {import_file}")
                return False
            
            with open(import_file, 'r', encoding='utf-8') as f:
                import_data = yaml.safe_load(f)
            
            gui_data = import_data.get('gui_config', {})
            
            # Create configuration from imported data
            cameras = []
            for cam_data in gui_data.get('cameras', []):
                cameras.append(GuiCameraConfig(**cam_data))
            
            # Ensure we have 6 cameras
            while len(cameras) < 6:
                cameras.append(GuiCameraConfig(
                    camera_id=len(cameras),
                    enabled=False,
                    physical_camera_id=len(cameras),
                    mask_path='',
                    baseline_count=0,
                    threshold=2
                ))
            
            sys_params_data = gui_data.get('system_parameters', {})
            system_parameters = GuiSystemParameters(**sys_params_data)
            
            imported_config = GuiConfiguration(
                cameras=cameras,
                system_parameters=system_parameters,
                last_updated=time.time()
            )
            
            # Save imported configuration
            if self.save_gui_configuration(imported_config, immediate=True):
                self.logger.info(f"Configuration imported from {import_file}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to import configuration: {e}")
            return False
    
    def stop(self):
        """Stop the configuration manager and save any pending changes"""
        try:
            # Signal auto-save thread to stop
            if self.save_thread and self.save_thread.is_alive():
                self.save_stop_event.set()
                self.save_thread.join(timeout=2.0)
            
            # Save any pending changes
            with self._config_lock:
                if self._save_pending and self._gui_config:
                    self._save_to_file()
            
            self.logger.info("GUI Configuration Manager stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping GUI Configuration Manager: {e}")
    
    def __del__(self):
        """Cleanup on destruction"""
        self.stop()
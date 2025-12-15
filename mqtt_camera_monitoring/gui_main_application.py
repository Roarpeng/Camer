#!/usr/bin/env python3
"""
Main GUI Application for MQTT Camera Monitoring System
Integrates GUI window with system wrapper and configuration persistence
"""

import sys
import time
import logging
from typing import Optional
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer

from mqtt_camera_monitoring.gui_main_window import MainWindow
from mqtt_camera_monitoring.gui_system_wrapper import GuiSystemWrapper
from mqtt_camera_monitoring.gui_config_manager import GuiConfigManager, GuiConfiguration


class MqttCameraMonitoringApp:
    """Main application class that integrates GUI, system wrapper, and configuration persistence"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.app: Optional[QApplication] = None
        self.main_window: Optional[MainWindow] = None
        self.system_wrapper: Optional[GuiSystemWrapper] = None
        self.config_manager: Optional[GuiConfigManager] = None
        self.status_update_timer: Optional[QTimer] = None
        self.config_file = config_file
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('gui_application.log', encoding='utf-8')
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def initialize(self) -> bool:
        """Initialize the application with configuration persistence"""
        try:
            # Create QApplication
            self.app = QApplication(sys.argv)
            self.app.setApplicationName("MQTT摄像头监控系统")
            self.app.setApplicationVersion("1.0.0")
            
            # Initialize configuration manager with auto-save
            self.config_manager = GuiConfigManager(self.config_file, auto_save=True)
            
            # Load previous configuration on startup
            gui_config = self.config_manager.load_gui_configuration()
            self.logger.info("Previous configuration loaded on startup")
            
            # Create main window
            self.main_window = MainWindow()
            
            # Apply loaded configuration to GUI
            self._apply_configuration_to_gui(gui_config)
            
            # Create system wrapper
            self.system_wrapper = GuiSystemWrapper(self.config_file)
            
            # Connect GUI to system wrapper
            self._connect_gui_to_system()
            
            # Set up configuration change monitoring for real-time auto-save
            self._setup_configuration_auto_save()
            
            # Set up status update timer
            self.status_update_timer = QTimer()
            self.status_update_timer.timeout.connect(self._update_gui_status)
            self.status_update_timer.start(1000)  # Update every second
            
            self.logger.info("Application initialized successfully with configuration persistence")
            return True
            
        except Exception as e:
            self.logger.error(f"Application initialization failed: {e}")
            return False
    
    def _connect_gui_to_system(self):
        """Connect GUI callbacks to system wrapper"""
        try:
            # Get GUI status update methods
            status_methods = self.main_window.get_system_status_methods()
            
            # Set callbacks in system wrapper
            for method_name, method_func in status_methods.items():
                self.system_wrapper.set_status_callback(method_name, method_func)
            
            # Connect GUI configuration changes to system
            self._setup_configuration_monitoring()
            
            self.logger.info("GUI connected to system wrapper")
            
        except Exception as e:
            self.logger.error(f"Failed to connect GUI to system: {e}")
    
    def _setup_configuration_monitoring(self):
        """Set up monitoring for GUI configuration changes"""
        try:
            # Monitor camera configuration changes
            for widget in self.main_window.camera_widgets:
                # Connect enable/disable changes
                widget['enable_checkbox'].toggled.connect(self._on_camera_config_changed)
                
                # Connect mask file changes
                widget['mask_input'].textChanged.connect(self._on_camera_config_changed)
                
                # Connect threshold changes
                widget['threshold_spinbox'].valueChanged.connect(self._on_camera_config_changed)
            
            # Monitor system parameter changes
            if hasattr(self.main_window, 'delay_spinbox'):
                self.main_window.delay_spinbox.valueChanged.connect(self._on_system_params_changed)
            
            if hasattr(self.main_window, 'global_threshold_spinbox'):
                self.main_window.global_threshold_spinbox.valueChanged.connect(self._on_system_params_changed)
            
            if hasattr(self.main_window, 'interval_spinbox'):
                self.main_window.interval_spinbox.valueChanged.connect(self._on_system_params_changed)
            
            self.logger.info("Configuration monitoring set up")
            
        except Exception as e:
            self.logger.error(f"Failed to set up configuration monitoring: {e}")
    
    def _on_camera_config_changed(self):
        """Handle camera configuration changes with auto-save"""
        try:
            # Get current camera configuration from GUI
            camera_configs = self.main_window.get_camera_configuration()
            
            # Save GUI configuration automatically when parameters change
            if self.config_manager:
                self.config_manager.update_camera_configuration(camera_configs)
                self.logger.debug("Camera configuration auto-saved")
            
            # Update system wrapper configuration
            if self.system_wrapper:
                self.system_wrapper.update_camera_configuration(camera_configs)
            
        except Exception as e:
            self.logger.error(f"Camera configuration update failed: {e}")
    
    def _on_system_params_changed(self):
        """Handle system parameter changes with auto-save"""
        try:
            # Get current system parameters from GUI
            system_params = self.main_window.get_system_parameters()
            
            # Save GUI configuration automatically when parameters change
            if self.config_manager:
                self.config_manager.update_system_parameters(system_params)
                self.logger.debug("System parameters auto-saved")
            
            # Update system wrapper parameters
            if self.system_wrapper:
                self.system_wrapper.update_system_parameters(system_params)
            
        except Exception as e:
            self.logger.error(f"System parameter update failed: {e}")
    
    def _update_gui_status(self):
        """Update GUI with current system status"""
        try:
            if self.system_wrapper and self.system_wrapper.is_running():
                # System is running, status updates are handled by the wrapper's monitoring thread
                pass
            else:
                # System is not running, update basic status
                if hasattr(self.main_window, 'update_system_health'):
                    self.main_window.update_system_health(0, 0, False)
        
        except Exception as e:
            self.logger.error(f"GUI status update failed: {e}")
    
    def start_monitoring_system(self) -> bool:
        """Start the monitoring system"""
        try:
            if not self.system_wrapper:
                self.logger.error("System wrapper not initialized")
                return False
            
            # Get current configuration from GUI
            camera_configs = self.main_window.get_camera_configuration()
            system_params = self.main_window.get_system_parameters()
            
            # Validate configuration
            valid, error_msg = self.main_window.validate_camera_configuration()
            if not valid:
                QMessageBox.warning(self.main_window, "配置错误", f"无法启动系统:\n{error_msg}")
                return False
            
            # Configure system wrapper
            if not self.system_wrapper.configure_cameras(camera_configs):
                QMessageBox.critical(self.main_window, "配置错误", "摄像头配置失败")
                return False
            
            if not self.system_wrapper.update_system_parameters(system_params):
                QMessageBox.critical(self.main_window, "配置错误", "系统参数配置失败")
                return False
            
            # Start system
            if self.system_wrapper.start_system():
                self.logger.info("Monitoring system started successfully")
                QMessageBox.information(self.main_window, "系统启动", "监控系统已成功启动")
                return True
            else:
                QMessageBox.critical(self.main_window, "启动失败", "监控系统启动失败，请检查日志")
                return False
        
        except Exception as e:
            error_msg = f"启动监控系统失败: {e}"
            self.logger.error(error_msg)
            QMessageBox.critical(self.main_window, "启动错误", error_msg)
            return False
    
    def stop_monitoring_system(self) -> bool:
        """Stop the monitoring system"""
        try:
            if self.system_wrapper and self.system_wrapper.is_running():
                if self.system_wrapper.stop_system():
                    self.logger.info("Monitoring system stopped successfully")
                    QMessageBox.information(self.main_window, "系统停止", "监控系统已停止")
                    return True
                else:
                    QMessageBox.warning(self.main_window, "停止失败", "监控系统停止失败")
                    return False
            else:
                self.logger.info("Monitoring system is not running")
                return True
        
        except Exception as e:
            error_msg = f"停止监控系统失败: {e}"
            self.logger.error(error_msg)
            QMessageBox.critical(self.main_window, "停止错误", error_msg)
            return False
    
    def show(self):
        """Show the main window"""
        if self.main_window:
            self.main_window.show()
    
    def run(self) -> int:
        """Run the application"""
        try:
            if not self.app:
                return 1
            
            # Show main window
            self.show()
            
            # Add menu bar or buttons for start/stop system
            self._add_system_controls()
            
            # Start event loop
            return self.app.exec()
        
        except Exception as e:
            self.logger.error(f"Application run failed: {e}")
            return 1
    
    def _add_system_controls(self):
        """Add system start/stop controls to the GUI"""
        try:
            # Connect start/stop buttons to system control methods
            if self.main_window:
                # Connect button signals
                if hasattr(self.main_window, 'start_button'):
                    self.main_window.start_button.clicked.connect(self._on_start_system)
                
                if hasattr(self.main_window, 'stop_button'):
                    self.main_window.stop_button.clicked.connect(self._on_stop_system)
                
                # Add system control methods to main window for external access
                self.main_window.start_monitoring_system = self.start_monitoring_system
                self.main_window.stop_monitoring_system = self.stop_monitoring_system
            
        except Exception as e:
            self.logger.error(f"Failed to add system controls: {e}")
    
    def _on_start_system(self):
        """Handle start system button click"""
        try:
            if self.start_monitoring_system():
                # Update button states
                if hasattr(self.main_window, 'update_system_control_status'):
                    self.main_window.update_system_control_status(True)
        except Exception as e:
            self.logger.error(f"Start system button handler failed: {e}")
    
    def _on_stop_system(self):
        """Handle stop system button click"""
        try:
            if self.stop_monitoring_system():
                # Update button states
                if hasattr(self.main_window, 'update_system_control_status'):
                    self.main_window.update_system_control_status(False)
        except Exception as e:
            self.logger.error(f"Stop system button handler failed: {e}")
    
    def _apply_configuration_to_gui(self, gui_config: GuiConfiguration):
        """Apply loaded configuration to GUI elements"""
        try:
            if not self.main_window:
                return
            
            # Apply camera configurations
            camera_configs = []
            for cam_config in gui_config.cameras:
                camera_configs.append({
                    'camera_id': cam_config.camera_id,
                    'enabled': cam_config.enabled,
                    'physical_camera_id': cam_config.physical_camera_id,
                    'mask_path': cam_config.mask_path,
                    'baseline_count': cam_config.baseline_count,
                    'threshold': cam_config.threshold
                })
            
            # Apply to GUI (this method should exist in MainWindow)
            if hasattr(self.main_window, 'apply_camera_configuration'):
                self.main_window.apply_camera_configuration(camera_configs)
            
            # Apply system parameters
            sys_params = {
                'delay_time': gui_config.system_parameters.delay_time,
                'monitoring_interval': gui_config.system_parameters.monitoring_interval,
                'global_threshold': gui_config.system_parameters.global_threshold
            }
            
            # Apply to GUI (this method should exist in MainWindow)
            if hasattr(self.main_window, 'apply_system_parameters'):
                self.main_window.apply_system_parameters(sys_params)
            
            self.logger.info("Configuration applied to GUI successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to apply configuration to GUI: {e}")
    
    def _setup_configuration_auto_save(self):
        """Set up real-time configuration file management (auto-save on parameter changes)"""
        try:
            if not self.config_manager:
                return
            
            # Add configuration change callback for logging
            def on_config_changed(config: GuiConfiguration):
                self.logger.debug(f"Configuration changed and saved at {time.strftime('%H:%M:%S')}")
            
            self.config_manager.add_change_callback(on_config_changed)
            
            # The auto-save is already handled in _on_camera_config_changed and _on_system_params_changed
            # This method sets up any additional auto-save monitoring
            
            self.logger.info("Real-time configuration file management set up")
            
        except Exception as e:
            self.logger.error(f"Failed to set up configuration auto-save: {e}")
    
    def save_configuration_now(self) -> bool:
        """Save current GUI configuration immediately"""
        try:
            if not self.config_manager or not self.main_window:
                return False
            
            # Get current configuration from GUI
            camera_configs = self.main_window.get_camera_configuration()
            system_params = self.main_window.get_system_parameters()
            
            # Update and save immediately
            self.config_manager.update_camera_configuration(camera_configs)
            self.config_manager.update_system_parameters(system_params)
            
            # Force immediate save
            current_config = self.config_manager.get_gui_configuration()
            return self.config_manager.save_gui_configuration(current_config, immediate=True)
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration immediately: {e}")
            return False
    
    def export_configuration(self, export_file: str) -> bool:
        """Export current configuration to file"""
        try:
            if not self.config_manager:
                return False
            
            return self.config_manager.export_configuration(export_file)
            
        except Exception as e:
            self.logger.error(f"Failed to export configuration: {e}")
            return False
    
    def import_configuration(self, import_file: str) -> bool:
        """Import configuration from file and apply to GUI"""
        try:
            if not self.config_manager:
                return False
            
            # Import configuration
            if self.config_manager.import_configuration(import_file):
                # Reload and apply to GUI
                gui_config = self.config_manager.get_gui_configuration()
                self._apply_configuration_to_gui(gui_config)
                
                self.logger.info(f"Configuration imported and applied from {import_file}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to import configuration: {e}")
            return False
    
    def quit(self):
        """Quit the application with proper configuration cleanup"""
        try:
            # Save any pending configuration changes
            if self.config_manager:
                self.save_configuration_now()
                self.config_manager.stop()
            
            # Stop monitoring system if running
            if self.system_wrapper and self.system_wrapper.is_running():
                self.system_wrapper.stop_system()
            
            # Stop status update timer
            if self.status_update_timer:
                self.status_update_timer.stop()
            
            # Quit application
            if self.app:
                self.app.quit()
            
            self.logger.info("Application quit with configuration saved")
        
        except Exception as e:
            self.logger.error(f"Application quit failed: {e}")


def main(config_file: str = "config.yaml"):
    """Main entry point with configuration file support"""
    print("启动MQTT摄像头监控GUI应用程序...")
    
    # Create and initialize application with configuration persistence
    app = MqttCameraMonitoringApp(config_file)
    
    if not app.initialize():
        print("应用程序初始化失败")
        return 1
    
    # Run application
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
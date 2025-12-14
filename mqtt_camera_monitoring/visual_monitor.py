"""
Enhanced Visual Monitor Component

Displays 6 independent camera feeds with individual parameter controls and real-time log display.
Provides comprehensive visual feedback for red light detection and system status.
"""

import cv2
import numpy as np
import logging
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from .config import VisualMonitorConfig
from .camera_manager import CameraFrame
from .light_detector import RedLightDetection


@dataclass
class CameraSettings:
    """Individual camera settings"""
    camera_id: int
    brightness: int = 50
    exposure: int = 100
    contrast: int = 50
    saturation: int = 50
    auto_exposure: bool = True
    enabled: bool = True


@dataclass
class DisplayWindow:
    """Represents a display window for a camera feed"""
    camera_id: int
    window_name: str
    is_active: bool
    last_update: float
    settings: CameraSettings
    error_message: Optional[str] = None
    baseline_count: int = 0
    baseline_area: float = 0.0
    current_count: int = 0
    current_area: float = 0.0


@dataclass
class LogEntry:
    """Log entry for the monitoring system"""
    timestamp: datetime
    camera_id: Optional[int]
    level: str
    message: str
    details: Optional[Dict[str, Any]] = None


class EnhancedVisualMonitor:
    """Enhanced visual monitor with 6 independent camera windows and real-time log display"""
    
    def __init__(self, config: VisualMonitorConfig, camera_count: int = 6):
        """
        Initialize enhanced visual monitor
        
        Args:
            config: Visual monitor configuration
            camera_count: Number of cameras to monitor (fixed at 6)
        """
        self.config = config
        self.camera_count = 6  # Fixed at 6 cameras
        self.logger = logging.getLogger(__name__)
        
        # Display windows
        self.windows: List[DisplayWindow] = []
        self.display_active = False
        self.display_lock = threading.Lock()
        
        # Camera settings
        self.camera_settings: Dict[int, CameraSettings] = {}
        
        # Log system
        self.log_entries: List[LogEntry] = []
        self.log_lock = threading.Lock()
        self.max_log_entries = 1000
        
        # GUI components
        self.control_window = None
        self.log_text_widget = None
        self.camera_controls = {}
        self.gui_thread = None
        self.gui_active = False
        
        # Error handling
        self.error_font = cv2.FONT_HERSHEY_SIMPLEX
        self.error_font_scale = 0.7
        self.error_color = (0, 0, 255)  # Red color for errors
        
        # Initialize camera settings
        self._initialize_camera_settings()
        
        self.logger.info(f"EnhancedVisualMonitor initialized for {self.camera_count} cameras")
    
    def _initialize_camera_settings(self) -> None:
        """Initialize default settings for all cameras"""
        for camera_id in range(self.camera_count):
            self.camera_settings[camera_id] = CameraSettings(
                camera_id=camera_id,
                brightness=50,
                exposure=100,
                contrast=50,
                saturation=50,
                auto_exposure=True,
                enabled=True
            )
    
    def add_log_entry(self, level: str, message: str, camera_id: Optional[int] = None, 
                     details: Optional[Dict[str, Any]] = None) -> None:
        """Add a log entry to the monitoring log"""
        with self.log_lock:
            entry = LogEntry(
                timestamp=datetime.now(),
                camera_id=camera_id,
                level=level,
                message=message,
                details=details
            )
            self.log_entries.append(entry)
            
            # Keep only recent entries
            if len(self.log_entries) > self.max_log_entries:
                self.log_entries = self.log_entries[-self.max_log_entries:]
            
            # Update GUI log display if active
            if self.gui_active and self.log_text_widget:
                self._update_log_display()
    
    def _update_log_display(self) -> None:
        """Update the log display in the GUI"""
        try:
            if not self.log_text_widget:
                return
            
            # Get recent log entries
            recent_entries = self.log_entries[-50:]  # Show last 50 entries
            
            # Clear and update log display
            self.log_text_widget.delete(1.0, tk.END)
            
            for entry in recent_entries:
                timestamp_str = entry.timestamp.strftime("%H:%M:%S")
                camera_str = f"[Cam{entry.camera_id}]" if entry.camera_id is not None else "[SYS]"
                level_str = f"[{entry.level}]"
                
                log_line = f"{timestamp_str} {camera_str} {level_str} {entry.message}\n"
                
                # Add color coding based on level
                if entry.level == "ERROR":
                    self.log_text_widget.insert(tk.END, log_line, "error")
                elif entry.level == "WARNING":
                    self.log_text_widget.insert(tk.END, log_line, "warning")
                elif entry.level == "INFO":
                    self.log_text_widget.insert(tk.END, log_line, "info")
                else:
                    self.log_text_widget.insert(tk.END, log_line)
            
            # Auto-scroll to bottom
            self.log_text_widget.see(tk.END)
            
        except Exception as e:
            self.logger.error(f"Error updating log display: {e}")
    
    def _create_control_gui(self) -> None:
        """Create the control GUI with camera settings and log display"""
        try:
            self.control_window = tk.Tk()
            self.control_window.title("MQTT摄像头监控系统 - 控制面板")
            self.control_window.geometry("800x600")
            
            # Create main frame
            main_frame = ttk.Frame(self.control_window)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Create notebook for tabs
            notebook = ttk.Notebook(main_frame)
            notebook.pack(fill=tk.BOTH, expand=True)
            
            # Camera controls tab
            camera_frame = ttk.Frame(notebook)
            notebook.add(camera_frame, text="摄像头控制")
            self._create_camera_controls(camera_frame)
            
            # Log display tab
            log_frame = ttk.Frame(notebook)
            notebook.add(log_frame, text="系统日志")
            self._create_log_display(log_frame)
            
            # Status tab
            status_frame = ttk.Frame(notebook)
            notebook.add(status_frame, text="系统状态")
            self._create_status_display(status_frame)
            
            self.gui_active = True
            
            # Configure log text colors
            if self.log_text_widget:
                self.log_text_widget.tag_config("error", foreground="red")
                self.log_text_widget.tag_config("warning", foreground="orange")
                self.log_text_widget.tag_config("info", foreground="blue")
            
            # Start GUI update loop
            self._gui_update_loop()
            
        except Exception as e:
            self.logger.error(f"Error creating control GUI: {e}")
    
    def _create_camera_controls(self, parent: ttk.Frame) -> None:
        """Create camera control widgets"""
        # Create scrollable frame
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create controls for each camera
        for camera_id in range(self.camera_count):
            self._create_single_camera_control(scrollable_frame, camera_id)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _create_single_camera_control(self, parent: ttk.Frame, camera_id: int) -> None:
        """Create control widgets for a single camera"""
        # Camera frame
        camera_frame = ttk.LabelFrame(parent, text=f"摄像头 {camera_id}", padding=10)
        camera_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Store control variables
        self.camera_controls[camera_id] = {}
        
        # Enable/Disable checkbox
        enabled_var = tk.BooleanVar(value=self.camera_settings[camera_id].enabled)
        enabled_check = ttk.Checkbutton(camera_frame, text="启用", variable=enabled_var,
                                       command=lambda: self._update_camera_setting(camera_id, 'enabled', enabled_var.get()))
        enabled_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)
        self.camera_controls[camera_id]['enabled'] = enabled_var
        
        # Brightness control
        ttk.Label(camera_frame, text="亮度:").grid(row=1, column=0, sticky=tk.W, pady=2)
        brightness_var = tk.IntVar(value=self.camera_settings[camera_id].brightness)
        brightness_scale = ttk.Scale(camera_frame, from_=0, to=100, variable=brightness_var, orient=tk.HORIZONTAL,
                                    command=lambda v: self._update_camera_setting(camera_id, 'brightness', int(float(v))))
        brightness_scale.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)
        brightness_label = ttk.Label(camera_frame, text=str(brightness_var.get()))
        brightness_label.grid(row=1, column=2, pady=2)
        self.camera_controls[camera_id]['brightness'] = (brightness_var, brightness_label)
        
        # Exposure control
        ttk.Label(camera_frame, text="曝光:").grid(row=2, column=0, sticky=tk.W, pady=2)
        exposure_var = tk.IntVar(value=self.camera_settings[camera_id].exposure)
        exposure_scale = ttk.Scale(camera_frame, from_=10, to=500, variable=exposure_var, orient=tk.HORIZONTAL,
                                  command=lambda v: self._update_camera_setting(camera_id, 'exposure', int(float(v))))
        exposure_scale.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=2)
        exposure_label = ttk.Label(camera_frame, text=str(exposure_var.get()))
        exposure_label.grid(row=2, column=2, pady=2)
        self.camera_controls[camera_id]['exposure'] = (exposure_var, exposure_label)
        
        # Contrast control
        ttk.Label(camera_frame, text="对比度:").grid(row=3, column=0, sticky=tk.W, pady=2)
        contrast_var = tk.IntVar(value=self.camera_settings[camera_id].contrast)
        contrast_scale = ttk.Scale(camera_frame, from_=0, to=100, variable=contrast_var, orient=tk.HORIZONTAL,
                                  command=lambda v: self._update_camera_setting(camera_id, 'contrast', int(float(v))))
        contrast_scale.grid(row=3, column=1, sticky=tk.EW, padx=5, pady=2)
        contrast_label = ttk.Label(camera_frame, text=str(contrast_var.get()))
        contrast_label.grid(row=3, column=2, pady=2)
        self.camera_controls[camera_id]['contrast'] = (contrast_var, contrast_label)
        
        # Saturation control
        ttk.Label(camera_frame, text="饱和度:").grid(row=4, column=0, sticky=tk.W, pady=2)
        saturation_var = tk.IntVar(value=self.camera_settings[camera_id].saturation)
        saturation_scale = ttk.Scale(camera_frame, from_=0, to=100, variable=saturation_var, orient=tk.HORIZONTAL,
                                    command=lambda v: self._update_camera_setting(camera_id, 'saturation', int(float(v))))
        saturation_scale.grid(row=4, column=1, sticky=tk.EW, padx=5, pady=2)
        saturation_label = ttk.Label(camera_frame, text=str(saturation_var.get()))
        saturation_label.grid(row=4, column=2, pady=2)
        self.camera_controls[camera_id]['saturation'] = (saturation_var, saturation_label)
        
        # Auto exposure checkbox
        auto_exp_var = tk.BooleanVar(value=self.camera_settings[camera_id].auto_exposure)
        auto_exp_check = ttk.Checkbutton(camera_frame, text="自动曝光", variable=auto_exp_var,
                                        command=lambda: self._update_camera_setting(camera_id, 'auto_exposure', auto_exp_var.get()))
        auto_exp_check.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=2)
        self.camera_controls[camera_id]['auto_exposure'] = auto_exp_var
        
        # Status labels
        status_frame = ttk.Frame(camera_frame)
        status_frame.grid(row=6, column=0, columnspan=3, sticky=tk.EW, pady=5)
        
        ttk.Label(status_frame, text="基线计数:").grid(row=0, column=0, sticky=tk.W)
        baseline_count_label = ttk.Label(status_frame, text="0", foreground="blue")
        baseline_count_label.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(status_frame, text="当前计数:").grid(row=0, column=2, sticky=tk.W, padx=10)
        current_count_label = ttk.Label(status_frame, text="0", foreground="green")
        current_count_label.grid(row=0, column=3, sticky=tk.W, padx=5)
        
        ttk.Label(status_frame, text="基线面积:").grid(row=1, column=0, sticky=tk.W)
        baseline_area_label = ttk.Label(status_frame, text="0.0", foreground="blue")
        baseline_area_label.grid(row=1, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(status_frame, text="当前面积:").grid(row=1, column=2, sticky=tk.W, padx=10)
        current_area_label = ttk.Label(status_frame, text="0.0", foreground="green")
        current_area_label.grid(row=1, column=3, sticky=tk.W, padx=5)
        
        self.camera_controls[camera_id]['status'] = {
            'baseline_count': baseline_count_label,
            'current_count': current_count_label,
            'baseline_area': baseline_area_label,
            'current_area': current_area_label
        }
        
        # Configure column weights
        camera_frame.columnconfigure(1, weight=1)
    
    def _create_log_display(self, parent: ttk.Frame) -> None:
        """Create log display widget"""
        # Log display frame
        log_frame = ttk.Frame(parent)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Log text widget with scrollbar
        self.log_text_widget = scrolledtext.ScrolledText(log_frame, height=20, width=80)
        self.log_text_widget.pack(fill=tk.BOTH, expand=True)
        
        # Control buttons
        button_frame = ttk.Frame(log_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(button_frame, text="清空日志", command=self._clear_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="导出日志", command=self._export_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="刷新", command=self._update_log_display).pack(side=tk.LEFT, padx=5)
    
    def _create_status_display(self, parent: ttk.Frame) -> None:
        """Create system status display"""
        # Status display frame
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # System status
        system_frame = ttk.LabelFrame(status_frame, text="系统状态", padding=10)
        system_frame.pack(fill=tk.X, pady=5)
        
        self.status_labels = {}
        
        # MQTT status
        ttk.Label(system_frame, text="MQTT连接:").grid(row=0, column=0, sticky=tk.W, pady=2)
        mqtt_status_label = ttk.Label(system_frame, text="未知", foreground="gray")
        mqtt_status_label.grid(row=0, column=1, sticky=tk.W, padx=10, pady=2)
        self.status_labels['mqtt'] = mqtt_status_label
        
        # Camera status
        ttk.Label(system_frame, text="活跃摄像头:").grid(row=1, column=0, sticky=tk.W, pady=2)
        camera_status_label = ttk.Label(system_frame, text="0/6", foreground="gray")
        camera_status_label.grid(row=1, column=1, sticky=tk.W, padx=10, pady=2)
        self.status_labels['cameras'] = camera_status_label
        
        # Detection status
        ttk.Label(system_frame, text="检测状态:").grid(row=2, column=0, sticky=tk.W, pady=2)
        detection_status_label = ttk.Label(system_frame, text="待机", foreground="gray")
        detection_status_label.grid(row=2, column=1, sticky=tk.W, padx=10, pady=2)
        self.status_labels['detection'] = detection_status_label
        
        # Trigger count
        ttk.Label(system_frame, text="触发次数:").grid(row=3, column=0, sticky=tk.W, pady=2)
        trigger_count_label = ttk.Label(system_frame, text="0", foreground="blue")
        trigger_count_label.grid(row=3, column=1, sticky=tk.W, padx=10, pady=2)
        self.status_labels['trigger_count'] = trigger_count_label
        
        system_frame.columnconfigure(1, weight=1)
    
    def _update_camera_setting(self, camera_id: int, setting: str, value: Any) -> None:
        """Update camera setting and apply to hardware"""
        try:
            if camera_id in self.camera_settings:
                setattr(self.camera_settings[camera_id], setting, value)
                
                # Update label if it's a numeric setting
                if setting in ['brightness', 'exposure', 'contrast', 'saturation']:
                    if camera_id in self.camera_controls:
                        control_tuple = self.camera_controls[camera_id].get(setting)
                        if control_tuple and len(control_tuple) > 1:
                            control_tuple[1].config(text=str(value))
                
                # Log the change
                self.add_log_entry("INFO", f"摄像头{camera_id} {setting}设置为{value}", camera_id)
                
                # TODO: Apply setting to actual camera hardware
                # This would be implemented in the camera manager
                
        except Exception as e:
            self.logger.error(f"Error updating camera {camera_id} setting {setting}: {e}")
            self.add_log_entry("ERROR", f"更新摄像头{camera_id}设置失败: {e}", camera_id)
    
    def _clear_log(self) -> None:
        """Clear the log display"""
        with self.log_lock:
            self.log_entries.clear()
        if self.log_text_widget:
            self.log_text_widget.delete(1.0, tk.END)
        self.add_log_entry("INFO", "日志已清空")
    
    def _export_log(self) -> None:
        """Export log to file"""
        try:
            filename = f"camera_monitor_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                for entry in self.log_entries:
                    timestamp_str = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    camera_str = f"[Cam{entry.camera_id}]" if entry.camera_id is not None else "[SYS]"
                    f.write(f"{timestamp_str} {camera_str} [{entry.level}] {entry.message}\n")
            
            self.add_log_entry("INFO", f"日志已导出到 {filename}")
            
        except Exception as e:
            self.logger.error(f"Error exporting log: {e}")
            self.add_log_entry("ERROR", f"导出日志失败: {e}")
    
    def _gui_update_loop(self) -> None:
        """GUI update loop"""
        try:
            if self.gui_active and self.control_window:
                # Update status displays
                self._update_status_display()
                
                # Update camera status in controls
                self._update_camera_status_display()
                
                # Schedule next update
                self.control_window.after(1000, self._gui_update_loop)
                
        except Exception as e:
            self.logger.error(f"Error in GUI update loop: {e}")
    
    def _update_status_display(self) -> None:
        """Update system status display"""
        try:
            if not self.status_labels:
                return
            
            # Update MQTT status (placeholder)
            self.status_labels['mqtt'].config(text="已连接", foreground="green")
            
            # Update camera status
            active_cameras = sum(1 for w in self.windows if w.is_active)
            self.status_labels['cameras'].config(text=f"{active_cameras}/{self.camera_count}", 
                                               foreground="green" if active_cameras > 0 else "red")
            
            # Update detection status (placeholder)
            self.status_labels['detection'].config(text="监控中", foreground="green")
            
        except Exception as e:
            self.logger.error(f"Error updating status display: {e}")
    
    def _update_camera_status_display(self) -> None:
        """Update camera status in control panel"""
        try:
            for camera_id, window in enumerate(self.windows):
                if camera_id in self.camera_controls and 'status' in self.camera_controls[camera_id]:
                    status_controls = self.camera_controls[camera_id]['status']
                    
                    # Update baseline and current values
                    status_controls['baseline_count'].config(text=str(window.baseline_count))
                    status_controls['current_count'].config(text=str(window.current_count))
                    status_controls['baseline_area'].config(text=f"{window.baseline_area:.1f}")
                    status_controls['current_area'].config(text=f"{window.current_area:.1f}")
                    
        except Exception as e:
            self.logger.error(f"Error updating camera status display: {e}")

    def create_windows(self) -> bool:
        """
        Initialize 6 independent display windows and control GUI
        
        Returns:
            bool: True if windows created successfully, False otherwise
        """
        try:
            self.logger.info(f"Creating enhanced display system with {self.camera_count} cameras")
            
            with self.display_lock:
                # Clear existing windows (simplified)
                if self.windows:
                    cv2.destroyAllWindows()
                    self.windows.clear()
                
                # Create windows for each camera
                for camera_id in range(self.camera_count):
                    try:
                        window_name = f"摄像头 {camera_id}"
                        
                        # Create OpenCV window
                        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
                        cv2.resizeWindow(window_name, self.config.window_width, self.config.window_height)
                        
                        # Position windows in a 3x2 grid layout
                        cols = 3  # 3 columns for 6 cameras (2 rows)
                        row = camera_id // cols
                        col = camera_id % cols
                        x_pos = col * (self.config.window_width + 10)
                        y_pos = row * (self.config.window_height + 50)
                        cv2.moveWindow(window_name, x_pos, y_pos)
                        
                        # Create display window object with enhanced features
                        display_window = DisplayWindow(
                            camera_id=camera_id,
                            window_name=window_name,
                            is_active=True,
                            last_update=time.time(),
                            settings=self.camera_settings[camera_id]
                        )
                        
                        self.windows.append(display_window)
                        
                        # Show simple initial placeholder
                        placeholder = self._create_simple_placeholder_frame(camera_id, "初始化中...")
                        cv2.imshow(window_name, placeholder)
                        
                        self.logger.debug(f"Created enhanced window for camera {camera_id}")
                        
                    except Exception as e:
                        self.logger.error(f"Error creating window for camera {camera_id}: {e}")
                        continue
                
                self.display_active = True
                cv2.waitKey(1)  # Process window events
                
                self.logger.info("Enhanced display system created successfully")
                
                # Start control GUI in separate thread (non-blocking)
                try:
                    self.gui_thread = threading.Thread(target=self._start_gui, daemon=True)
                    self.gui_thread.start()
                    self.logger.info("Control GUI thread started")
                except Exception as e:
                    self.logger.warning(f"Failed to start GUI thread: {e}")
                    # Continue without GUI - OpenCV windows will still work
                
                return len(self.windows) > 0
                
        except Exception as e:
            self.logger.error(f"Error creating enhanced display windows: {e}")
            return False
    
    def _create_simple_placeholder_frame(self, camera_id: int, message: str) -> np.ndarray:
        """Create simple placeholder frame"""
        frame = np.zeros((self.config.window_height, self.config.window_width, 3), dtype=np.uint8)
        
        # Simple colored background
        colors = [(100, 50, 50), (50, 100, 50), (50, 50, 100), 
                 (100, 100, 50), (100, 50, 100), (50, 100, 100)]
        frame[:] = colors[camera_id % len(colors)]
        
        # Add camera ID
        cv2.putText(frame, f"Camera {camera_id}", (50, self.config.window_height//2), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
        
        # Add message
        cv2.putText(frame, message, (50, self.config.window_height//2 + 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 1)
        
        return frame
    
    def _start_gui(self) -> None:
        """Start the GUI in a separate thread"""
        try:
            # 延迟启动GUI，确保OpenCV窗口先创建
            time.sleep(1)
            self._create_control_gui()
            if self.control_window:
                self.control_window.mainloop()
        except Exception as e:
            self.logger.error(f"Error in GUI thread: {e}")
            try:
                self.add_log_entry("ERROR", f"控制界面错误: {e}")
            except:
                pass  # 如果日志系统也有问题，就忽略
        finally:
            self.gui_active = False
    
    def update_display(self, frames: List[Optional[CameraFrame]], 
                      detection_results: Optional[List[Optional[RedLightDetection]]] = None) -> bool:
        """
        Update display with frames and green box overlays
        
        Args:
            frames: List of camera frames to display
            detection_results: Optional list of detection results for overlays
            
        Returns:
            bool: True if display updated successfully, False otherwise
        """
        if not self.display_active:
            self.logger.warning("Display not active, cannot update")
            return False
        
        try:
            with self.display_lock:
                current_time = time.time()
                
                for camera_id in range(min(len(self.windows), len(frames))):
                    window = self.windows[camera_id]
                    frame = frames[camera_id]
                    
                    if not window.is_active:
                        continue
                    
                    try:
                        # Get detection result for this camera
                        detection = None
                        if detection_results and camera_id < len(detection_results):
                            detection = detection_results[camera_id]
                        
                        # Create display frame
                        if frame and frame.is_valid and frame.frame is not None:
                            display_frame = self._create_display_frame(frame, detection)
                            window.error_message = None
                        else:
                            # Create error frame
                            error_msg = "Camera disconnected" if frame is None else "Invalid frame"
                            display_frame = self._create_error_frame(camera_id, error_msg)
                            window.error_message = error_msg
                        
                        # Update window
                        cv2.imshow(window.window_name, display_frame)
                        window.last_update = current_time
                        
                    except Exception as e:
                        self.logger.error(f"Error updating display for camera {camera_id}: {e}")
                        error_frame = self._create_error_frame(camera_id, f"Display error: {str(e)}")
                        cv2.imshow(window.window_name, error_frame)
                        window.error_message = str(e)
                
                # Process window events
                cv2.waitKey(1)
                return True
                
        except Exception as e:
            self.logger.error(f"Error updating display: {e}")
            return False
    
    def update_camera_detection_data(self, camera_id: int, baseline_count: int = 0, 
                                   baseline_area: float = 0.0, current_count: int = 0, 
                                   current_area: float = 0.0) -> None:
        """Update camera detection data for display"""
        if camera_id < len(self.windows):
            window = self.windows[camera_id]
            window.baseline_count = baseline_count
            window.baseline_area = baseline_area
            window.current_count = current_count
            window.current_area = current_area
            
            # Log significant changes
            if current_count != baseline_count or abs(current_area - baseline_area) > baseline_area * 0.1:
                self.add_log_entry("INFO", 
                    f"检测变化 - 计数: {baseline_count}→{current_count}, 面积: {baseline_area:.1f}→{current_area:.1f}",
                    camera_id)

    def _create_display_frame(self, camera_frame: CameraFrame, 
                             detection: Optional[RedLightDetection] = None) -> np.ndarray:
        """
        Create display frame with detection overlays
        
        Args:
            camera_frame: Camera frame to display
            detection: Optional detection results for overlays
            
        Returns:
            np.ndarray: Frame with overlays
        """
        # Copy frame to avoid modifying original
        display_frame = camera_frame.frame.copy()
        
        # Add detection overlays if enabled and detection available
        if self.config.show_detection_boxes and detection:
            self._draw_detection_overlays(display_frame, detection)
        
        # Add camera ID and timestamp
        self._add_frame_info(display_frame, camera_frame)
        
        return display_frame
    
    def _draw_detection_overlays(self, frame: np.ndarray, detection: RedLightDetection) -> None:
        """
        Draw green bounding boxes around detected red lights
        
        Args:
            frame: Frame to draw on (modified in place)
            detection: Detection results with bounding boxes
        """
        box_color = tuple(self.config.box_color)  # Convert list to tuple for OpenCV
        thickness = self.config.box_thickness
        
        # Draw bounding boxes
        for x, y, w, h in detection.bounding_boxes:
            # Draw rectangle
            cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, thickness)
            
            # Add detection info text
            info_text = f"Red Light"
            text_size = cv2.getTextSize(info_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            
            # Position text above the box
            text_x = x
            text_y = max(y - 5, text_size[1] + 5)
            
            # Draw text background
            cv2.rectangle(frame, 
                         (text_x, text_y - text_size[1] - 2), 
                         (text_x + text_size[0] + 4, text_y + 2), 
                         box_color, -1)
            
            # Draw text
            cv2.putText(frame, info_text, (text_x + 2, text_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        # Add detection summary
        summary_text = f"Detected: {detection.count} lights, Area: {detection.total_area:.0f}"
        cv2.putText(frame, summary_text, (10, frame.shape[0] - 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 1)
    
    def _add_frame_info(self, frame: np.ndarray, camera_frame: CameraFrame) -> None:
        """
        Add enhanced camera info and settings to frame
        
        Args:
            frame: Frame to add info to (modified in place)
            camera_frame: Camera frame with metadata
        """
        camera_id = camera_frame.camera_id
        settings = self.camera_settings.get(camera_id, CameraSettings(camera_id))
        
        # Camera ID (top left)
        camera_text = f"摄像头 {camera_id}"
        cv2.putText(frame, camera_text, (10, 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Camera settings (top right)
        settings_text = f"亮度:{settings.brightness} 曝光:{settings.exposure}"
        settings_size = cv2.getTextSize(settings_text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
        cv2.putText(frame, settings_text, (frame.shape[1] - settings_size[0] - 10, 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        
        # Detection info (if available)
        if camera_id < len(self.windows):
            window = self.windows[camera_id]
            detection_text = f"基线:{window.baseline_count}/{window.baseline_area:.0f} 当前:{window.current_count}/{window.current_area:.0f}"
            cv2.putText(frame, detection_text, (10, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 255, 255), 1)
        
        # Timestamp (bottom left)
        timestamp_text = f"{time.strftime('%H:%M:%S', time.localtime(camera_frame.timestamp))}"
        cv2.putText(frame, timestamp_text, (10, frame.shape[0] - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Status indicator (bottom right)
        status_color = (0, 255, 0) if camera_frame.is_valid else (0, 0, 255)
        status_text = "在线" if camera_frame.is_valid else "错误"
        status_size = cv2.getTextSize(status_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
        cv2.putText(frame, status_text, (frame.shape[1] - status_size[0] - 10, frame.shape[0] - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, status_color, 2)
        
        # Enabled/Disabled indicator
        if not settings.enabled:
            disabled_text = "已禁用"
            disabled_size = cv2.getTextSize(disabled_text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
            disabled_x = (frame.shape[1] - disabled_size[0]) // 2
            disabled_y = (frame.shape[0] + disabled_size[1]) // 2
            
            # Add semi-transparent overlay
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
            
            cv2.putText(frame, disabled_text, (disabled_x, disabled_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
    
    def _create_enhanced_placeholder_frame(self, camera_id: int, message: str) -> np.ndarray:
        """
        Create enhanced placeholder frame with camera settings info
        
        Args:
            camera_id: Camera identifier
            message: Message to display
            
        Returns:
            np.ndarray: Enhanced placeholder frame
        """
        # Create dark frame
        frame = np.zeros((self.config.window_height, self.config.window_width, 3), dtype=np.uint8)
        frame[:] = (20, 20, 20)  # Dark gray background
        
        # Get camera settings
        settings = self.camera_settings.get(camera_id, CameraSettings(camera_id))
        
        # Add camera ID (large text)
        camera_text = f"摄像头 {camera_id}"
        text_size = cv2.getTextSize(camera_text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 2)[0]
        text_x = (frame.shape[1] - text_size[0]) // 2
        text_y = 60
        cv2.putText(frame, camera_text, (text_x, text_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
        
        # Add status message
        msg_size = cv2.getTextSize(message, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 1)[0]
        msg_x = (frame.shape[1] - msg_size[0]) // 2
        msg_y = text_y + 40
        cv2.putText(frame, message, (msg_x, msg_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
        
        # Add camera settings info
        y_offset = msg_y + 50
        settings_info = [
            f"亮度: {settings.brightness}",
            f"曝光: {settings.exposure}ms",
            f"对比度: {settings.contrast}",
            f"饱和度: {settings.saturation}",
            f"自动曝光: {'开' if settings.auto_exposure else '关'}",
            f"状态: {'启用' if settings.enabled else '禁用'}"
        ]
        
        for i, info in enumerate(settings_info):
            info_size = cv2.getTextSize(info, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            info_x = (frame.shape[1] - info_size[0]) // 2
            info_y = y_offset + i * 25
            
            if info_y < frame.shape[0] - 20:  # Make sure text fits in frame
                color = (100, 255, 100) if settings.enabled else (100, 100, 255)
                cv2.putText(frame, info, (info_x, info_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        return frame

    def _create_placeholder_frame(self, camera_id: int, message: str) -> np.ndarray:
        """
        Create placeholder frame with message
        
        Args:
            camera_id: Camera identifier
            message: Message to display
            
        Returns:
            np.ndarray: Placeholder frame
        """
        # Create black frame
        frame = np.zeros((self.config.window_height, self.config.window_width, 3), dtype=np.uint8)
        
        # Add camera ID
        camera_text = f"Camera {camera_id}"
        text_size = cv2.getTextSize(camera_text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
        text_x = (frame.shape[1] - text_size[0]) // 2
        text_y = frame.shape[0] // 2 - 20
        cv2.putText(frame, camera_text, (text_x, text_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        
        # Add message
        msg_size = cv2.getTextSize(message, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 1)[0]
        msg_x = (frame.shape[1] - msg_size[0]) // 2
        msg_y = frame.shape[0] // 2 + 20
        cv2.putText(frame, message, (msg_x, msg_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
        
        return frame
    
    def _create_error_frame(self, camera_id: int, error_message: str) -> np.ndarray:
        """
        Create error frame with error indicator
        
        Args:
            camera_id: Camera identifier
            error_message: Error message to display
            
        Returns:
            np.ndarray: Error frame
        """
        # Create dark red frame
        frame = np.full((self.config.window_height, self.config.window_width, 3), 
                       (0, 0, 50), dtype=np.uint8)
        
        # Add camera ID
        camera_text = f"Camera {camera_id}"
        text_size = cv2.getTextSize(camera_text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
        text_x = (frame.shape[1] - text_size[0]) // 2
        text_y = frame.shape[0] // 2 - 40
        cv2.putText(frame, camera_text, (text_x, text_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        
        # Add ERROR indicator
        error_text = "ERROR"
        error_size = cv2.getTextSize(error_text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)[0]
        error_x = (frame.shape[1] - error_size[0]) // 2
        error_y = frame.shape[0] // 2
        cv2.putText(frame, error_text, (error_x, error_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, self.error_color, 3)
        
        # Add error message
        if len(error_message) > 30:
            error_message = error_message[:27] + "..."
        
        msg_size = cv2.getTextSize(error_message, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)[0]
        msg_x = (frame.shape[1] - msg_size[0]) // 2
        msg_y = frame.shape[0] // 2 + 30
        cv2.putText(frame, error_message, (msg_x, msg_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        return frame
    
    def show_error(self, camera_id: int, error_msg: str) -> bool:
        """
        Display error indicator for failed camera
        
        Args:
            camera_id: Camera identifier
            error_msg: Error message to display
            
        Returns:
            bool: True if error displayed successfully, False otherwise
        """
        if not self.display_active or camera_id >= len(self.windows):
            return False
        
        try:
            with self.display_lock:
                window = self.windows[camera_id]
                window.error_message = error_msg
                
                # Create and display error frame
                error_frame = self._create_error_frame(camera_id, error_msg)
                cv2.imshow(window.window_name, error_frame)
                cv2.waitKey(1)
                
                self.logger.warning(f"Error displayed for camera {camera_id}: {error_msg}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error showing error for camera {camera_id}: {e}")
            return False
    
    def update_single_camera(self, camera_id: int, frame: Optional[CameraFrame], 
                           detection: Optional[RedLightDetection] = None) -> bool:
        """
        Update display for a single camera
        
        Args:
            camera_id: Camera identifier
            frame: Camera frame to display
            detection: Optional detection results
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        if not self.display_active or camera_id >= len(self.windows):
            return False
        
        try:
            with self.display_lock:
                window = self.windows[camera_id]
                
                if not window.is_active:
                    return False
                
                # Create display frame
                if frame and frame.is_valid and frame.frame is not None:
                    display_frame = self._create_display_frame(frame, detection)
                    window.error_message = None
                else:
                    error_msg = "Camera disconnected" if frame is None else "Invalid frame"
                    display_frame = self._create_error_frame(camera_id, error_msg)
                    window.error_message = error_msg
                
                # Update window
                cv2.imshow(window.window_name, display_frame)
                window.last_update = time.time()
                cv2.waitKey(1)
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error updating single camera display {camera_id}: {e}")
            return False
    
    def close_windows(self) -> None:
        """
        Clean up display resources and close all windows
        """
        try:
            self.logger.info("Closing visual monitor windows")
            
            with self.display_lock:
                self.display_active = False
                
                # Close individual windows
                for window in self.windows:
                    try:
                        cv2.destroyWindow(window.window_name)
                    except Exception as e:
                        self.logger.error(f"Error closing window {window.window_name}: {e}")
                
                # Destroy all windows as fallback
                cv2.destroyAllWindows()
                
                # Clear windows list
                self.windows.clear()
                
                self.logger.info("All visual monitor windows closed")
                
        except Exception as e:
            self.logger.error(f"Error closing visual monitor windows: {e}")
    
    def is_active(self) -> bool:
        """
        Check if visual monitor is active
        
        Returns:
            bool: True if monitor is active
        """
        return self.display_active
    
    def get_window_status(self) -> Dict[str, Any]:
        """
        Get status of all display windows
        
        Returns:
            Dict containing window status information
        """
        with self.display_lock:
            return {
                'display_active': self.display_active,
                'total_windows': len(self.windows),
                'active_windows': sum(1 for w in self.windows if w.is_active),
                'windows': [
                    {
                        'camera_id': w.camera_id,
                        'window_name': w.window_name,
                        'is_active': w.is_active,
                        'last_update': w.last_update,
                        'error_message': w.error_message
                    }
                    for w in self.windows
                ]
            }
    
    def set_window_active(self, camera_id: int, active: bool) -> bool:
        """
        Set active status for a specific window
        
        Args:
            camera_id: Camera identifier
            active: Whether window should be active
            
        Returns:
            bool: True if status changed successfully
        """
        if camera_id >= len(self.windows):
            return False
        
        try:
            with self.display_lock:
                window = self.windows[camera_id]
                window.is_active = active
                
                if not active:
                    # Show inactive placeholder
                    placeholder = self._create_placeholder_frame(camera_id, "Camera Inactive")
                    cv2.imshow(window.window_name, placeholder)
                    cv2.waitKey(1)
                
                self.logger.debug(f"Camera {camera_id} window set to {'active' if active else 'inactive'}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error setting window status for camera {camera_id}: {e}")
            return False
    
    def toggle_detection_boxes(self) -> bool:
        """
        Toggle display of detection bounding boxes
        
        Returns:
            bool: New state of detection box display
        """
        self.config.show_detection_boxes = not self.config.show_detection_boxes
        self.logger.info(f"Detection boxes {'enabled' if self.config.show_detection_boxes else 'disabled'}")
        self.add_log_entry("INFO", f"检测框显示{'开启' if self.config.show_detection_boxes else '关闭'}")
        return self.config.show_detection_boxes
    
    def get_camera_settings(self, camera_id: int) -> Optional[CameraSettings]:
        """Get camera settings for a specific camera"""
        return self.camera_settings.get(camera_id)
    
    def update_camera_settings(self, camera_id: int, **kwargs) -> bool:
        """Update camera settings"""
        try:
            if camera_id in self.camera_settings:
                settings = self.camera_settings[camera_id]
                for key, value in kwargs.items():
                    if hasattr(settings, key):
                        setattr(settings, key, value)
                        self.add_log_entry("INFO", f"摄像头{camera_id} {key}更新为{value}", camera_id)
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error updating camera settings: {e}")
            self.add_log_entry("ERROR", f"更新摄像头{camera_id}设置失败: {e}", camera_id)
            return False


# Compatibility alias for existing code
VisualMonitor = EnhancedVisualMonitor
#!/usr/bin/env python3
"""
PySide GUI Main Window for MQTT Camera Monitoring System
Provides graphical interface for configuration and monitoring
"""

import sys
from typing import Optional, List, Dict
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QLabel, QFrame, QCheckBox, QComboBox, QLineEdit,
    QPushButton, QSpinBox, QDoubleSpinBox, QFileDialog, QGridLayout,
    QGroupBox, QScrollArea, QTextEdit
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QTextCursor
import os

# Import USB camera detector
try:
    from usb_camera_detector import USBCameraDetector
except ImportError:
    # Fallback if detector is not available
    USBCameraDetector = None

# Import path utilities for PyInstaller compatibility
try:
    from path_utils import get_config_path, get_mask_path
except ImportError:
    # Fallback if path_utils is not available
    def get_config_path(filename="config.yaml"):
        return filename
    def get_mask_path(filename):
        return filename


class MainWindow(QMainWindow):
    """Main GUI window for MQTT Camera Monitoring System"""
    
    def __init__(self):
        super().__init__()
        self.camera_widgets = []  # Initialize camera widgets list
        self.delay_spinbox = None
        self.global_threshold_spinbox = None
        self.interval_spinbox = None
        self.autosave_label = None
        self.available_cameras = []  # Store detected USB cameras
        self.camera_detector = None
        
        # Initialize USB camera detector
        self._initialize_camera_detector()
        
        self.setup_window_properties()
        self.setup_ui()
        # Load configuration after UI is set up
        self.load_configuration_from_file()
    
    def _initialize_camera_detector(self):
        """Initialize USB camera detector and detect available cameras"""
        try:
            if USBCameraDetector:
                self.camera_detector = USBCameraDetector()
                self.available_cameras = self.camera_detector.detect_cameras()
                print(f"检测到 {len(self.available_cameras)} 个USB摄像头:")
                for camera in self.available_cameras:
                    print(f"  - ID {camera['id']}: {camera['name']}")
            else:
                print("USB摄像头检测器不可用，使用默认数字ID")
                # Fallback to simple numeric IDs
                self.available_cameras = [
                    {'id': i, 'name': f'摄像头 {i}', 'description': f'USB摄像头 {i}'}
                    for i in range(6)
                ]
        except Exception as e:
            print(f"初始化摄像头检测器失败: {e}")
            # Fallback to simple numeric IDs
            self.available_cameras = [
                {'id': i, 'name': f'摄像头 {i}', 'description': f'USB摄像头 {i}'}
                for i in range(6)
            ]
    
    def refresh_camera_list(self):
        """刷新可用摄像头列表"""
        try:
            if self.camera_detector:
                self.available_cameras = self.camera_detector.detect_cameras()
                print(f"刷新后检测到 {len(self.available_cameras)} 个USB摄像头")
                
                # Update all camera combo boxes
                for widget in self.camera_widgets:
                    combo = widget['id_combo']
                    current_selection = combo.currentText()
                    
                    # Clear and repopulate
                    combo.clear()
                    for camera in self.available_cameras:
                        combo.addItem(f"{camera['name']} (ID: {camera['id']})", camera['id'])
                    
                    # Try to restore previous selection
                    index = combo.findText(current_selection)
                    if index >= 0:
                        combo.setCurrentIndex(index)
                        
                return True
        except Exception as e:
            print(f"刷新摄像头列表失败: {e}")
            return False
    
    def on_refresh_cameras_clicked(self):
        """处理刷新摄像头按钮点击事件"""
        try:
            print("正在刷新摄像头列表...")
            success = self.refresh_camera_list()
            
            if success:
                print("摄像头列表刷新成功")
                # 可以添加状态栏消息或弹窗提示
            else:
                print("摄像头列表刷新失败")
                
        except Exception as e:
            print(f"刷新摄像头列表时出错: {e}")
        
    def setup_window_properties(self):
        """Initialize basic window properties and styling"""
        # Set window title and size
        self.setWindowTitle("MQTT摄像头监控系统")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # Set window icon (if available)
        # self.setWindowIcon(QIcon("icon.png"))
        
        # Apply basic styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QFrame {
                border: 1px solid #cccccc;
                border-radius: 5px;
                background-color: white;
                margin: 2px;
            }
            QLabel {
                font-size: 12px;
                color: #333333;
            }
        """)
    
    def setup_ui(self):
        """Set up main window with left and right panel layout"""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main horizontal layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Create left panel (Camera Configuration)
        self.left_panel = self.create_left_panel()
        splitter.addWidget(self.left_panel)
        
        # Create right panel (System Status)
        self.right_panel = self.create_right_panel()
        splitter.addWidget(self.right_panel)
        
        # Set initial splitter sizes (60% left, 40% right)
        splitter.setSizes([720, 480])
        
        # Set splitter properties
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)
    
    def create_left_panel(self) -> QFrame:
        """Create camera configuration panel (left side)"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        
        # Create scroll area for the panel content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Create content widget for scroll area
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Panel title
        title_label = QLabel("摄像头配置")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Add separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # Create camera configuration widgets
        self.camera_widgets = []
        self.create_camera_configuration_widgets(layout)
        
        # Add stretch to push content to top
        layout.addStretch()
        
        # Set content widget to scroll area
        scroll_area.setWidget(content_widget)
        
        # Create panel layout and add scroll area
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.addWidget(scroll_area)
        
        return panel
    
    def create_right_panel(self) -> QFrame:
        """Create system status panel (right side)"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        
        # Create scroll area for the panel content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Create content widget for scroll area
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Panel title
        title_label = QLabel("系统状态")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Add separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # Create MQTT status display
        self.create_mqtt_status_display(layout)
        
        # Create baseline events log
        self.create_baseline_events_log(layout)
        
        # Create trigger events log
        self.create_trigger_events_log(layout)
        
        # Create system health indicators
        self.create_system_health_indicators(layout)
        
        # Add stretch to push content to top
        layout.addStretch()
        
        # Set content widget to scroll area
        scroll_area.setWidget(content_widget)
        
        # Create panel layout and add scroll area
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.addWidget(scroll_area)
        
        return panel
    
    def create_camera_configuration_widgets(self, layout: QVBoxLayout):
        """Create camera configuration widgets for up to 6 cameras"""
        # Create group box for camera configurations
        camera_group = QGroupBox("摄像头设置 (0-5)")
        camera_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        camera_layout = QVBoxLayout(camera_group)
        camera_layout.setSpacing(15)
        
        # Add refresh cameras button
        refresh_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 刷新摄像头列表")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        refresh_btn.clicked.connect(self.on_refresh_cameras_clicked)
        
        refresh_layout.addWidget(refresh_btn)
        refresh_layout.addStretch()
        camera_layout.addLayout(refresh_layout)
        
        # Create configuration widgets for 6 cameras (Camera 0-5)
        for camera_id in range(6):
            camera_widget = self.create_single_camera_widget(camera_id)
            self.camera_widgets.append(camera_widget)
            camera_layout.addWidget(camera_widget['frame'])
        
        layout.addWidget(camera_group)
        
        # Add system parameter configuration
        self.create_system_parameter_widgets(layout)
    
    def create_single_camera_widget(self, camera_id: int) -> dict:
        """Create configuration widgets for a single camera"""
        # Create frame for this camera
        camera_frame = QFrame()
        camera_frame.setFrameStyle(QFrame.Box)
        camera_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #dddddd;
                border-radius: 3px;
                background-color: #fafafa;
                margin: 2px;
                padding: 5px;
            }
        """)
        
        # Create grid layout for camera controls
        grid_layout = QGridLayout(camera_frame)
        grid_layout.setContentsMargins(10, 10, 10, 10)
        grid_layout.setSpacing(8)
        
        # Camera enable/disable checkbox
        enable_checkbox = QCheckBox(f"启用摄像头 {camera_id}")
        enable_checkbox.setStyleSheet("font-weight: bold; color: #333333;")
        grid_layout.addWidget(enable_checkbox, 0, 0, 1, 3)
        
        # Camera ID selection dropdown with USB device names
        id_label = QLabel("USB摄像头:")
        id_combo = QComboBox()
        
        # Populate with detected USB cameras
        if self.available_cameras:
            for camera in self.available_cameras:
                display_text = f"{camera['name']} (ID: {camera['id']})"
                id_combo.addItem(display_text, camera['id'])
        else:
            # Fallback to simple numeric IDs if no cameras detected
            for i in range(6):
                id_combo.addItem(f"摄像头 {i}", i)
        
        # Set default selection
        if camera_id < id_combo.count():
            id_combo.setCurrentIndex(camera_id)
        
        id_combo.setEnabled(False)  # Initially disabled
        grid_layout.addWidget(id_label, 1, 0)
        grid_layout.addWidget(id_combo, 1, 1, 1, 2)
        
        # Mask file path input with browser button
        mask_label = QLabel("遮罩文件:")
        mask_input = QLineEdit()
        mask_input.setPlaceholderText("选择遮罩文件 (1920x1080分辨率)")
        mask_input.setEnabled(False)  # Initially disabled
        mask_browse_btn = QPushButton("浏览...")
        mask_browse_btn.setEnabled(False)  # Initially disabled
        mask_browse_btn.setMaximumWidth(80)
        grid_layout.addWidget(mask_label, 2, 0)
        grid_layout.addWidget(mask_input, 2, 1)
        grid_layout.addWidget(mask_browse_btn, 2, 2)
        
        # Baseline red light count input
        baseline_label = QLabel("基线计数:")
        baseline_spinbox = QSpinBox()
        baseline_spinbox.setRange(0, 999)
        baseline_spinbox.setValue(0)
        baseline_spinbox.setEnabled(False)  # Initially disabled
        baseline_spinbox.setReadOnly(True)  # Read-only as it's set by system
        baseline_spinbox.setStyleSheet("background-color: #f0f0f0;")
        grid_layout.addWidget(baseline_label, 3, 0)
        grid_layout.addWidget(baseline_spinbox, 3, 1, 1, 2)
        
        # Comparison threshold input
        threshold_label = QLabel("阈值:")
        threshold_spinbox = QSpinBox()
        threshold_spinbox.setRange(1, 50)
        threshold_spinbox.setValue(2)  # Default value
        threshold_spinbox.setEnabled(False)  # Initially disabled
        grid_layout.addWidget(threshold_label, 4, 0)
        grid_layout.addWidget(threshold_spinbox, 4, 1, 1, 2)
        
        # Add separator line for monitoring section
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("color: #cccccc;")
        grid_layout.addWidget(separator, 5, 0, 1, 3)
        
        # Camera monitoring status section
        status_label = QLabel("监控状态:")
        status_label.setStyleSheet("font-weight: bold; color: #666666;")
        grid_layout.addWidget(status_label, 6, 0, 1, 3)
        
        # Current detection count display
        current_count_label = QLabel("当前计数:")
        current_count_display = QLabel("--")
        current_count_display.setStyleSheet("""
            QLabel {
                padding: 2px 6px;
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: #ffffff;
                font-weight: bold;
                color: #333333;
            }
        """)
        grid_layout.addWidget(current_count_label, 7, 0)
        grid_layout.addWidget(current_count_display, 7, 1, 1, 2)
        
        # Trigger status indicator
        trigger_status_label = QLabel("触发状态:")
        trigger_status_indicator = QLabel("未触发")
        trigger_status_indicator.setStyleSheet("""
            QLabel {
                padding: 2px 6px;
                border-radius: 3px;
                background-color: #f0f0f0;
                color: #666666;
                font-weight: bold;
            }
        """)
        grid_layout.addWidget(trigger_status_label, 8, 0)
        grid_layout.addWidget(trigger_status_indicator, 8, 1, 1, 2)
        
        # Camera status indicator (enabled/disabled)
        camera_status_label = QLabel("摄像头状态:")
        camera_status_indicator = QLabel("已禁用")
        camera_status_indicator.setStyleSheet("""
            QLabel {
                padding: 2px 6px;
                border-radius: 3px;
                background-color: #ffeeee;
                color: #cc0000;
                font-weight: bold;
            }
        """)
        grid_layout.addWidget(camera_status_label, 9, 0)
        grid_layout.addWidget(camera_status_indicator, 9, 1, 1, 2)
        
        # Connect enable checkbox to enable/disable other controls and update status
        def on_enable_changed(checked):
            id_combo.setEnabled(checked)
            mask_input.setEnabled(checked)
            mask_browse_btn.setEnabled(checked)
            threshold_spinbox.setEnabled(checked)
            # Update camera status indicator
            if checked:
                camera_status_indicator.setText("已启用")
                camera_status_indicator.setStyleSheet("""
                    QLabel {
                        padding: 2px 6px;
                        border-radius: 3px;
                        background-color: #eeffee;
                        color: #009900;
                        font-weight: bold;
                    }
                """)
                # Validate configuration when enabled
                self._validate_single_camera_config(camera_id)
            else:
                camera_status_indicator.setText("已禁用")
                camera_status_indicator.setStyleSheet("""
                    QLabel {
                        padding: 2px 6px;
                        border-radius: 3px;
                        background-color: #ffeeee;
                        color: #cc0000;
                        font-weight: bold;
                    }
                """)
                # Reset monitoring displays when disabled
                current_count_display.setText("--")
                trigger_status_indicator.setText("未触发")
                trigger_status_indicator.setStyleSheet("""
                    QLabel {
                        padding: 2px 6px;
                        border-radius: 3px;
                        background-color: #f0f0f0;
                        color: #666666;
                        font-weight: bold;
                    }
                """)
                # Clear any validation errors when disabled
                self._clear_camera_validation_error(camera_id)
        
        enable_checkbox.toggled.connect(on_enable_changed)
        
        # Connect real-time validation for camera ID changes
        def on_camera_id_changed():
            if enable_checkbox.isChecked():
                self._validate_single_camera_config(camera_id)
        
        id_combo.currentIndexChanged.connect(on_camera_id_changed)
        
        # Connect real-time validation for mask file changes
        def on_mask_path_changed():
            if enable_checkbox.isChecked():
                self._validate_single_camera_config(camera_id)
        
        mask_input.textChanged.connect(on_mask_path_changed)
        
        # Connect real-time validation for threshold changes
        def on_threshold_changed():
            if enable_checkbox.isChecked():
                self._validate_single_camera_config(camera_id)
        
        threshold_spinbox.valueChanged.connect(on_threshold_changed)
        
        # Connect browse button to file dialog
        def browse_mask_file():
            file_path, _ = QFileDialog.getOpenFileName(
                camera_frame,
                f"选择摄像头 {camera_id} 的遮罩文件",
                "",
                "图像文件 (*.png *.jpg *.jpeg *.bmp *.tiff);;所有文件 (*)"
            )
            if file_path:
                mask_input.setText(file_path)
        
        mask_browse_btn.clicked.connect(browse_mask_file)
        
        # Store widget references
        camera_widget = {
            'frame': camera_frame,
            'camera_id': camera_id,
            'enable_checkbox': enable_checkbox,
            'id_combo': id_combo,
            'mask_input': mask_input,
            'mask_browse_btn': mask_browse_btn,
            'baseline_spinbox': baseline_spinbox,
            'threshold_spinbox': threshold_spinbox,
            'current_count_display': current_count_display,
            'trigger_status_indicator': trigger_status_indicator,
            'camera_status_indicator': camera_status_indicator
        }
        
        return camera_widget
    
    def get_camera_configuration(self) -> list:
        """Get current camera configuration from widgets"""
        configurations = []
        
        for widget in self.camera_widgets:
            config = {
                'camera_id': widget['camera_id'],
                'enabled': widget['enable_checkbox'].isChecked(),
                'physical_camera_id': widget['id_combo'].currentData() if widget['id_combo'].currentData() is not None else widget['id_combo'].currentIndex(),
                'mask_path': widget['mask_input'].text().strip(),
                'baseline_count': widget['baseline_spinbox'].value(),
                'threshold': widget['threshold_spinbox'].value()
            }
            configurations.append(config)
        
        return configurations
    
    def update_camera_baseline(self, camera_id: int, baseline_count: int):
        """Update baseline count display for a specific camera"""
        if 0 <= camera_id < len(self.camera_widgets):
            self.camera_widgets[camera_id]['baseline_spinbox'].setValue(baseline_count)
    
    def update_camera_info(self, camera_id: int, baseline: int, current: int, triggered: bool):
        """Update camera monitoring info (baseline, current count, trigger status)"""
        if 0 <= camera_id < len(self.camera_widgets):
            widget = self.camera_widgets[camera_id]
            
            # Only update if camera is enabled
            if widget['enable_checkbox'].isChecked():
                # Update baseline count
                widget['baseline_spinbox'].setValue(baseline)
                
                # Update current detection count
                widget['current_count_display'].setText(str(current))
                
                # Update trigger status
                if triggered:
                    widget['trigger_status_indicator'].setText("已触发")
                    widget['trigger_status_indicator'].setStyleSheet("""
                        QLabel {
                            padding: 2px 6px;
                            border-radius: 3px;
                            background-color: #ffeeee;
                            color: #cc0000;
                            font-weight: bold;
                        }
                    """)
                else:
                    widget['trigger_status_indicator'].setText("未触发")
                    widget['trigger_status_indicator'].setStyleSheet("""
                        QLabel {
                            padding: 2px 6px;
                            border-radius: 3px;
                            background-color: #eeffee;
                            color: #009900;
                            font-weight: bold;
                        }
                    """)
    
    def update_camera_current_count(self, camera_id: int, current_count: int):
        """Update current detection count for a specific camera"""
        if 0 <= camera_id < len(self.camera_widgets):
            widget = self.camera_widgets[camera_id]
            
            # Only update if camera is enabled
            if widget['enable_checkbox'].isChecked():
                widget['current_count_display'].setText(str(current_count))
    
    def update_camera_trigger_status(self, camera_id: int, triggered: bool):
        """Update trigger status for a specific camera"""
        if 0 <= camera_id < len(self.camera_widgets):
            widget = self.camera_widgets[camera_id]
            
            # Only update if camera is enabled
            if widget['enable_checkbox'].isChecked():
                if triggered:
                    widget['trigger_status_indicator'].setText("已触发")
                    widget['trigger_status_indicator'].setStyleSheet("""
                        QLabel {
                            padding: 2px 6px;
                            border-radius: 3px;
                            background-color: #ffeeee;
                            color: #cc0000;
                            font-weight: bold;
                        }
                    """)
                else:
                    widget['trigger_status_indicator'].setText("未触发")
                    widget['trigger_status_indicator'].setStyleSheet("""
                        QLabel {
                            padding: 2px 6px;
                            border-radius: 3px;
                            background-color: #eeffee;
                            color: #009900;
                            font-weight: bold;
                        }
                    """)
    
    def reset_camera_monitoring_displays(self):
        """Reset all camera monitoring displays to default state"""
        for widget in self.camera_widgets:
            if widget['enable_checkbox'].isChecked():
                # Reset to monitoring state but no data
                widget['current_count_display'].setText("--")
                widget['trigger_status_indicator'].setText("监控中")
                widget['trigger_status_indicator'].setStyleSheet("""
                    QLabel {
                        padding: 2px 6px;
                        border-radius: 3px;
                        background-color: #ffffee;
                        color: #cc9900;
                        font-weight: bold;
                    }
                """)
            else:
                # Reset to disabled state
                widget['current_count_display'].setText("--")
                widget['trigger_status_indicator'].setText("未触发")
                widget['trigger_status_indicator'].setStyleSheet("""
                    QLabel {
                        padding: 2px 6px;
                        border-radius: 3px;
                        background-color: #f0f0f0;
                        color: #666666;
                        font-weight: bold;
                    }
                """)
    
    def get_enabled_cameras(self) -> list:
        """Get list of enabled camera IDs"""
        enabled_cameras = []
        for widget in self.camera_widgets:
            if widget['enable_checkbox'].isChecked():
                enabled_cameras.append(widget['camera_id'])
        return enabled_cameras
    
    def validate_camera_configuration(self) -> tuple[bool, str]:
        """Validate current camera configuration with comprehensive checks"""
        enabled_cameras = []
        used_physical_ids = []
        
        for widget in self.camera_widgets:
            if widget['enable_checkbox'].isChecked():
                camera_id = widget['camera_id']
                physical_id = widget['id_combo'].currentData() if widget['id_combo'].currentData() is not None else widget['id_combo'].currentIndex()
                mask_path = widget['mask_input'].text().strip()
                threshold = widget['threshold_spinbox'].value()
                
                # Validate camera ID range (0-5)
                if not (0 <= camera_id <= 5):
                    return False, f"摄像头ID {camera_id} 超出有效范围 (0-5)"
                
                # Validate physical camera ID range (0-5)
                if not (0 <= physical_id <= 5):
                    return False, f"摄像头 {camera_id}: 物理摄像头ID {physical_id} 超出有效范围 (0-5)"
                
                # Check for duplicate physical camera ID assignments
                if physical_id in used_physical_ids:
                    return False, f"物理摄像头ID {physical_id} 被多个摄像头使用，每个物理摄像头只能分配给一个摄像头"
                used_physical_ids.append(physical_id)
                
                # Check mask file existence and format
                if not mask_path:
                    return False, f"摄像头 {camera_id}: 必须指定遮罩文件路径"
                
                if not os.path.exists(mask_path):
                    return False, f"摄像头 {camera_id}: 遮罩文件不存在: {mask_path}"
                
                # Validate mask file format and ensure 1920x1080 resolution
                try:
                    import cv2
                    mask_img = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
                    if mask_img is None:
                        return False, f"摄像头 {camera_id}: 无法读取遮罩文件，请检查文件格式: {mask_path}"
                    
                    height, width = mask_img.shape
                    if width != 1920 or height != 1080:
                        return False, f"摄像头 {camera_id}: 遮罩文件分辨率必须为1920x1080，当前为{width}x{height}: {mask_path}"
                        
                except Exception as e:
                    return False, f"摄像头 {camera_id}: 遮罩文件验证失败: {str(e)}"
                
                # Validate comparison threshold range
                if not (1 <= threshold <= 50):
                    return False, f"摄像头 {camera_id}: 比较阈值 {threshold} 超出有效范围 (1-50)"
                
                enabled_cameras.append(camera_id)
        
        # Ensure at least one camera is enabled before starting monitoring
        if not enabled_cameras:
            return False, "至少需要启用一个摄像头才能开始监控"
        
        # Validate system parameters
        delay_time = self.delay_spinbox.value()
        if not (0.1 <= delay_time <= 10.0):
            return False, f"延时时间 {delay_time} 秒超出有效范围 (0.1-10.0秒)"
        
        global_threshold = self.global_threshold_spinbox.value()
        if not (1 <= global_threshold <= 50):
            return False, f"全局阈值 {global_threshold} 超出有效范围 (1-50)"
        
        monitoring_interval = self.interval_spinbox.value()
        if not (0.1 <= monitoring_interval <= 5.0):
            return False, f"监控间隔 {monitoring_interval} 秒超出有效范围 (0.1-5.0秒)"
        
        return True, "配置验证通过"
    
    def _validate_single_camera_config(self, camera_id: int):
        """Validate configuration for a single camera and show visual feedback"""
        if camera_id >= len(self.camera_widgets):
            return
        
        widget = self.camera_widgets[camera_id]
        
        # Only validate if camera is enabled
        if not widget['enable_checkbox'].isChecked():
            return
        
        error_messages = []
        
        # Validate physical camera ID
        physical_id = widget['id_combo'].currentData() if widget['id_combo'].currentData() is not None else widget['id_combo'].currentIndex()
        if not (0 <= physical_id <= 5):
            error_messages.append(f"物理摄像头ID {physical_id} 超出范围 (0-5)")
        
        # Check for duplicate physical camera IDs
        used_physical_ids = []
        for i, other_widget in enumerate(self.camera_widgets):
            if (i != camera_id and 
                other_widget['enable_checkbox'].isChecked() and 
                (other_widget['id_combo'].currentData() if other_widget['id_combo'].currentData() is not None else other_widget['id_combo'].currentIndex()) == physical_id):
                error_messages.append(f"物理摄像头ID {physical_id} 已被摄像头 {i} 使用")
                break
        
        # Validate mask file
        mask_path = widget['mask_input'].text().strip()
        if not mask_path:
            error_messages.append("必须指定遮罩文件路径")
        elif not os.path.exists(mask_path):
            error_messages.append("遮罩文件不存在")
        else:
            # Validate mask file resolution
            try:
                import cv2
                mask_img = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
                if mask_img is None:
                    error_messages.append("无法读取遮罩文件，请检查文件格式")
                else:
                    height, width = mask_img.shape
                    if width != 1920 or height != 1080:
                        error_messages.append(f"遮罩文件分辨率必须为1920x1080，当前为{width}x{height}")
            except Exception as e:
                error_messages.append(f"遮罩文件验证失败: {str(e)}")
        
        # Validate threshold
        threshold = widget['threshold_spinbox'].value()
        if not (1 <= threshold <= 50):
            error_messages.append(f"阈值 {threshold} 超出范围 (1-50)")
        
        # Show validation feedback
        if error_messages:
            self._show_camera_validation_error(camera_id, error_messages)
        else:
            self._clear_camera_validation_error(camera_id)
    
    def _show_camera_validation_error(self, camera_id: int, error_messages: list):
        """Show validation error for a specific camera"""
        if camera_id >= len(self.camera_widgets):
            return
        
        widget = self.camera_widgets[camera_id]
        
        # Change camera status to show error
        error_text = "; ".join(error_messages)
        widget['camera_status_indicator'].setText("配置错误")
        widget['camera_status_indicator'].setStyleSheet("""
            QLabel {
                padding: 2px 6px;
                border-radius: 3px;
                background-color: #ffeeee;
                color: #cc0000;
                font-weight: bold;
            }
        """)
        widget['camera_status_indicator'].setToolTip(error_text)
        
        # Add red border to frame to indicate error
        widget['frame'].setStyleSheet("""
            QFrame {
                border: 2px solid #cc0000;
                border-radius: 3px;
                background-color: #fff5f5;
                margin: 2px;
                padding: 5px;
            }
        """)
    
    def _clear_camera_validation_error(self, camera_id: int):
        """Clear validation error for a specific camera"""
        if camera_id >= len(self.camera_widgets):
            return
        
        widget = self.camera_widgets[camera_id]
        
        # Reset camera status to normal
        if widget['enable_checkbox'].isChecked():
            widget['camera_status_indicator'].setText("已启用")
            widget['camera_status_indicator'].setStyleSheet("""
                QLabel {
                    padding: 2px 6px;
                    border-radius: 3px;
                    background-color: #eeffee;
                    color: #009900;
                    font-weight: bold;
                }
            """)
        else:
            widget['camera_status_indicator'].setText("已禁用")
            widget['camera_status_indicator'].setStyleSheet("""
                QLabel {
                    padding: 2px 6px;
                    border-radius: 3px;
                    background-color: #ffeeee;
                    color: #cc0000;
                    font-weight: bold;
                }
            """)
        
        widget['camera_status_indicator'].setToolTip("")
        
        # Reset frame style to normal
        widget['frame'].setStyleSheet("""
            QFrame {
                border: 1px solid #dddddd;
                border-radius: 3px;
                background-color: #fafafa;
                margin: 2px;
                padding: 5px;
            }
        """)
    
    def validate_system_parameters(self) -> tuple[bool, str]:
        """Validate system parameters with comprehensive checks"""
        # Validate delay time
        delay_time = self.delay_spinbox.value()
        if not (0.1 <= delay_time <= 10.0):
            return False, f"延时时间 {delay_time} 秒超出有效范围 (0.1-10.0秒)"
        
        # Validate global threshold
        global_threshold = self.global_threshold_spinbox.value()
        if not (1 <= global_threshold <= 50):
            return False, f"全局阈值 {global_threshold} 超出有效范围 (1-50)"
        
        # Validate monitoring interval
        monitoring_interval = self.interval_spinbox.value()
        if not (0.1 <= monitoring_interval <= 5.0):
            return False, f"监控间隔 {monitoring_interval} 秒超出有效范围 (0.1-5.0秒)"
        
        return True, "系统参数验证通过"
    
    def _validate_system_parameters_realtime(self):
        """Real-time validation of system parameters with visual feedback"""
        valid, error_msg = self.validate_system_parameters()
        
        if not valid:
            # Show error in auto-save label
            self.autosave_label.setText(f"参数错误: {error_msg}")
            self.autosave_label.setStyleSheet("color: #cc0000; font-style: italic; font-weight: bold;")
        else:
            # Clear error and show normal auto-save status
            self.autosave_label.setText("自动保存: 就绪")
            self.autosave_label.setStyleSheet("color: #666666; font-style: italic;")
    
    def create_system_parameter_widgets(self, layout: QVBoxLayout):
        """Create system parameter configuration widgets"""
        # Create group box for system parameters
        system_group = QGroupBox("系统参数")
        system_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        system_layout = QGridLayout(system_group)
        system_layout.setContentsMargins(15, 15, 15, 15)
        system_layout.setSpacing(10)
        
        # Delay time input field (default 0.4s)
        delay_label = QLabel("延时时间 (秒):")
        self.delay_spinbox = QDoubleSpinBox()
        self.delay_spinbox.setRange(0.1, 10.0)
        self.delay_spinbox.setSingleStep(0.1)
        self.delay_spinbox.setDecimals(1)
        self.delay_spinbox.setValue(0.4)  # Default value
        self.delay_spinbox.setToolTip("建立基线前的延时时间 (秒)")
        system_layout.addWidget(delay_label, 0, 0)
        system_layout.addWidget(self.delay_spinbox, 0, 1)
        
        # Global comparison threshold input field (default 2)
        global_threshold_label = QLabel("全局阈值:")
        self.global_threshold_spinbox = QSpinBox()
        self.global_threshold_spinbox.setRange(1, 50)
        self.global_threshold_spinbox.setValue(2)  # Default value
        self.global_threshold_spinbox.setToolTip("所有摄像头的全局比较阈值")
        system_layout.addWidget(global_threshold_label, 1, 0)
        system_layout.addWidget(self.global_threshold_spinbox, 1, 1)
        
        # Monitoring interval input field (default 0.2s)
        interval_label = QLabel("监控间隔 (秒):")
        self.interval_spinbox = QDoubleSpinBox()
        self.interval_spinbox.setRange(0.1, 5.0)
        self.interval_spinbox.setSingleStep(0.1)
        self.interval_spinbox.setDecimals(1)
        self.interval_spinbox.setValue(0.2)  # Default value
        self.interval_spinbox.setToolTip("检测之间的监控间隔 (秒)")
        system_layout.addWidget(interval_label, 2, 0)
        system_layout.addWidget(self.interval_spinbox, 2, 1)
        
        # Add separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        system_layout.addWidget(separator, 3, 0, 1, 2)
        
        # MQTT Broker Host input field
        broker_label = QLabel("MQTT代理地址:")
        self.mqtt_broker_input = QLineEdit()
        self.mqtt_broker_input.setPlaceholderText("例如: 192.168.10.80")
        self.mqtt_broker_input.setText("192.168.10.80")  # Default value
        self.mqtt_broker_input.setToolTip("MQTT代理服务器的IP地址或域名")
        system_layout.addWidget(broker_label, 4, 0)
        system_layout.addWidget(self.mqtt_broker_input, 4, 1)
        
        # MQTT Port input field
        port_label = QLabel("MQTT端口:")
        self.mqtt_port_spinbox = QSpinBox()
        self.mqtt_port_spinbox.setRange(1, 65535)
        self.mqtt_port_spinbox.setValue(1883)  # Default MQTT port
        self.mqtt_port_spinbox.setToolTip("MQTT代理服务器端口")
        system_layout.addWidget(port_label, 5, 0)
        system_layout.addWidget(self.mqtt_port_spinbox, 5, 1)
        
        # MQTT Client ID input field
        client_id_label = QLabel("客户端ID:")
        self.mqtt_client_id_input = QLineEdit()
        self.mqtt_client_id_input.setPlaceholderText("例如: receiver")
        self.mqtt_client_id_input.setText("receiver")  # Default value
        self.mqtt_client_id_input.setToolTip("MQTT客户端标识符")
        system_layout.addWidget(client_id_label, 6, 0)
        system_layout.addWidget(self.mqtt_client_id_input, 6, 1)
        
        # MQTT Subscribe Topic input field
        subscribe_topic_label = QLabel("订阅主题:")
        self.mqtt_subscribe_topic_input = QLineEdit()
        self.mqtt_subscribe_topic_input.setPlaceholderText("例如: changeState")
        self.mqtt_subscribe_topic_input.setText("changeState")  # Default value
        self.mqtt_subscribe_topic_input.setToolTip("订阅的MQTT主题")
        system_layout.addWidget(subscribe_topic_label, 7, 0)
        system_layout.addWidget(self.mqtt_subscribe_topic_input, 7, 1)
        
        # MQTT Publish Topic input field
        publish_topic_label = QLabel("发布主题:")
        self.mqtt_publish_topic_input = QLineEdit()
        self.mqtt_publish_topic_input.setPlaceholderText("例如: receiver/triggered")
        self.mqtt_publish_topic_input.setText("receiver/triggered")  # Default value
        self.mqtt_publish_topic_input.setToolTip("发布触发消息的MQTT主题")
        system_layout.addWidget(publish_topic_label, 8, 0)
        system_layout.addWidget(self.mqtt_publish_topic_input, 8, 1)
        
        # Auto-save status label
        self.autosave_label = QLabel("自动保存: 就绪")
        self.autosave_label.setStyleSheet("color: #666666; font-style: italic;")
        system_layout.addWidget(self.autosave_label, 9, 0, 1, 2)
        
        layout.addWidget(system_group)
        
        # Add system control buttons
        self.create_system_control_buttons(layout)
        
        # Connect parameter changes to auto-save functionality and validation
        self.delay_spinbox.valueChanged.connect(self.on_parameter_changed)
        self.global_threshold_spinbox.valueChanged.connect(self.on_parameter_changed)
        self.interval_spinbox.valueChanged.connect(self.on_parameter_changed)
        
        # Connect MQTT parameter changes to auto-save
        self.mqtt_broker_input.textChanged.connect(self.on_parameter_changed)
        self.mqtt_port_spinbox.valueChanged.connect(self.on_parameter_changed)
        self.mqtt_client_id_input.textChanged.connect(self.on_parameter_changed)
        self.mqtt_subscribe_topic_input.textChanged.connect(self.on_parameter_changed)
        self.mqtt_publish_topic_input.textChanged.connect(self.on_parameter_changed)
        
        # Connect real-time validation for system parameters
        self.delay_spinbox.valueChanged.connect(self._validate_system_parameters_realtime)
        self.global_threshold_spinbox.valueChanged.connect(self._validate_system_parameters_realtime)
        self.interval_spinbox.valueChanged.connect(self._validate_system_parameters_realtime)
        
        # Connect real-time validation for MQTT parameters
        self.mqtt_broker_input.textChanged.connect(self._validate_mqtt_parameters_realtime)
        self.mqtt_port_spinbox.valueChanged.connect(self._validate_mqtt_parameters_realtime)
        self.mqtt_client_id_input.textChanged.connect(self._validate_mqtt_parameters_realtime)
        self.mqtt_subscribe_topic_input.textChanged.connect(self._validate_mqtt_parameters_realtime)
        self.mqtt_publish_topic_input.textChanged.connect(self._validate_mqtt_parameters_realtime)
        
        # Also connect global threshold to update individual camera thresholds
        self.global_threshold_spinbox.valueChanged.connect(self.update_camera_thresholds)
    
    def create_system_control_buttons(self, layout: QVBoxLayout):
        """Create system start/stop control buttons"""
        # Create group box for system controls
        control_group = QGroupBox("系统控制")
        control_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        control_layout = QHBoxLayout(control_group)
        control_layout.setContentsMargins(15, 15, 15, 15)
        control_layout.setSpacing(10)
        
        # Start system button
        self.start_button = QPushButton("启动监控系统")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        control_layout.addWidget(self.start_button)
        
        # Stop system button
        self.stop_button = QPushButton("停止监控系统")
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #c1170a;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.stop_button.setEnabled(False)  # Initially disabled
        control_layout.addWidget(self.stop_button)
        
        # System status indicator
        self.system_status_label = QLabel("系统状态: 未启动")
        self.system_status_label.setStyleSheet("""
            QLabel {
                padding: 4px 8px;
                border-radius: 3px;
                background-color: #ffeeee;
                color: #cc0000;
                font-weight: bold;
            }
        """)
        control_layout.addWidget(self.system_status_label)
        
        layout.addWidget(control_group)
        
        # Connect button signals (will be connected by main application)
        # self.start_button.clicked.connect(self.start_monitoring_system)
        # self.stop_button.clicked.connect(self.stop_monitoring_system)
    
    def update_system_control_status(self, running: bool):
        """Update system control button states"""
        if running:
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.system_status_label.setText("系统状态: 运行中")
            self.system_status_label.setStyleSheet("""
                QLabel {
                    padding: 4px 8px;
                    border-radius: 3px;
                    background-color: #eeffee;
                    color: #009900;
                    font-weight: bold;
                }
            """)
        else:
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.system_status_label.setText("系统状态: 未启动")
            self.system_status_label.setStyleSheet("""
                QLabel {
                    padding: 4px 8px;
                    border-radius: 3px;
                    background-color: #ffeeee;
                    color: #cc0000;
                    font-weight: bold;
                }
            """)
    
    def on_parameter_changed(self):
        """Handle parameter changes and trigger auto-save"""
        # Update auto-save status
        self.autosave_label.setText("自动保存: 保存中...")
        self.autosave_label.setStyleSheet("color: #ff6600; font-style: italic;")
        
        # Save configuration to file
        self.save_configuration_to_file()
        
        # Notify external callback if set (for system wrapper updates)
        if hasattr(self, '_mqtt_config_callback') and self._mqtt_config_callback:
            try:
                mqtt_params = self.get_mqtt_parameters()
                self._mqtt_config_callback(mqtt_params)
            except Exception as e:
                print(f"MQTT配置回调失败: {e}")
        
        # Update status after a short delay
        QTimer.singleShot(1000, self.reset_autosave_status)
    
    def reset_autosave_status(self):
        """Reset auto-save status label"""
        self.autosave_label.setText("自动保存: 已保存")
        self.autosave_label.setStyleSheet("color: #009900; font-style: italic;")
    
    def set_mqtt_config_callback(self, callback):
        """Set callback function for MQTT configuration changes"""
        self._mqtt_config_callback = callback
    
    def update_camera_thresholds(self, value: int):
        """Update all camera threshold values when global threshold changes"""
        for widget in self.camera_widgets:
            widget['threshold_spinbox'].setValue(value)
    
    def get_system_parameters(self) -> dict:
        """Get current system parameters"""
        return {
            'delay_time': self.delay_spinbox.value(),
            'global_threshold': self.global_threshold_spinbox.value(),
            'monitoring_interval': self.interval_spinbox.value()
        }
    
    def get_mqtt_parameters(self) -> dict:
        """Get current MQTT parameters from GUI"""
        return {
            'broker_host': self.mqtt_broker_input.text().strip(),
            'broker_port': self.mqtt_port_spinbox.value(),
            'client_id': self.mqtt_client_id_input.text().strip(),
            'subscribe_topic': self.mqtt_subscribe_topic_input.text().strip(),
            'publish_topic': self.mqtt_publish_topic_input.text().strip(),
            'keepalive': 60,  # Default value
            'max_reconnect_attempts': 10,  # Default value
            'reconnect_delay': 5  # Default value
        }
    
    def apply_mqtt_parameters(self, mqtt_params: dict):
        """Apply MQTT parameters to GUI elements"""
        try:
            self.mqtt_broker_input.setText(mqtt_params.get('broker_host', '192.168.10.80'))
            self.mqtt_port_spinbox.setValue(mqtt_params.get('broker_port', 1883))
            self.mqtt_client_id_input.setText(mqtt_params.get('client_id', 'receiver'))
            self.mqtt_subscribe_topic_input.setText(mqtt_params.get('subscribe_topic', 'changeState'))
            self.mqtt_publish_topic_input.setText(mqtt_params.get('publish_topic', 'receiver/triggered'))
        except Exception as e:
            print(f"应用MQTT参数失败: {e}")
    
    def _validate_mqtt_parameters_realtime(self):
        """Real-time validation for MQTT parameters"""
        try:
            mqtt_params = self.get_mqtt_parameters()
            
            # Validate broker host
            broker_host = mqtt_params['broker_host']
            if not broker_host:
                self.autosave_label.setText("错误: MQTT代理地址不能为空")
                self.autosave_label.setStyleSheet("color: #cc0000; font-style: italic; font-weight: bold;")
                return
            
            # Validate client ID
            client_id = mqtt_params['client_id']
            if not client_id:
                self.autosave_label.setText("错误: 客户端ID不能为空")
                self.autosave_label.setStyleSheet("color: #cc0000; font-style: italic; font-weight: bold;")
                return
            
            # Validate topics
            subscribe_topic = mqtt_params['subscribe_topic']
            publish_topic = mqtt_params['publish_topic']
            if not subscribe_topic or not publish_topic:
                self.autosave_label.setText("错误: MQTT主题不能为空")
                self.autosave_label.setStyleSheet("color: #cc0000; font-style: italic; font-weight: bold;")
                return
            
            # If all validations pass
            self.autosave_label.setText("自动保存: 就绪")
            self.autosave_label.setStyleSheet("color: #666666; font-style: italic;")
            
        except Exception as e:
            self.autosave_label.setText(f"MQTT参数验证错误: {e}")
            self.autosave_label.setStyleSheet("color: #cc0000; font-style: italic; font-weight: bold;")
    
    def save_configuration_to_file(self):
        """Save current configuration to config file"""
        try:
            import yaml
            
            # Get current configuration
            camera_config = self.get_camera_configuration()
            system_params = self.get_system_parameters()
            mqtt_params = self.get_mqtt_parameters()
            
            # Load existing config file or create new structure
            config_file = get_config_path("config.yaml")
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f) or {}
            else:
                config = {}
            
            # Update MQTT configuration with GUI values (优先使用GUI配置)
            if 'mqtt' not in config:
                config['mqtt'] = {}
            
            config['mqtt'].update(mqtt_params)
            
            # Update configuration with GUI values
            if 'cameras' not in config:
                config['cameras'] = {}
            
            # Update camera count based on enabled cameras
            enabled_count = sum(1 for cam in camera_config if cam['enabled'])
            config['cameras']['count'] = max(enabled_count, 1)  # At least 1
            
            # Update red light detection parameters
            if 'red_light_detection' not in config:
                config['red_light_detection'] = {}
            
            config['red_light_detection']['count_decrease_threshold'] = system_params['global_threshold']
            
            # Add GUI-specific configuration section
            if 'gui_config' not in config:
                config['gui_config'] = {}
            
            config['gui_config']['delay_time'] = system_params['delay_time']
            config['gui_config']['monitoring_interval'] = system_params['monitoring_interval']
            config['gui_config']['cameras'] = camera_config
            config['gui_config']['mqtt'] = mqtt_params  # 保存GUI中的MQTT配置
            
            # Save updated configuration
            with open(config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            
        except Exception as e:
            print(f"保存配置错误: {e}")
            self.autosave_label.setText("自动保存: 错误")
            self.autosave_label.setStyleSheet("color: #cc0000; font-style: italic;")
    
    def load_configuration_from_file(self):
        """Load configuration from config file"""
        try:
            import yaml
            
            config_file = get_config_path("config.yaml")
            if not os.path.exists(config_file):
                return
            
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f) or {}
            
            # Load GUI-specific configuration if available
            gui_config = config.get('gui_config', {})
            
            # Load system parameters
            if 'delay_time' in gui_config:
                self.delay_spinbox.setValue(gui_config['delay_time'])
            
            if 'monitoring_interval' in gui_config:
                self.interval_spinbox.setValue(gui_config['monitoring_interval'])
            
            # Load global threshold from red_light_detection section
            red_light_config = config.get('red_light_detection', {})
            if 'count_decrease_threshold' in red_light_config:
                self.global_threshold_spinbox.setValue(red_light_config['count_decrease_threshold'])
            
            # Load MQTT configuration (优先从GUI配置读取，然后从主配置读取)
            mqtt_config = gui_config.get('mqtt', config.get('mqtt', {}))
            if mqtt_config:
                self.apply_mqtt_parameters(mqtt_config)
            
            # Load camera configurations
            camera_configs = gui_config.get('cameras', [])
            for i, cam_config in enumerate(camera_configs):
                if i < len(self.camera_widgets):
                    widget = self.camera_widgets[i]
                    widget['enable_checkbox'].setChecked(cam_config.get('enabled', False))
                    # Set camera selection by finding the matching camera ID
                    physical_camera_id = cam_config.get('physical_camera_id', i)
                    combo = widget['id_combo']
                    
                    # Find the index that matches the physical camera ID
                    found_index = -1
                    for idx in range(combo.count()):
                        if combo.itemData(idx) == physical_camera_id:
                            found_index = idx
                            break
                    
                    if found_index >= 0:
                        combo.setCurrentIndex(found_index)
                    else:
                        # Fallback to index if data not found
                        if physical_camera_id < combo.count():
                            combo.setCurrentIndex(physical_camera_id)
                    widget['mask_input'].setText(cam_config.get('mask_path', ''))
                    widget['threshold_spinbox'].setValue(cam_config.get('threshold', 2))
            
        except Exception as e:
            print(f"加载配置错误: {e}")
    
    def create_mqtt_status_display(self, layout: QVBoxLayout):
        """Create MQTT status display widgets"""
        # Create group box for MQTT status
        mqtt_group = QGroupBox("MQTT连接状态")
        mqtt_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        mqtt_layout = QGridLayout(mqtt_group)
        mqtt_layout.setContentsMargins(15, 15, 15, 15)
        mqtt_layout.setSpacing(8)
        
        # MQTT connection status indicator
        status_label = QLabel("连接状态:")
        self.mqtt_status_indicator = QLabel("未连接")
        self.mqtt_status_indicator.setStyleSheet("""
            QLabel {
                padding: 4px 8px;
                border-radius: 3px;
                background-color: #ffcccc;
                color: #cc0000;
                font-weight: bold;
            }
        """)
        mqtt_layout.addWidget(status_label, 0, 0)
        mqtt_layout.addWidget(self.mqtt_status_indicator, 0, 1)
        
        # Last message timestamp display
        timestamp_label = QLabel("最后消息时间:")
        self.last_message_timestamp = QLabel("无")
        self.last_message_timestamp.setStyleSheet("color: #666666;")
        mqtt_layout.addWidget(timestamp_label, 1, 0)
        mqtt_layout.addWidget(self.last_message_timestamp, 1, 1)
        
        # Connection information text area
        info_label = QLabel("连接信息:")
        self.connection_info_text = QTextEdit()
        self.connection_info_text.setMaximumHeight(80)
        self.connection_info_text.setReadOnly(True)
        self.connection_info_text.setPlainText("等待连接...")
        self.connection_info_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f8f8;
                border: 1px solid #dddddd;
                border-radius: 3px;
                font-family: monospace;
                font-size: 10px;
            }
        """)
        mqtt_layout.addWidget(info_label, 2, 0, Qt.AlignTop)
        mqtt_layout.addWidget(self.connection_info_text, 2, 1)
        
        layout.addWidget(mqtt_group)
    
    def update_mqtt_status(self, connected: bool, broker_host: str = "", last_message_time: str = ""):
        """Update MQTT connection status display"""
        if connected:
            self.mqtt_status_indicator.setText("已连接")
            self.mqtt_status_indicator.setStyleSheet("""
                QLabel {
                    padding: 4px 8px;
                    border-radius: 3px;
                    background-color: #ccffcc;
                    color: #009900;
                    font-weight: bold;
                }
            """)
            if broker_host:
                self.connection_info_text.setPlainText(f"已连接到: {broker_host}\n客户端ID: receiver")
        else:
            self.mqtt_status_indicator.setText("未连接")
            self.mqtt_status_indicator.setStyleSheet("""
                QLabel {
                    padding: 4px 8px;
                    border-radius: 3px;
                    background-color: #ffcccc;
                    color: #cc0000;
                    font-weight: bold;
                }
            """)
            self.connection_info_text.setPlainText("连接断开或未建立")
        
        if last_message_time:
            self.last_message_timestamp.setText(last_message_time)
        else:
            self.last_message_timestamp.setText("无")
    
    def create_baseline_events_log(self, layout: QVBoxLayout):
        """Create baseline events log display"""
        # Create group box for baseline events
        baseline_group = QGroupBox("基线建立事件")
        baseline_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        baseline_layout = QVBoxLayout(baseline_group)
        baseline_layout.setContentsMargins(15, 15, 15, 15)
        baseline_layout.setSpacing(8)
        
        # Scrollable text area for baseline establishment events
        self.baseline_events_text = QTextEdit()
        self.baseline_events_text.setMaximumHeight(120)
        self.baseline_events_text.setReadOnly(True)
        self.baseline_events_text.setPlainText("等待基线建立事件...")
        self.baseline_events_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f8f8;
                border: 1px solid #dddddd;
                border-radius: 3px;
                font-family: monospace;
                font-size: 10px;
            }
        """)
        baseline_layout.addWidget(self.baseline_events_text)
        
        layout.addWidget(baseline_group)
    
    def log_baseline_event(self, timestamp: str, triggered_cameras: list, message_content: str = ""):
        """Log baseline establishment event with timestamp and triggered cameras information"""
        # Format the camera list
        if triggered_cameras:
            camera_list = ", ".join([f"摄像头{cam_id}" for cam_id in triggered_cameras])
        else:
            camera_list = ""
        
        # Create log entry with improved formatting
        if camera_list and message_content:
            log_entry = f"[{timestamp}] {camera_list} - {message_content}"
        elif camera_list:
            log_entry = f"[{timestamp}] {camera_list} - 基线建立触发"
        elif message_content:
            log_entry = f"[{timestamp}] {message_content}"
        else:
            log_entry = f"[{timestamp}] 基线事件"
        
        # Add to text area with automatic scrolling
        current_text = self.baseline_events_text.toPlainText()
        if current_text == "等待基线建立事件...":
            self.baseline_events_text.setPlainText(log_entry)
        else:
            self.baseline_events_text.append(log_entry)
        
        # Implement automatic log scrolling to latest events
        cursor = self.baseline_events_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.baseline_events_text.setTextCursor(cursor)
        self.baseline_events_text.ensureCursorVisible()
        
        # Limit log size to prevent memory issues (keep last 100 entries)
        self._limit_log_size(self.baseline_events_text, 100)
    
    def create_trigger_events_log(self, layout: QVBoxLayout):
        """Create trigger events log display"""
        # Create group box for trigger events
        trigger_group = QGroupBox("触发事件")
        trigger_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        trigger_layout = QVBoxLayout(trigger_group)
        trigger_layout.setContentsMargins(15, 15, 15, 15)
        trigger_layout.setSpacing(8)
        
        # Scrollable text area for receiver trigger events
        self.trigger_events_text = QTextEdit()
        self.trigger_events_text.setMaximumHeight(120)
        self.trigger_events_text.setReadOnly(True)
        self.trigger_events_text.setPlainText("等待触发事件...")
        self.trigger_events_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f8f8;
                border: 1px solid #dddddd;
                border-radius: 3px;
                font-family: monospace;
                font-size: 10px;
            }
        """)
        trigger_layout.addWidget(self.trigger_events_text)
        
        layout.addWidget(trigger_group)
    
    def log_trigger_event(self, device_id: int, timestamp: str, camera_id: int, baseline_count: int, trigger_count: int):
        """Log receiver trigger event with device ID, timestamp, and camera information"""
        # Create log entry with baseline count vs trigger count details and improved formatting
        if device_id >= 0:
            # Successful trigger
            count_diff = baseline_count - trigger_count if baseline_count >= 0 else 0
            log_entry = (f"[{timestamp}] 设备{device_id}触发 - 摄像头{camera_id} | "
                        f"基线: {baseline_count}, 当前: {trigger_count}, "
                        f"差值: {count_diff}")
        else:
            # Failed trigger (device_id = -1)
            log_entry = (f"[{timestamp}] 触发失败 - 摄像头{camera_id} | "
                        f"基线: {baseline_count}, 当前: {trigger_count}")
        
        # Add to text area with automatic scrolling
        current_text = self.trigger_events_text.toPlainText()
        if current_text == "等待触发事件...":
            self.trigger_events_text.setPlainText(log_entry)
        else:
            self.trigger_events_text.append(log_entry)
        
        # Implement automatic log scrolling to latest events
        cursor = self.trigger_events_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.trigger_events_text.setTextCursor(cursor)
        self.trigger_events_text.ensureCursorVisible()
        
        # Limit log size to prevent memory issues (keep last 100 entries)
        self._limit_log_size(self.trigger_events_text, 100)
    
    def create_system_health_indicators(self, layout: QVBoxLayout):
        """Create system health indicators display"""
        # Create group box for system health
        health_group = QGroupBox("系统健康状态")
        health_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        health_layout = QGridLayout(health_group)
        health_layout.setContentsMargins(15, 15, 15, 15)
        health_layout.setSpacing(8)
        
        # Number of cameras initialized and enabled
        cameras_init_label = QLabel("已初始化摄像头:")
        self.cameras_initialized_count = QLabel("0")
        self.cameras_initialized_count.setStyleSheet("font-weight: bold; color: #333333;")
        health_layout.addWidget(cameras_init_label, 0, 0)
        health_layout.addWidget(self.cameras_initialized_count, 0, 1)
        
        cameras_enabled_label = QLabel("已启用摄像头:")
        self.cameras_enabled_count = QLabel("0")
        self.cameras_enabled_count.setStyleSheet("font-weight: bold; color: #333333;")
        health_layout.addWidget(cameras_enabled_label, 1, 0)
        health_layout.addWidget(self.cameras_enabled_count, 1, 1)
        
        # Monitoring active status
        monitoring_label = QLabel("监控状态:")
        self.monitoring_status = QLabel("未激活")
        self.monitoring_status.setStyleSheet("""
            QLabel {
                padding: 2px 6px;
                border-radius: 3px;
                background-color: #ffcccc;
                color: #cc0000;
                font-weight: bold;
            }
        """)
        health_layout.addWidget(monitoring_label, 2, 0)
        health_layout.addWidget(self.monitoring_status, 2, 1)
        
        # Last error messages
        error_label = QLabel("最后错误:")
        self.last_error_text = QTextEdit()
        self.last_error_text.setMaximumHeight(60)
        self.last_error_text.setReadOnly(True)
        self.last_error_text.setPlainText("无错误")
        self.last_error_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f8f8;
                border: 1px solid #dddddd;
                border-radius: 3px;
                font-family: monospace;
                font-size: 10px;
            }
        """)
        health_layout.addWidget(error_label, 3, 0, Qt.AlignTop)
        health_layout.addWidget(self.last_error_text, 3, 1)
        
        layout.addWidget(health_group)
    
    def _limit_log_size(self, text_widget: QTextEdit, max_lines: int):
        """Limit log size by keeping only the most recent entries"""
        try:
            text_content = text_widget.toPlainText()
            lines = text_content.split('\n')
            
            if len(lines) > max_lines:
                # Keep only the last max_lines entries
                recent_lines = lines[-max_lines:]
                text_widget.setPlainText('\n'.join(recent_lines))
                
                # Move cursor to end
                cursor = text_widget.textCursor()
                cursor.movePosition(QTextCursor.End)
                text_widget.setTextCursor(cursor)
        except Exception as e:
            # If there's an error, just continue - don't break logging
            pass
    
    def format_timestamp(self, timestamp=None) -> str:
        """Format timestamp for consistent display in logs"""
        import time
        if timestamp is None:
            timestamp = time.time()
        
        if isinstance(timestamp, (int, float)):
            return time.strftime("%H:%M:%S", time.localtime(timestamp))
        elif isinstance(timestamp, str):
            return timestamp
        else:
            return time.strftime("%H:%M:%S")
    
    def clear_event_logs(self):
        """Clear all event logs"""
        self.baseline_events_text.setPlainText("等待基线建立事件...")
        self.trigger_events_text.setPlainText("等待触发事件...")
    
    def export_event_logs(self) -> dict:
        """Export current event logs for external use"""
        return {
            'baseline_events': self.baseline_events_text.toPlainText(),
            'trigger_events': self.trigger_events_text.toPlainText(),
            'export_time': self.format_timestamp()
        }
    
    def update_system_health(self, cameras_initialized: int, cameras_enabled: int, 
                           monitoring_active: bool, last_error: str = ""):
        """Update system health indicators with enhanced error display"""
        # Update camera counts
        self.cameras_initialized_count.setText(str(cameras_initialized))
        self.cameras_enabled_count.setText(str(cameras_enabled))
        
        # Update monitoring status with more detailed states
        if monitoring_active:
            self.monitoring_status.setText("激活")
            self.monitoring_status.setStyleSheet("""
                QLabel {
                    padding: 2px 6px;
                    border-radius: 3px;
                    background-color: #ccffcc;
                    color: #009900;
                    font-weight: bold;
                }
            """)
        else:
            # Show different states based on error conditions
            if last_error:
                self.monitoring_status.setText("错误")
                self.monitoring_status.setStyleSheet("""
                    QLabel {
                        padding: 2px 6px;
                        border-radius: 3px;
                        background-color: #ffcccc;
                        color: #cc0000;
                        font-weight: bold;
                    }
                """)
            elif cameras_initialized == 0:
                self.monitoring_status.setText("摄像头未初始化")
                self.monitoring_status.setStyleSheet("""
                    QLabel {
                        padding: 2px 6px;
                        border-radius: 3px;
                        background-color: #fff0cc;
                        color: #cc6600;
                        font-weight: bold;
                    }
                """)
            else:
                self.monitoring_status.setText("未激活")
                self.monitoring_status.setStyleSheet("""
                    QLabel {
                        padding: 2px 6px;
                        border-radius: 3px;
                        background-color: #f0f0f0;
                        color: #666666;
                        font-weight: bold;
                    }
                """)
        
        # Update last error with enhanced formatting and timestamp
        if last_error:
            import time
            timestamp = time.strftime("%H:%M:%S")
            error_with_timestamp = f"[{timestamp}] {last_error}"
            
            # Append to existing errors instead of replacing
            current_text = self.last_error_text.toPlainText()
            if current_text == "无错误":
                self.last_error_text.setPlainText(error_with_timestamp)
            else:
                self.last_error_text.append(error_with_timestamp)
            
            # Limit error log size
            self._limit_log_size(self.last_error_text, 20)
            
            self.last_error_text.setStyleSheet("""
                QTextEdit {
                    background-color: #fff0f0;
                    border: 1px solid #ffcccc;
                    border-radius: 3px;
                    font-family: monospace;
                    font-size: 10px;
                    color: #cc0000;
                }
            """)
            
            # Auto-scroll to latest error
            cursor = self.last_error_text.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.last_error_text.setTextCursor(cursor)
            self.last_error_text.ensureCursorVisible()
        else:
            # Only clear if explicitly setting no error
            if not hasattr(self, '_error_cleared') or not self._error_cleared:
                self.last_error_text.setPlainText("无错误")
                self.last_error_text.setStyleSheet("""
                    QTextEdit {
                        background-color: #f8f8f8;
                        border: 1px solid #dddddd;
                        border-radius: 3px;
                        font-family: monospace;
                        font-size: 10px;
                    }
                """)
                self._error_cleared = True
    
    def get_system_status_methods(self) -> dict:
        """Get dictionary of system status update methods for external use"""
        return {
            'update_mqtt_status': self.update_mqtt_status,
            'log_baseline_event': self.log_baseline_event,
            'log_trigger_event': self.log_trigger_event,
            'update_system_health': self.update_system_health,
            'update_camera_info': self.update_camera_info,
            'update_camera_baseline': self.update_camera_baseline,
            'update_camera_current_count': self.update_camera_current_count,
            'update_camera_trigger_status': self.update_camera_trigger_status,
            'reset_camera_monitoring_displays': self.reset_camera_monitoring_displays,
            'get_enabled_cameras': self.get_enabled_cameras,
            'show_error_message': self.show_error_message,
            'show_camera_initialization_error': self.show_camera_initialization_error,
            'clear_all_errors': self.clear_all_errors
        }
    
    def show_error_message(self, error_type: str, message: str, camera_id: int = -1):
        """Show error message in GUI status panel with categorization"""
        import time
        timestamp = time.strftime("%H:%M:%S")
        
        # Format error message based on type
        if camera_id >= 0:
            formatted_message = f"[{timestamp}] {error_type} - 摄像头{camera_id}: {message}"
        else:
            formatted_message = f"[{timestamp}] {error_type}: {message}"
        
        # Add to error log
        current_text = self.last_error_text.toPlainText()
        if current_text == "无错误":
            self.last_error_text.setPlainText(formatted_message)
        else:
            self.last_error_text.append(formatted_message)
        
        # Limit error log size
        self._limit_log_size(self.last_error_text, 50)
        
        # Update error display styling
        self.last_error_text.setStyleSheet("""
            QTextEdit {
                background-color: #fff0f0;
                border: 1px solid #ffcccc;
                border-radius: 3px;
                font-family: monospace;
                font-size: 10px;
                color: #cc0000;
            }
        """)
        
        # Auto-scroll to latest error
        cursor = self.last_error_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.last_error_text.setTextCursor(cursor)
        self.last_error_text.ensureCursorVisible()
        
        # Also log to baseline events for comprehensive tracking
        self.log_baseline_event(timestamp, [camera_id] if camera_id >= 0 else [], formatted_message)
        
        # Reset error cleared flag
        self._error_cleared = False
    
    def show_camera_initialization_error(self, camera_id: int, physical_id: int, error_message: str):
        """Handle camera initialization failures gracefully with detailed error display"""
        # Show error in main error log
        self.show_error_message("摄像头初始化失败", f"物理ID {physical_id}: {error_message}", camera_id)
        
        # Update camera status to show initialization failure
        if 0 <= camera_id < len(self.camera_widgets):
            widget = self.camera_widgets[camera_id]
            widget['camera_status_indicator'].setText("初始化失败")
            widget['camera_status_indicator'].setStyleSheet("""
                QLabel {
                    padding: 2px 6px;
                    border-radius: 3px;
                    background-color: #ffcccc;
                    color: #cc0000;
                    font-weight: bold;
                }
            """)
            widget['camera_status_indicator'].setToolTip(f"初始化失败: {error_message}")
            
            # Add red border to indicate failure
            widget['frame'].setStyleSheet("""
                QFrame {
                    border: 2px solid #cc0000;
                    border-radius: 3px;
                    background-color: #fff5f5;
                    margin: 2px;
                    padding: 5px;
                }
            """)
            
            # Reset monitoring displays
            widget['current_count_display'].setText("--")
            widget['trigger_status_indicator'].setText("初始化失败")
            widget['trigger_status_indicator'].setStyleSheet("""
                QLabel {
                    padding: 2px 6px;
                    border-radius: 3px;
                    background-color: #ffcccc;
                    color: #cc0000;
                    font-weight: bold;
                }
            """)
    
    def clear_all_errors(self):
        """Clear all error displays and reset to normal state"""
        # Clear error log
        self.last_error_text.setPlainText("无错误")
        self.last_error_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f8f8;
                border: 1px solid #dddddd;
                border-radius: 3px;
                font-family: monospace;
                font-size: 10px;
            }
        """)
        
        # Clear camera validation errors
        for camera_id in range(len(self.camera_widgets)):
            self._clear_camera_validation_error(camera_id)
        
        # Clear system parameter errors
        self.autosave_label.setText("自动保存: 就绪")
        self.autosave_label.setStyleSheet("color: #666666; font-style: italic;")
        
        # Set error cleared flag
        self._error_cleared = True


class GuiApplication:
    """Main GUI application class"""
    
    def __init__(self):
        self.app: Optional[QApplication] = None
        self.main_window: Optional[MainWindow] = None
    
    def initialize(self) -> bool:
        """Initialize the GUI application"""
        try:
            # Create QApplication instance
            self.app = QApplication(sys.argv)
            
            # Set application properties
            self.app.setApplicationName("MQTT摄像头监控系统")
            self.app.setApplicationVersion("1.0.0")
            self.app.setOrganizationName("摄像头监控")
            
            # Create main window
            self.main_window = MainWindow()
            
            return True
            
        except Exception as e:
            print(f"GUI应用程序初始化失败: {e}")
            return False
    
    def show(self):
        """Show the main window"""
        if self.main_window:
            self.main_window.show()
    
    def run(self) -> int:
        """Run the GUI application event loop"""
        if not self.app:
            return 1
        
        try:
            # Show main window
            self.show()
            
            # Start event loop
            return self.app.exec()
            
        except Exception as e:
            print(f"GUI应用程序错误: {e}")
            return 1
    
    def quit(self):
        """Quit the application"""
        if self.app:
            self.app.quit()


def main():
    """Main entry point for GUI application"""
    print("启动MQTT摄像头监控GUI...")
    
    # Create and initialize GUI application
    gui_app = GuiApplication()
    
    if not gui_app.initialize():
        print("GUI应用程序初始化失败")
        return 1
    
    # Run the application
    return gui_app.run()


if __name__ == "__main__":
    sys.exit(main())
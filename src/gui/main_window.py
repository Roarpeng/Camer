import cv2
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                               QLabel, QScrollArea, QMessageBox)
from PySide6.QtGui import QImage
from PySide6.QtCore import Slot, Qt

from src.gui.widgets import ImageDisplay, LogViewer, CameraControlWidget
from src.core.camera import CameraThread
from src.core.processor import ImageProcessor
from src.utils.logger import app_logger, SignallingLogHandler
import logging

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Camer - Multi-Camera Monitoring System")
        self.resize(1400, 900)
        
        # Multi-Camera Systems
        self.cameras = []
        self.processors = []
        self.displays = []
        self.controls = []
        self.need_baseline_flags = [False] * 3
        
        # Setup Logger to GUI
        self.log_handler = SignallingLogHandler()
        logging.getLogger("CamerApp").addHandler(self.log_handler)
        
        self.init_ui()
        self.init_logic()
        
        app_logger.info("Application Initialized. 3-Camera Support Ready.")

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # --- Left Panel: Controls ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setFixedWidth(280)
        
        left_layout.addWidget(QLabel("<h3>Camera Controls</h3>"))
        for i in range(3):
            ctrl = CameraControlWidget(i)
            self.controls.append(ctrl)
            left_layout.addWidget(ctrl)
        
        left_layout.addStretch()
        main_layout.addWidget(left_panel)
        
        # --- Center Panel: Monitors ---
        center_scroll = QScrollArea()
        center_scroll.setWidgetResizable(True)
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        
        for i in range(3):
            display = ImageDisplay()
            display.setText(f"Camera {i+1} Off")
            self.displays.append(display)
            center_layout.addWidget(display)
            center_layout.addWidget(QLabel(f"Monitor {i+1}"))
            
        center_scroll.setWidget(center_widget)
        main_layout.addWidget(center_scroll, stretch=3)
        
        # --- Right Panel: Logs ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_panel.setFixedWidth(350)
        
        self.log_viewer = LogViewer()
        right_layout.addWidget(self.log_viewer)
        
        main_layout.addWidget(right_panel)

    def init_logic(self):
        # Logger signal
        self.log_handler.log_signal.connect(self.log_viewer.append_log)
        
        for i in range(3):
            # Processor
            proc = ImageProcessor()
            self.processors.append(proc)
            
            # Camera Thread
            cam = CameraThread(camera_index=i)
            self.cameras.append(cam)
            
            # Connections
            # Use lambda with default argument to capture 'i' correctly in the loop
            cam.frame_received.connect(lambda frame, idx=i: self.process_frame(frame, idx))
            cam.error_occurred.connect(lambda err, idx=i: self.handle_camera_error(err, idx))
            
            # Control Connections
            ctrl = self.controls[i]
            ctrl.activated.connect(lambda active, idx=i: self.toggle_camera(active, idx))
            ctrl.mask_changed.connect(lambda path, idx=i: self.on_mask_changed(path, idx))
            ctrl.reset_baseline.connect(lambda idx=i: self.on_reset_baseline(idx))

    def handle_camera_error(self, err, idx):
        app_logger.error(f"Cam {idx+1}: {err}")
        # Only show popup for critical "Cannot open" errors
        if "Cannot open" in err:
            QMessageBox.warning(self, "Camera Error", f"Failed to activate Camera {idx+1}.\n{err}")
            # Reset checkbox
            self.controls[idx].check_active.setChecked(False)

    @Slot(bool, int)
    def toggle_camera(self, active, idx):
        cam = self.cameras[idx]
        if active:
            if not cam.isRunning():
                cam.start()
                app_logger.info(f"Camera {idx+1} activation requested...")
        else:
            if cam.isRunning():
                cam.stop()
                self.displays[idx].setText(f"Camera {idx+1} Disconnected")
                app_logger.info(f"Camera {idx+1} deactivated.")


    @Slot(str, int)
    def on_mask_changed(self, path, idx):
        self.processors[idx].set_mask(path)
        app_logger.info(f"Camera {idx+1} mask updated.")

    @Slot(int)
    def on_reset_baseline(self, idx):
        self.need_baseline_flags[idx] = True
        app_logger.info(f"Camera {idx+1} baseline reset requested.")

    @Slot(object, int)
    def process_frame(self, frame, idx):
        processor = self.processors[idx]
        display = self.displays[idx]
        
        # 1. Update Baseline if requested
        if self.need_baseline_flags[idx]:
            processor.set_baseline(frame)
            self.need_baseline_flags[idx] = False
            
        # 2. Process
        vis_frame, is_triggered, diff_val = processor.process(frame)
        
        # 3. Display Image (Convert BGR to RGB to QImage)
        rgb_frame = cv2.cvtColor(vis_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        display.update_image(q_img)

    def closeEvent(self, event):
        for cam in self.cameras:
            cam.stop()
        super().closeEvent(event)


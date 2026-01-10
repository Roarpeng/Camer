import cv2
import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                               QLabel, QScrollArea, QMessageBox)
from PySide6.QtGui import QImage, QPainter
from PySide6.QtCore import Slot, Qt

from src.gui.widgets import ImageDisplay, LogViewer, CameraControlWidget, MqttConfigWidget
from src.core.camera import CameraThread
from src.core.processor import ImageProcessor
from src.core.mqtt_client import MqttWorker
from src.utils.logger import app_logger, SignallingLogHandler
from src.utils.config import ConfigManager
import logging
import time

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Camer - 多摄像头监控系统")
        self.resize(1400, 900)
        self.setMinimumSize(1000, 600)  # 设置最小尺寸，但允许更大
        
        # Multi-Camera Systems
        self.cameras = []
        self.processors = []
        self.displays = []
        self.controls = []
        self.need_baseline_flags = [False] * 8
        self.last_scan_times = [0.0] * 8
        self.brightness_reported_flags = [False] * 8
        self.scan_intervals = [300] * 8  # 默认300ms
        
        # 基线延时相关
        self.baseline_delay = 1000  # 默认延时1秒
        self.baseline_trigger_time = 0.0  # 触发时间戳
        self.baseline_pending = False  # 是否有待处理的基线建立
        
        # Config Manager
        self.config_manager = ConfigManager()
        
        # MQTT
        broker = self.config_manager.get_mqtt_broker()
        client_id = self.config_manager.get_client_id()
        subscribe_topics = self.config_manager.get_subscribe_topics()
        publish_topic = self.config_manager.get_publish_topic()
        self.mqtt_worker = MqttWorker(broker=broker, client_id=client_id, topics=subscribe_topics, publish_topic=publish_topic)
        self.mqtt_worker.start()
        
        # Setup Logger to GUI
        self.log_handler = SignallingLogHandler()
        logging.getLogger("CamerApp").addHandler(self.log_handler)
        
        self.init_ui()
        self.init_logic()
        self.load_config()
        
        app_logger.info("程序已初始化。八路摄像头支持已就绪。")

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # --- Left Panel: Controls with Scroll Area ---
        left_scroll = QScrollArea()
        left_scroll.setFixedWidth(340)  # Slightly wider to account for scrollbar
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_scroll.setFrameShape(QScrollArea.NoFrame)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(0)  # Spacing handled by the widgets themselves
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        label_title = QLabel("摄像头控制")
        label_title.setProperty("h3", True)
        label_title.setContentsMargins(16, 16, 16, 0)
        left_layout.addWidget(label_title)
        
        self.mqtt_config = MqttConfigWidget()
        left_layout.addWidget(self.mqtt_config)
        
        for i in range(8):
            ctrl = CameraControlWidget(i)
            self.controls.append(ctrl)
            left_layout.addWidget(ctrl)
        
        left_layout.addStretch()
        left_scroll.setWidget(left_panel)
        main_layout.addWidget(left_scroll)
        
        # --- Center Panel: Monitors ---
        center_scroll = QScrollArea()
        center_scroll.setWidgetResizable(True)
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        
        for i in range(8):
            display = ImageDisplay()
            display.setText(f"摄像头 {i+1} 已关闭")
            self.displays.append(display)
            center_layout.addWidget(display)
            center_layout.addWidget(QLabel(f"监控画面 {i+1}"))
            
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
        
        for i in range(8):
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
            ctrl.threshold_changed.connect(lambda val, idx=i: self.on_threshold_changed(val, idx))
            ctrl.min_area_changed.connect(lambda val, idx=i: self.on_min_area_changed(val, idx))
            ctrl.scan_interval_changed.connect(lambda val, idx=i: self.on_scan_interval_changed(val, idx))

        # MQTT Signal
        self.mqtt_config.config_updated.connect(self.on_mqtt_config_updated)
        self.mqtt_config.auto_connect_changed.connect(self.on_auto_connect_changed)
        self.mqtt_config.baseline_delay_changed.connect(self.on_baseline_delay_changed)
        self.mqtt_worker.reset_signal.connect(self.on_mqtt_trigger)
        self.mqtt_worker.status_changed.connect(self.mqtt_config.update_status)

    def load_config(self):
        """从配置管理器加载配置并应用到UI"""
        # 加载 MQTT 配置
        broker = self.config_manager.get_mqtt_broker()
        self.mqtt_config.edit_broker.setText(broker)
        
        # 加载 Client ID
        client_id = self.config_manager.get_client_id()
        self.mqtt_config.edit_client_id.setText(client_id)
        
        # 加载订阅主题
        subscribe_topics = self.config_manager.get_subscribe_topics()
        self.mqtt_config.edit_subscribe.setText(",".join(subscribe_topics))
        
        # 加载发布主题
        publish_topic = self.config_manager.get_publish_topic()
        self.mqtt_config.edit_publish.setText(publish_topic)
        
        # 加载自动连接配置
        auto_connect = self.config_manager.get_auto_connect()
        self.mqtt_config.check_auto_connect.blockSignals(True)
        self.mqtt_config.check_auto_connect.setChecked(auto_connect)
        self.mqtt_config.check_auto_connect.blockSignals(False)
        
        # 如果配置为自动连接，则自动连接 broker
        if auto_connect:
            app_logger.info("配置为自动连接，正在连接 MQTT Broker...")
            self.mqtt_worker.reconnect(broker=broker, client_id=client_id, subscribe_topics=subscribe_topics, publish_topic=publish_topic)
        
        # 加载基线延时配置
        self.baseline_delay = self.config_manager.get_baseline_delay()
        self.mqtt_config.slider_baseline_delay.blockSignals(True)
        self.mqtt_config.slider_baseline_delay.setValue(self.baseline_delay)
        self.mqtt_config.slider_baseline_delay.blockSignals(False)
        
        # 加载摄像头配置
        for i in range(8):
            cam_config = self.config_manager.get_camera_config(i)
            if cam_config:
                ctrl = self.controls[i]
                
                # 设置激活状态（不触发信号）
                ctrl.check_active.blockSignals(True)
                ctrl.check_active.setChecked(cam_config.get("active", False))
                ctrl.check_active.blockSignals(False)
                
                # 设置掩码
                mask = cam_config.get("mask", "")
                if mask:
                    index = ctrl.combo_mask.findText(os.path.basename(mask))
                    if index >= 0:
                        ctrl.combo_mask.setCurrentIndex(index)
                
                # 设置阈值
                ctrl.slider_thresh.blockSignals(True)
                ctrl.slider_thresh.setValue(cam_config.get("threshold", 50))
                ctrl.slider_thresh.blockSignals(False)
                
                # 设置最小面积
                ctrl.slider_area.blockSignals(True)
                ctrl.slider_area.setValue(cam_config.get("min_area", 500))
                ctrl.slider_area.blockSignals(False)
                
                # 设置扫描间隔
                ctrl.slider_interval.blockSignals(True)
                ctrl.slider_interval.setValue(cam_config.get("scan_interval", 300))
                ctrl.slider_interval.blockSignals(False)
                
                # 应用到处理器
                self.processors[i].threshold = cam_config.get("threshold", 50)
                self.processors[i].min_area = cam_config.get("min_area", 500)
                self.scan_intervals[i] = cam_config.get("scan_interval", 300)
                
                # 如果掩码路径存在，应用到处理器
                if mask and os.path.exists(mask):
                    self.processors[i].set_mask(mask)
                
                # 如果配置为激活，则自动激活摄像头
                if cam_config.get("active", False):
                    app_logger.info(f"配置为自动激活，正在启动摄像头 {i+1}...")
                    self.toggle_camera(True, i)
        
        app_logger.info("配置加载完成。")

    def on_mqtt_config_updated(self, broker, client_id, subscribe_topics, publish_topic):
        app_logger.info(f"正在更新 MQTT 配置 - Broker: {broker}, Client ID: {client_id}, 订阅: {subscribe_topics}, 发布: {publish_topic}")
        self.config_manager.set_mqtt_broker(broker)
        self.config_manager.set_client_id(client_id)
        self.config_manager.set_subscribe_topics(subscribe_topics)
        self.config_manager.set_publish_topic(publish_topic)
        self.mqtt_worker.reconnect(broker=broker, client_id=client_id, subscribe_topics=subscribe_topics, publish_topic=publish_topic)

    @Slot(bool)
    def on_auto_connect_changed(self, auto_connect):
        self.config_manager.set_auto_connect(auto_connect)
        app_logger.info(f"自动连接设置已更新: {auto_connect}")

    def on_mqtt_trigger(self):
        """Triggered by MQTT to reset all baselines (with delay)"""
        self.baseline_trigger_time = time.time()
        self.baseline_pending = True
        app_logger.info(f"收到 MQTT 触发信号：{self.baseline_delay}ms 后重置所有摄像头基准。")
    
    @Slot(int)
    def on_baseline_delay_changed(self, val):
        """Handle baseline delay change from UI"""
        self.baseline_delay = val
        self.config_manager.set_baseline_delay(val)
        app_logger.info(f"基线延时已更新为: {val}ms")

    def handle_camera_error(self, err, idx):
        app_logger.error(f"摄像头 {idx+1}: {err}")
        # Only show popup for critical "Cannot open" errors
        if "Cannot open" in err:
            QMessageBox.warning(self, "摄像头错误", f"无法激活摄像头 {idx+1}。\n{err}")
            # Reset checkbox
            self.controls[idx].check_active.setChecked(False)

    @Slot(bool, int)
    def toggle_camera(self, active, idx):
        cam = self.cameras[idx]
        if active:
            if not cam.isRunning():
                cam.start()
                app_logger.info(f"正在请求激活摄像头 {idx+1}...")
        else:
            if cam.isRunning():
                cam.stop()
                self.displays[idx].setText(f"摄像头 {idx+1} 已断开连接")
                app_logger.info(f"摄像头 {idx+1} 已停用。")
        
        # 保存配置
        self.config_manager.set_camera_active(idx, active)


    @Slot(str, int)
    def on_mask_changed(self, path, idx):
        self.processors[idx].set_mask(path)
        self.config_manager.set_camera_mask(idx, path)
        app_logger.info(f"摄像头 {idx+1} 遮罩已更新。")

    @Slot(int, int)
    def on_threshold_changed(self, val, idx):
        self.processors[idx].threshold = val
        self.config_manager.set_camera_threshold(idx, val)
        app_logger.debug(f"摄像头 {idx+1} 阈值已更新为: {val}")

    @Slot(int, int)
    def on_min_area_changed(self, val, idx):
        self.processors[idx].min_area = val
        self.config_manager.set_camera_min_area(idx, val)
        app_logger.debug(f"摄像头 {idx+1} 最小面积已更新为: {val}")

    @Slot(int, int)
    def on_scan_interval_changed(self, val, idx):
        self.scan_intervals[idx] = val
        self.config_manager.set_camera_scan_interval(idx, val)
        app_logger.info(f"摄像头 {idx+1} 扫描间隔已更新为: {val}ms")

    @Slot(int)
    def on_reset_baseline(self, idx):
        self.need_baseline_flags[idx] = True
        self.brightness_reported_flags[idx] = False
        app_logger.info(f"摄像头 {idx+1} 基准重置请求已发送。")

    @Slot(object, int)
    def process_frame(self, frame, idx):
        processor = self.processors[idx]
        display = self.displays[idx]

        # 0. 检查延时基线建立（使用 currenttime - lasttime 逻辑）
        current_time = time.time()
        if self.baseline_pending:
            delay_sec = self.baseline_delay / 1000.0  # 转换为秒
            if (current_time - self.baseline_trigger_time) >= delay_sec:
                self.baseline_pending = False
                app_logger.info("延时完成，正在重置所有摄像头基准...")
                for i in range(8):
                    self.on_reset_baseline(i)

        # 1. Update Baseline if requested
        if self.need_baseline_flags[idx]:
            processor.set_baseline(frame)
            self.need_baseline_flags[idx] = False

        # 2. Process（现在返回亮度值，避免重复计算）
        vis_frame, is_triggered, diff_val, current_brightness = processor.process(frame)

        # 3. ROI Brightness Scan（使用处理器返回的亮度值，避免重复计算）
        scan_interval_sec = self.scan_intervals[idx] / 1000.0  # 转换为秒
        if (current_time - self.last_scan_times[idx]) >= scan_interval_sec:
            self.last_scan_times[idx] = current_time
            if processor.baseline_brightness is not None:
                # 使用处理器返回的亮度值，避免重复的 cv2.cvtColor 和 cv2.mean
                if abs(current_brightness - processor.baseline_brightness) > processor.threshold:
                    # 只在未上报过时才上报
                    if not self.brightness_reported_flags[idx]:
                        publish_topic = self.config_manager.get_publish_topic()
                        self.mqtt_worker.publish(publish_topic, "")
                        self.brightness_reported_flags[idx] = True
                        app_logger.info(f"摄像头 {idx+1} 亮度变化触发上报：{current_brightness:.2f} (基准: {processor.baseline_brightness:.2f})")

        # 4. Display Image (Convert BGR to RGB to QImage)
        rgb_frame = cv2.cvtColor(vis_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)

        display.update_image(q_img)

    def closeEvent(self, event):
        self.mqtt_worker.stop()
        for cam in self.cameras:
            cam.stop()
        super().closeEvent(event)


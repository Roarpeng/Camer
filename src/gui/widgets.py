from PySide6.QtWidgets import (QWidget, QLabel, QTextEdit, QVBoxLayout, 
                               QHBoxLayout, QCheckBox, QComboBox, QPushButton, 
                               QGroupBox, QFormLayout, QSlider, QLineEdit)
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt, Signal, Slot
import os
import sys

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    return os.path.join(base_path, relative_path)

class ImageDisplay(QLabel):
    """
    Subclass of QLabel optimized for displaying OpenCV images.
    """
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setText("无信号")
        self.setStyleSheet("background-color: #E0E0E0; color: #757575; border: 1px solid #BDBDBD; border-radius: 4px;")
        self.setMinimumSize(320, 240) # Smaller for multi-view
        self.setScaledContents(True)

    @Slot(object)
    def update_image(self, qt_image):
        """Receives a QImage and displays it."""
        self.setPixmap(QPixmap.fromImage(qt_image))

class LogViewer(QWidget):
    """
    Widget containing a QTextEdit for logs.
    """
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setStyleSheet("background-color: #1e1e1e; color: #dcdcdc; font-family: Consolas; font-size: 10pt;")
        
        layout.addWidget(QLabel("<b>系统日志</b>"))
        layout.addWidget(self.text_area)

    @Slot(str)
    def append_log(self, message):
        self.text_area.append(message)
        # Scroll to bottom
        sb = self.text_area.verticalScrollBar()
        sb.setValue(sb.maximum())

class CameraControlWidget(QGroupBox):
    """
    Individual control panel for one camera.
    """
    activated = Signal(bool)
    mask_changed = Signal(str)
    reset_baseline = Signal()
    threshold_changed = Signal(int)
    min_area_changed = Signal(int)

    def __init__(self, camera_id):
        super().__init__(f"摄像头 {camera_id + 1}")
        self.camera_id = camera_id
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)
        
        self.check_active = QCheckBox("激活")
        self.combo_mask = QComboBox()
        self.btn_reset = QPushButton("重置基准")
        
        # Sensitivity (Threshold)
        self.slider_thresh = QSlider(Qt.Horizontal)
        self.slider_thresh.setRange(1, 255)
        self.slider_thresh.setValue(50)
        
        # Min Area (Noise Filter)
        self.slider_area = QSlider(Qt.Horizontal)
        self.slider_area.setRange(1, 5000)
        self.slider_area.setValue(500)
        
        # Populate mask combo
        self.data_dir = get_resource_path('data')
        
        if os.path.exists(self.data_dir):
            masks = [f for f in os.listdir(self.data_dir) if f.lower().endswith(('.png', '.jpg'))]
            self.combo_mask.addItem("不使用遮罩")
            self.combo_mask.addItems(masks)
        else:
            # Fallback for logging/debugging
            print(f"Data directory not found at: {self.data_dir}")
        
        layout.addRow(self.check_active)
        layout.addRow("遮罩:", self.combo_mask)
        layout.addRow("灵敏度:", self.slider_thresh)
        layout.addRow("最小面积:", self.slider_area)
        layout.addRow(self.btn_reset)
        
        # Connections
        self.check_active.toggled.connect(self.activated.emit)
        self.combo_mask.currentTextChanged.connect(self.on_mask_changed)
        self.btn_reset.clicked.connect(self.reset_baseline.emit)
        self.slider_thresh.valueChanged.connect(self.threshold_changed.emit)
        self.slider_area.valueChanged.connect(self.min_area_changed.emit)

    def on_mask_changed(self, text):
        if text == "不使用遮罩":
            self.mask_changed.emit("")
        else:
            path = os.path.join(self.data_dir, text)
            self.mask_changed.emit(path)

class MqttConfigWidget(QGroupBox):
    """
    Control for MQTT Broker configuration.
    """
    config_updated = Signal(str, list, str)

    def __init__(self):
        super().__init__("MQTT 配置")
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)
        self.edit_broker = QLineEdit("localhost")
        
        # 订阅主题配置
        self.edit_subscribe = QLineEdit("changeState,receiver")
        self.edit_subscribe.setPlaceholderText("多个主题用逗号分隔")
        
        # 发布主题配置
        self.edit_publish = QLineEdit("receiver")
        
        self.btn_update = QPushButton("连接/更新")
        
        layout.addRow("Broker:", self.edit_broker)
        layout.addRow("订阅主题:", self.edit_subscribe)
        layout.addRow("发布主题:", self.edit_publish)
        layout.addRow(self.btn_update)
        
        self.btn_update.clicked.connect(lambda: self.on_btn_clicked())

    def on_btn_clicked(self):
        self.btn_update.setText("正在连接...")
        self.btn_update.setEnabled(False)
        
        # 解析订阅主题
        subscribe_text = self.edit_subscribe.text().strip()
        subscribe_topics = [t.strip() for t in subscribe_text.split(",") if t.strip()]
        
        # 获取发布主题
        publish_topic = self.edit_publish.text().strip()
        
        self.config_updated.emit(self.edit_broker.text(), subscribe_topics, publish_topic)

    @Slot(bool, str)
    def update_status(self, connected, message):
        self.btn_update.setEnabled(True)
        self.btn_update.setText(f"连接/更新 ({message})")
        if connected:
            self.btn_update.setStyleSheet("background-color: #4CAF50; color: white;") # Material Green
        else:
            self.btn_update.setStyleSheet("") # Reset to default (Material Purple)


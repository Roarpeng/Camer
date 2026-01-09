from PySide6.QtWidgets import (QWidget, QLabel, QTextEdit, QVBoxLayout, 
                               QHBoxLayout, QCheckBox, QComboBox, QPushButton, 
                               QGroupBox, QFormLayout, QSlider, QLineEdit, QSpacerItem, QSizePolicy)
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt, Signal, Slot
import os
import sys

def get_resource_path(relative_path):
    """ 获取资源绝对路径 """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, relative_path)


class ImageDisplay(QLabel):
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setText("无信号")
        self.setProperty("display", True)
        self.setMinimumSize(320, 240)
        self.setScaledContents(True)

    @Slot(object)
    def update_image(self, qt_image):
        self.setPixmap(QPixmap.fromImage(qt_image))


class LogViewer(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("系统日志")
        title.setProperty("h3", True)
        
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setProperty("log", True)
        
        layout.addWidget(title)
        layout.addWidget(self.text_area)

    @Slot(str)
    def append_log(self, message):
        self.text_area.append(message)
        sb = self.text_area.verticalScrollBar()
        sb.setValue(sb.maximum())


class LabeledSlider(QWidget):
    """
    垂直堆叠滑块：标题行(左对齐标题+右对齐数值) + 滑块
    """
    valueChanged = Signal(int)
    
    def __init__(self, label_text, min_val, max_val, default_val, suffix=""):
        super().__init__()
        self.suffix = suffix
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(6)
        
        # 第一行：Header
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        
        lbl_name = QLabel(label_text)
        lbl_name.setProperty("label", True)
        
        self.lbl_value = QLabel(f"{default_val}{suffix}")
        self.lbl_value.setStyleSheet("color: #1890FF; font-weight: 600;")
        
        header.addWidget(lbl_name)
        header.addStretch()
        header.addWidget(self.lbl_value)
        layout.addLayout(header)
        
        # 第二行：Slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(min_val, max_val)
        self.slider.setValue(default_val)
        self.slider.setMinimumHeight(24)
        layout.addWidget(self.slider)
        
        self.slider.valueChanged.connect(self._on_value_changed)
    
    def _on_value_changed(self, val):
        self.lbl_value.setText(f"{val}{self.suffix}")
        self.valueChanged.emit(val)
    
    def setValue(self, val):
        self.slider.setValue(val)
    
    def value(self):
        return self.slider.value()
    
    def blockSignals(self, block):
        self.slider.blockSignals(block)


class CameraControlWidget(QGroupBox):
    activated = Signal(bool)
    mask_changed = Signal(str)
    reset_baseline = Signal()
    threshold_changed = Signal(int)
    min_area_changed = Signal(int)
    scan_interval_changed = Signal(int)

    def __init__(self, camera_id):
        super().__init__(f"摄像头 {camera_id + 1}")
        self.camera_id = camera_id
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 28, 16, 16)
        
        # 激活状态
        self.check_active = QCheckBox("激活摄像头监控")
        layout.addWidget(self.check_active)
        
        # 遮罩选择 (垂直对齐)
        mask_vbox = QVBoxLayout()
        mask_vbox.setSpacing(6)
        lbl_mask = QLabel("处理遮罩")
        lbl_mask.setProperty("label", True)
        self.combo_mask = QComboBox()
        mask_vbox.addWidget(lbl_mask)
        mask_vbox.addWidget(self.combo_mask)
        layout.addLayout(mask_vbox)
        
        # 滑块
        self.slider_thresh = LabeledSlider("检测阈值", 1, 255, 50)
        self.slider_area = LabeledSlider("最小物体面积", 1, 5000, 500)
        self.slider_interval = LabeledSlider("对比扫描间隔", 100, 5000, 300, "ms")
        
        layout.addWidget(self.slider_thresh)
        layout.addWidget(self.slider_area)
        layout.addWidget(self.slider_interval)
        
        # 按钮排版
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_reset = QPushButton("重捕获基准")
        self.btn_reset.setProperty("secondary", True)
        self.btn_reset.setFixedWidth(100)
        btn_layout.addWidget(self.btn_reset)
        layout.addLayout(btn_layout)
        
        # 加载数据
        self.data_dir = get_resource_path('data')
        if os.path.exists(self.data_dir):
            masks = [f for f in os.listdir(self.data_dir) if f.lower().endswith(('.png', '.jpg'))]
            self.combo_mask.addItem("不使用遮罩")
            self.combo_mask.addItems(masks)
            
        # 事件
        self.check_active.toggled.connect(self.activated.emit)
        self.combo_mask.currentTextChanged.connect(self.on_mask_changed)
        self.btn_reset.clicked.connect(self.reset_baseline.emit)
        self.slider_thresh.valueChanged.connect(self.threshold_changed.emit)
        self.slider_area.valueChanged.connect(self.min_area_changed.emit)
        self.slider_interval.valueChanged.connect(self.scan_interval_changed.emit)

    def on_mask_changed(self, text):
        if text == "不使用遮罩":
            self.mask_changed.emit("")
        else:
            self.mask_changed.emit(os.path.join(self.data_dir, text))


class MqttConfigWidget(QGroupBox):
    config_updated = Signal(str, str, list, str)
    auto_connect_changed = Signal(bool)

    def __init__(self):
        super().__init__("MQTT 服务配置")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(16, 32, 16, 16)
        
        def add_field(label_text, default_val):
            vbox = QVBoxLayout()
            vbox.setSpacing(6)
            lbl = QLabel(label_text)
            lbl.setProperty("label", True)
            edit = QLineEdit(default_val)
            vbox.addWidget(lbl)
            vbox.addWidget(edit)
            layout.addLayout(vbox)
            return edit
            
        self.edit_broker = add_field("Broker IP 地址", "localhost")
        self.edit_client_id = add_field("MQTT 客户端 ID", "camer")
        self.edit_subscribe = add_field("订阅主题 (逗号分隔)", "changeState,receiver")
        self.edit_publish = add_field("发布结果主题", "receiver")
        
        self.check_auto_connect = QCheckBox("启动时自动尝试连接")
        self.check_auto_connect.setChecked(True)
        layout.addWidget(self.check_auto_connect)
        
        self.btn_update = QPushButton("更新并连接 MQTT")
        self.btn_update.setFixedHeight(36)
        layout.addWidget(self.btn_update)
        
        self.btn_update.clicked.connect(self.on_btn_clicked)
        self.check_auto_connect.toggled.connect(self.auto_connect_changed.emit)

    def on_btn_clicked(self):
        self.btn_update.setText("正在连接...")
        self.btn_update.setEnabled(False)
        client_id = self.edit_client_id.text().strip()
        sub_text = self.edit_subscribe.text().strip()
        topics = [t.strip() for t in sub_text.split(",") if t.strip()]
        self.config_updated.emit(self.edit_broker.text(), client_id, topics, self.edit_publish.text().strip())

    @Slot(bool, str)
    def update_status(self, connected, message):
        self.btn_update.setEnabled(True)
        self.btn_update.setText(f"连接 / 更新 ({message})")
        if connected:
            self.btn_update.setStyleSheet("background-color: #52C41A; color: white;")
        else:
            self.btn_update.setStyleSheet("")

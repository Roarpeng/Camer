from PySide6.QtWidgets import (QWidget, QLabel, QTextEdit, QVBoxLayout, 
                               QHBoxLayout, QCheckBox, QComboBox, QPushButton, 
                               QGroupBox, QFormLayout)
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
        self.setText("No Signal")
        self.setStyleSheet("background-color: black; color: white; border: 1px solid #444;")
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
        
        layout.addWidget(QLabel("<b>System Log</b>"))
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

    def __init__(self, camera_id):
        super().__init__(f"Camera {camera_id + 1}")
        self.camera_id = camera_id
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)
        
        self.check_active = QCheckBox("Active")
        self.combo_mask = QComboBox()
        self.btn_reset = QPushButton("Reset Baseline")
        
        # Populate mask combo
        self.data_dir = get_resource_path('data')
        
        if os.path.exists(self.data_dir):
            masks = [f for f in os.listdir(self.data_dir) if f.lower().endswith(('.png', '.jpg'))]
            self.combo_mask.addItem("No Mask")
            self.combo_mask.addItems(masks)
        else:
            # Fallback for logging/debugging
            print(f"Data directory not found at: {self.data_dir}")
        
        layout.addRow(self.check_active)
        layout.addRow("Mask:", self.combo_mask)
        layout.addRow(self.btn_reset)
        
        # Connections
        self.check_active.toggled.connect(self.activated.emit)
        self.combo_mask.currentTextChanged.connect(self.on_mask_changed)
        self.btn_reset.clicked.connect(self.reset_baseline.emit)

    def on_mask_changed(self, text):
        if text == "No Mask":
            self.mask_changed.emit("")
        else:
            path = os.path.join(self.data_dir, text)
            self.mask_changed.emit(path)


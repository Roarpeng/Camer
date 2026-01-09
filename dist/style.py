TECHNO_STYLE = """
/* 主窗口 - 深色科技背景 */
QMainWindow {
    background-color: #0A0E27;
}

/* 通用控件样式 */
QWidget {
    background-color: #0A0E27;
    color: #00F0FF;
    font-family: 'Microsoft YaHei', 'Segoe UI', 'SimHei', sans-serif;
    font-size: 16pt;
    selection-background-color: #00F0FF;
    selection-color: #0A0E27;
}

/* 标签样式 */
QLabel {
    background-color: transparent;
    color: #00F0FF;
    border: none;
}

QLabel[h3="true"] {
    color: #00F0FF;
    font-size: 18pt;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 1px;
    padding: 12px 0;
}

/* 分组框 - 科技感边框 */
QGroupBox {
    border: 2px solid #00F0FF;
    border-radius: 6px;
    margin-top: 2em;
    padding: 16px;
    font-weight: bold;
    color: #00F0FF;
    background-color: rgba(10, 14, 39, 0.8);
    font-size: 16pt;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 15px;
    padding: 0 8px 0 8px;
    color: #00F0FF;
    background-color: #0A0E27;
    font-size: 17pt;
}

/* 按钮 - 霓虹灯效果 */
QPushButton {
    background-color: transparent;
    color: #00F0FF;
    border: 2px solid #00F0FF;
    border-radius: 4px;
    padding: 14px 28px;
    font-weight: bold;
    font-size: 16pt;
    letter-spacing: 0.5px;
    min-height: 48px;
}

QPushButton:hover {
    background-color: rgba(0, 240, 255, 0.2);
    border-color: #00FFAA;
    color: #00FFAA;
}

QPushButton:pressed {
    background-color: rgba(0, 240, 255, 0.4);
    color: #00FFAA;
}

QPushButton:disabled {
    border-color: #4A5568;
    color: #4A5568;
}

/* 复选框 */
QCheckBox {
    spacing: 16px;
    color: #00F0FF;
    font-size: 16pt;
}

QCheckBox::indicator {
    width: 26px;
    height: 26px;
    border: 2px solid #00F0FF;
    border-radius: 3px;
    background-color: transparent;
}

QCheckBox::indicator:hover {
    border-color: #00FFAA;
}

QCheckBox::indicator:checked {
    background-color: #00F0FF;
    border-color: #00F0FF;
}

QCheckBox::indicator:checked:hover {
    background-color: #00FFAA;
    border-color: #00FFAA;
}

/* 下拉框 */
QComboBox {
    background-color: #1A1F3A;
    border: 2px solid #00F0FF;
    border-radius: 4px;
    padding: 14px 18px;
    color: #00F0FF;
    font-size: 16pt;
    min-height: 48px;
}

QComboBox:hover {
    border-color: #00FFAA;
}

QComboBox:on {
    border-color: #00FFAA;
}

QComboBox QAbstractItemView {
    background-color: #1A1F3A;
    border: 2px solid #00F0FF;
    color: #00F0FF;
    selection-background-color: #00F0FF;
    selection-color: #0A0E27;
    outline: none;
}

QComboBox::drop-down {
    border: none;
    width: 28px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 7px solid #00F0FF;
    margin-right: 8px;
}

QComboBox::down-arrow:hover {
    border-top-color: #00FFAA;
}

/* 文本输入框 */
QLineEdit {
    background-color: #1A1F3A;
    border: 2px solid #00F0FF;
    border-radius: 4px;
    padding: 14px 18px;
    color: #00F0FF;
    font-size: 16pt;
    min-height: 48px;
    selection-background-color: #00F0FF;
    selection-color: #0A0E27;
}

QLineEdit:hover {
    border-color: #00FFAA;
}

QLineEdit:focus {
    border-color: #00FFAA;
    outline: none;
}

/* 滑块 - 科技感 */
QSlider::groove:horizontal {
    border: none;
    height: 10px;
    background: #1A1F3A;
    margin: 2px 0;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #00F0FF;
    border: 2px solid #00F0FF;
    width: 24px;
    height: 24px;
    margin: -9px 0;
    border-radius: 12px;
}

QSlider::handle:horizontal:hover {
    background: #00FFAA;
    border-color: #00FFAA;
}

/* 滚动区域 */
QScrollArea {
    border: none;
    background-color: transparent;
}

/* 滚动条 */
QScrollBar:vertical {
    border: 2px solid #00F0FF;
    background: #1A1F3A;
    width: 12px;
    margin: 0px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background: #00F0FF;
    min-height: 28px;
    border-radius: 5px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background: #00FFAA;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: 2px solid #00F0FF;
    background: #1A1F3A;
    height: 12px;
    margin: 0px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal {
    background: #00F0FF;
    min-width: 28px;
    border-radius: 5px;
    margin: 2px;
}

QScrollBar::handle:horizontal:hover {
    background: #00FFAA;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* 文本编辑器 */
QTextEdit {
    background-color: #0A0E27;
    border: 2px solid #00F0FF;
    border-radius: 4px;
    color: #00F0FF;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 10pt;
}

QTextEdit:focus {
    border-color: #00FFAA;
    outline: none;
}

/* 图像显示 */
QLabel[display="true"] {
    background-color: #000000;
    border: 2px solid #00F0FF;
    border-radius: 4px;
    color: #4A5568;
}

QLabel[display="true"]:hover {
    border-color: #00FFAA;
}

/* 日志区域 */
QTextEdit[log="true"] {
    background-color: #0A0E27;
    border: 2px solid #00F0FF;
    border-radius: 4px;
    color: #00F0FF;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 10pt;
}

QTextEdit[log="true"]::selection {
    background-color: #00F0FF;
    color: #0A0E27;
}
"""

"""
Ant Design 风格工业级 UI 样式表 - 垂直堆叠优化版
"""

TECHNO_STYLE = """
/* 全局背景 */
QMainWindow {
    background-color: #F0F2F5;
}

/* 基础文字与控件 */
QWidget {
    background-color: transparent;
    color: #262626;
    font-family: 'Microsoft YaHei UI', 'Segoe UI', sans-serif;
    font-size: 14px;
}

/* 顶部标题栏样式的标签 */
QLabel[h3="true"] {
    color: #1890FF;
    font-size: 18px;
    font-weight: 600;
    padding: 12px 16px;
}

/* 字段标签 */
QLabel[label="true"] {
    color: #595959;
    font-weight: 600;
    margin-bottom: 2px;
}

/* 卡片容器 */
QGroupBox {
    background-color: #FFFFFF;
    border: 1px solid #F0F0F0;
    border-radius: 8px;
    margin: 8px 16px;
    padding: 16px;
}

QGroupBox::title {
    subcontrol-origin: padding;
    subcontrol-position: top left;
    left: 16px;
    padding-top: 10px;
    color: #1F1F1F;
    font-weight: 600;
}

/* 按钮 */
QPushButton {
    background-color: #1890FF;
    color: #FFFFFF;
    border: none;
    border-radius: 4px;
    padding: 4px 15px;
    min-height: 32px;
}

QPushButton:hover {
    background-color: #40A9FF;
}

QPushButton:pressed {
    background-color: #096DD9;
}

/* 描边按钮 */
QPushButton[secondary="true"] {
    background-color: #FFFFFF;
    color: #1890FF;
    border: 1px solid #1890FF;
}

QPushButton[secondary="true"]:hover {
    background-color: #F0F7FF;
}

/* 输入控件 */
QLineEdit, QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #D9D9D9;
    border-radius: 4px;
    padding: 4px 11px;
    min-height: 32px;
}

QLineEdit:hover, QComboBox:hover {
    border-color: #40A9FF;
}

QLineEdit:focus, QComboBox:focus {
    border-color: #1890FF;
}

/* 下拉箭头 */
QComboBox::drop-down {
    border: none;
    width: 30px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #BFBFBF;
}

/* 滑块 */
QSlider::groove:horizontal {
    border: none;
    height: 4px;
    background: #F0F0F0;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: #1890FF;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #FFFFFF;
    border: 2px solid #1890FF;
    width: 14px;
    height: 14px;
    margin: -6px 0;
    border-radius: 8px;
}

/* 复选框 */
QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #D9D9D9;
    border-radius: 2px;
}

QCheckBox::indicator:checked {
    background-color: #1890FF;
    border-color: #1890FF;
}

/* 滚动条定制 */
QScrollBar:vertical {
    border: none;
    background: #F0F2F5;
    width: 10px;
}

QScrollBar::handle:vertical {
    background: #BFBFBF;
    min-height: 40px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #8C8C8C;
}

/* 日志区域 */
QTextEdit[log="true"] {
    background-color: #141414;
    border: none;
    border-radius: 4px;
    color: #52C41A;
    font-family: 'Consolas', monospace;
    padding: 12px;
}

/* 监控画面 */
QLabel[display="true"] {
    background-color: #141414;
    border-radius: 4px;
}
"""

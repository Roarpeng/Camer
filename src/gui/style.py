MATERIAL_STYLE = """
QMainWindow {
    background-color: #FAFAFA;
}

QWidget {
    background-color: #FAFAFA;
    color: #212121;
    font-family: 'Microsoft YaHei', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    font-size: 10pt;
}

QLabel {
    background-color: transparent;
    color: #212121;
}

QGroupBox {
    border: 1px solid #BDBDBD;
    border-radius: 8px;
    margin-top: 1.5em;
    padding: 10px;
    font-weight: bold;
    color: #6200EE;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 3px 0 3px;
}

QPushButton {
    background-color: #6200EE;
    color: white;
    border-radius: 4px;
    padding: 8px 16px;
    border: none;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #3700B3;
}

QPushButton:pressed {
    background-color: #03DAC6;
    color: #212121;
}

QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #BDBDBD;
    border-radius: 2px;
}

QCheckBox::indicator:checked {
    background-color: #6200EE;
}

QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #BDBDBD;
    border-radius: 4px;
    padding: 4px;
    color: #212121;
}

QComboBox:on {
    border: 1px solid #6200EE;
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    color: #212121;
    selection-background-color: #6200EE;
}

QSlider::groove:horizontal {
    border: 1px solid #BDBDBD;
    height: 4px;
    background: #E0E0E0;
    margin: 2px 0;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #6200EE;
    border: 1px solid #6200EE;
    width: 14px;
    height: 14px;
    margin: -6px 0;
    border-radius: 7px;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollBar:vertical {
    border: none;
    background: #FAFAFA;
    width: 10px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:vertical {
    background: #BDBDBD;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QTextEdit {
    background-color: #FFFFFF;
    border: 1px solid #BDBDBD;
    border-radius: 4px;
    color: #212121;
}
"""

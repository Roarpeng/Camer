import sys
import os

# Ensure project root is in sys.path so 'src' module can be found
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from src.gui.main_window import MainWindow
from src.gui.style import TECHNO_STYLE

def main():
    # 设置 DPI 缩放环境变量（必须在创建 QApplication 之前设置）
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"
    
    app = QApplication(sys.argv)
    
    # 应用科技感样式
    app.setStyleSheet(TECHNO_STYLE)
    
    # 设置字体，使用适中的点数
    font = app.font()
    font.setFamily("Segoe UI")
    font.setPointSize(16)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

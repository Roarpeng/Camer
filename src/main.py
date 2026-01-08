import sys
import os

# Ensure project root is in sys.path so 'src' module can be found
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication
from src.gui.main_window import MainWindow
from src.gui.style import MATERIAL_STYLE

def main():
    app = QApplication(sys.argv)
    
    # Apply Material Design Style
    app.setStyleSheet(MATERIAL_STYLE)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

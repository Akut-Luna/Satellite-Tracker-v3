import sys
from PySide6.QtWidgets import QApplication

from core.app_core import AppCore

def main():
    app = QApplication(sys.argv)
    # app.setStyleSheet('QWidget { font-size: 11pt; }')

    core = AppCore() # -> core/app_core.py
    core.start() # Tracker app runs now until the main window is closed
    
    exit_code = app.exec() # <- Once the main window is closed the code will resume from here.
    core.shutdown()
    sys.exit(exit_code)

if __name__ == "__main__":
    main() 
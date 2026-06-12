import sys
from PySide6.QtWidgets import QApplication

from core.app_core import AppCore

def main():
    app = QApplication(sys.argv) 
    
    core = AppCore() # -> core/app_core.py
    core.start() # Tracker app runs now until the main window is closed
    
    exit_code = app.exec() # <- Once the main window is closed the code will resume from here.
    core.shutdown()
    sys.exit(exit_code)

    # TODO: build RA/DEC stack from UI to motor controller

if __name__ == "__main__":
    main() 
import sys
if sys.version_info < (3, 12, 6):
    sys.exit('Python 3.12.6+ is required.')

from PySide6.QtWidgets import QApplication

from core.app_core import AppCore

def main():
    print('Performing setup...')
    app = QApplication(sys.argv)

    core = AppCore() # -> core/app_core.py
    core.start() # Tracker app runs now until the main window is closed
    print('Setup complete.')

    exit_code = app.exec() # <- Once the main window is closed the code will resume from here.
    core.shutdown()
    print('Shutdown complete.')
    sys.exit(exit_code)

if __name__ == "__main__":

    main() 
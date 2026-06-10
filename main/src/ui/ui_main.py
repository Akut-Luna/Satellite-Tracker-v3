import os
import matplotlib.image as mpimg
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox, 
    QDateTimeEdit, QRadioButton, QCheckBox, QButtonGroup, QFileDialog,
    QGroupBox, QGridLayout, QSpinBox, QDoubleSpinBox,
    QStackedWidget, QFrame
)
from PySide6.QtCore import QDateTime, Qt, QTimer, QTimeZone, Signal
from PySide6.QtGui import QIcon

from ui.ui_setup import setup_ui
from ui.ui_update import update_ui, update_map
from core.config import AppConfig

class SatelliteTrackerApp(QMainWindow):
    # ------------ bind imported functions (makes it act like normal member functions) ------------
    setup_ui = setup_ui
    update_ui = update_ui
    update_map = update_map

    # ------------------------------------ Signals (send data) ------------------------------------
    RA_changed  = Signal(str) # used in ui_setup.py
    DEC_changed = Signal(str) # used in ui_setup.py
    # ---------------------------------------------------------------------------------------------

    def __init__(self, config: AppConfig):
        '''
        This function initializes the UI.
        '''
        super().__init__()
        self.config = config
        self.setWindowTitle('Satellite Tracker')
        self.setWindowIcon(QIcon(os.path.join('main', 'images', 'satellite_icon_white.svg')))
        self.setGeometry(100, 100, 1200, 800) # set inital pos and size

        # Map
        map_path = os.path.join('main', 'images', 'nasa-topo_1024.jpg')
        self.earth_img = mpimg.imread(map_path)

        # setup
        self.setup_ui()
    
    def log_message(self, msg):
        self.console.append(msg)


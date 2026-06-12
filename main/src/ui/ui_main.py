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
import numpy as np
from ui.ui_setup import setup_ui
from ui.ui_update import update_ui, update_map, update_ui_tracking
from core.config import AppConfig

class SatelliteTrackerApp(QMainWindow):
    # ------------ bind imported functions (makes it act like normal member functions) ------------
    setup_ui = setup_ui
    update_ui = update_ui
    update_map = update_map
    update_ui_tracking = update_ui_tracking

    # ------------------------------------ Signals (send data) ------------------------------------
    RA_changed  = Signal(str)
    DEC_changed = Signal(str)
    tracking_mode_changed = Signal(int)
    tracking_changed = Signal(bool)
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

        # ------------------------------- variabels to keep track of ------------------------------

        # local 
        self.tracking = False # Needs to be kept in sync with the self.tracking in main_loop.py

        # Map
        map_path = os.path.join('main', 'images', 'nasa-topo_1024.jpg')
        self.earth_img = mpimg.imread(map_path)
        self.flight_path = None

        # -----------------------------------------------------------------------------------------

        # setup
        self.setup_ui()
    
    def log_message(self, msg):
        self.console.append(msg)

    # ------------------------------------ Slots (receive data) -----------------------------------
    def update_flight_path(self, flight_path):
        self.flight_path = flight_path

    def update_tracking(self, tracking):
        self.tracking = tracking
        self.update_ui_tracking(tracking)

    def toggle_tracking(self, checked):
        '''
        This function tells AppCore to tell everyone to update self.tracking

        Parameters:
            checked (bool): True -> turn tracking on, False -> turn tracking off
        '''
        self.tracking_changed.emit(checked)
    # ---------------------------------------------------------------------------------------------

    def on_tracking_mode_changed(self, index):
        '''
        Parameters:
            index (int): index of satellite in satellite list
        '''
        if self.tracking:
            self.toggle_tracking(False)
            self.log_message('Tracking stopped because tracking methode was changed')
        self.tracking_mode_stack.setCurrentIndex(index)
        self.doppler_initial_freq.setText('0.0')
        self.tracking_mode_changed.emit(index)




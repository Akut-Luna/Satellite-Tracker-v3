import os
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import cartopy.geodesic as geodesic
import matplotlib.image as mpimg
from dotenv import load_dotenv
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox, 
    QDateTimeEdit, QRadioButton, QCheckBox, QButtonGroup, QFileDialog,
    QGroupBox, QGridLayout, QSpinBox, QDoubleSpinBox,
    QStackedWidget, QFrame
)
from PySide6.QtCore import QDateTime, Qt, QTimer, QTimeZone, Signal
from PySide6.QtGui import QIcon
from matplotlib.figure import Figure
from matplotlib.patches import Polygon
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas # must be imported after PySide

from ui.ui_setup import setup_ui

class SatelliteTrackerApp(QMainWindow):
    # signals for the UI to broadcast on change

    RA_changed = Signal(str)
    DEC_changed = Signal(str)

    def __init__(self):
        '''
        This function initializes the UI.
        '''
        super().__init__()
        self.setWindowTitle('Satellite Tracker')
        self.setWindowIcon(QIcon(os.path.join('main', 'images', 'satellite_icon_white.svg')))
        self.setGeometry(100, 100, 1200, 800) # set inital pos and size

        # UI
        setup_ui(self)
    
    def log_message(self, msg):
        self.console.append(msg)


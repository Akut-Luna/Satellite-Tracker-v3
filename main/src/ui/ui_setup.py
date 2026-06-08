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

def setup_find_passes_widget(self):
    pass

def setup_tracking_modes_widget(self):
    '''
    Sets up the UI element 'Tracking Modes'
    '''
    self.tracking_modes_group = QGroupBox('Tracking Modes')
    tracking_modes_layout = QVBoxLayout(self.tracking_modes_group)
    
    # tracking option selection
    self.tracking_mode_combo = QComboBox()
    self.tracking_mode_combo.addItems(['List', 'RA/DEC', 'TLE/OMM File', 'SPICE', 'AZ/EL'])
    # self.tracking_mode_combo.currentIndexChanged.connect(self.on_tracking_mode_changed) #TODO: solve with Signals
    tracking_modes_layout.addWidget(self.tracking_mode_combo)
    
    # Stacked widget to switch between tracking options input types
    self.tracking_mode_stack = QStackedWidget()

    # 0. List widget --------------------------------------------------------------------------

    
    # 1. RA/DEC widget ------------------------------------------------------------------------
    self.ra_dec_widget = QWidget()
    ra_dec_layout = QGridLayout(self.ra_dec_widget)
    
    ra_dec_layout.addWidget(QLabel('RA [h]:'), 0, 0)
    self.ra_input = QLineEdit()
    ra_dec_layout.addWidget(self.ra_input, 0, 1)

    ra_dec_layout.addWidget(QLabel('DEC [°]:'), 1, 0)
    self.dec_input = QLineEdit()
    ra_dec_layout.addWidget(self.dec_input, 1, 1)
    self.tracking_mode_stack.addWidget(self.ra_dec_widget)

    # 2. TLE/OMM File widget ------------------------------------------------------------------

    # 3. SPICE widget -------------------------------------------------------------------------

    # 4. AZ/EL widget -------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------

    tracking_modes_layout.addWidget(self.tracking_mode_stack)
    self.top_layout.addWidget(self.tracking_modes_group)


def setup_antenna_widget(self):
    pass

def setup_data_widget(self):
    pass

def setup_tracking_widget(self):
    pass

def setup_ui(self):
    '''
    Sets up the main UI window
    '''
    # Main widget and layout
    central_widget = QWidget()
    main_layout = QVBoxLayout(central_widget)
    self.setCentralWidget(central_widget)

    # Top row: find passes and tracking method
    self.top_layout = QHBoxLayout()
    setup_find_passes_widget(self)
    setup_tracking_modes_widget(self)
    main_layout.addLayout(self.top_layout)

    # Middle row: Antenna, Data and Tracking


    # Bottom row: World map and console
    bottom_layout = QHBoxLayout()
    
    # World map
    self.map_projection = ccrs.PlateCarree()
    self.map_figure = Figure(figsize=(8, 4))
    self.map_canvas = FigureCanvas(self.map_figure)
    self.map_ax = self.map_figure.add_subplot(111, projection=self.map_projection)
    # self.update_map(None, None, None) # empty map
    
    bottom_layout.addWidget(self.map_canvas)
    
    # Console
    console_group = QGroupBox('Console')
    console_layout = QVBoxLayout(console_group)
    self.console = QTextEdit()
    self.console.setReadOnly(True)
    console_layout.addWidget(self.console)
    bottom_layout.addWidget(console_group)
    
    main_layout.addLayout(bottom_layout)

    # self.set_style()
    
    # Log initial message
    self.log_message('Satellite Tracker initialized')

    # Set focus to the main window to prevent input widgets from capturing arrow keys
    self.setFocus()
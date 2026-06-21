import os
import matplotlib.image as mpimg
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox, 
    QDateTimeEdit, QRadioButton, QCheckBox, QButtonGroup, QFileDialog,
    QGroupBox, QGridLayout, QSpinBox, QDoubleSpinBox,
    QStackedWidget, QFrame
)
from PySide6.QtCore import QDateTime, Qt, QTimer, QTimeZone, Signal, Slot
from PySide6.QtGui import QIcon
import numpy as np
from ui.ui_setup import (
    set_style, setup_ui, 
    setup_find_passes_widget,
    setup_tracking_modes_widget,
    setup_antenna_widget,
    setup_data_widget,
    setup_tracking_widget
)
from ui.ui_update import update_ui, update_map, update_ui_tracking
from ui.ui_buttons import (
    browse_list, browse_OMM, browse_spice
)
from utils.helper import get_target_names_from_file
from core.config import AppConfig
import pandas as pd

class SatelliteTrackerApp(QMainWindow):
    # ------------ bind imported functions (makes it act like normal member functions) ------------
    # setup
    set_style = set_style
    setup_ui = setup_ui
    setup_find_passes_widget = setup_find_passes_widget
    setup_tracking_modes_widget = setup_tracking_modes_widget
    setup_antenna_widget = setup_antenna_widget
    setup_data_widget = setup_data_widget
    setup_tracking_widget = setup_tracking_widget

    # buttons
    browse_list = browse_list
    browse_OMM = browse_OMM
    browse_spice = browse_spice

    # helper
    get_target_names_from_file = get_target_names_from_file

    # update
    update_ui = update_ui
    update_map = update_map
    update_ui_tracking = update_ui_tracking

    # ------------------------------------ Signals (send data) ------------------------------------
    RA_changed  = Signal(str)
    DEC_changed = Signal(str)
    tracking_mode_changed = Signal(int)
    tracking_changed = Signal(bool)
    target_list_idx_changed = Signal(int)
    OMM_df_changed = Signal(pd.DataFrame)
    OMM_satellite_name_changed = Signal(str)
    OMM_satellite_id_changed = Signal(str)
    doppler_emited_freq_changed = Signal(str)
    target_list_path_changed = Signal(str)
    azimuth_offset_changed = Signal(float)
    elevation_offset_changed = Signal(float)
    start_tracking_at_AOS_changed = Signal(bool)
    OMM_add_to_list = Signal()
    List_add_to_list = Signal()
    spice_kernels_changed = Signal(str)
    spice_target_name_changed = Signal(str)
    close_connection = Signal()
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
        self.ground_track = None

        # -----------------------------------------------------------------------------------------

        # setup
        self.setup_ui()
    
    def log_message(self, msg):
        self.console.append(msg)

    # ------------------------------------ Slots (receive data) -----------------------------------
    def update_ground_track(self, ground_track):
        self.ground_track = ground_track

    @Slot(bool)
    def update_tracking(self, tracking):
        self.tracking = tracking
        self.update_ui_tracking(tracking)

    @Slot(bool)
    def toggle_tracking(self, checked):
        '''
        This function tells AppCore to tell everyone to update self.tracking

        Parameters:
            checked (bool): True -> turn tracking on, False -> turn tracking off
        '''
        self.tracking_changed.emit(checked) # -> app_core
    
    @Slot(float, float)
    def update_antenna_status(self, antenna_az, antenna_el):
        if antenna_az == 9999: # no connection
            self.current_azimuth.setText('N/A')
            self.current_elevation.setText('N/A')
        else:
            self.current_azimuth.setText(f'{antenna_az:.1f}°')
            self.current_elevation.setText(f'{antenna_el:.1f}°')
    
    def update_ui_f0(self, f0):
        self.doppler_initial_freq.setText(str(f0))
    
    def uncheck_start_tracking_at_AOS_btn(self):
        self.start_tracking_at_AOS_btn.setChecked(False)

    def add_to_list_dropdown(self, target_name):
        all_items = [self.tracking_mode_list_dropdown.itemText(i) for i in range(self.tracking_mode_list_dropdown.count())]
        if target_name not in all_items:
            self.tracking_mode_list_dropdown.addItems([target_name])
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
        self.tracking_mode_changed.emit(index) # -> main_loop

    def closeEvent(self, event):
        '''
        This function overwrites the default (empty) closeEvent from QMainWindow
        Parameters:
            event (PySide6.QtGui.QKeyEvent): event
        '''
        print('Shutting down...')

        self.close_connection.emit() # -> motor controller
        event.accept()  # Ensures the window closes properly


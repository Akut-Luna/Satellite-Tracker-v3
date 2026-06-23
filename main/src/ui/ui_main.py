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
from datetime import datetime, timezone
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
import time

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
    RA_changed  = Signal(str) # for tracking mode OMM file only
    DEC_changed = Signal(str) # for tracking mode OMM file only
    az_deg_changed = Signal(str) # for tracking mode AZ/EL only
    el_deg_changed = Signal(str) # for tracking mode AZ/EL only
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
    find_passes_start_time_changed = Signal(object)
    find_passes_end_time_changed = Signal(object)
    find_passes_min_angle_changed = Signal(int)
    go_find_passes = Signal()
    local_time_radio_button_changed = Signal(bool)
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

    def keyPressEvent(self, event):
        '''
        Parameters:
            event (PySide6.QtGui.QKeyEvent): event
        '''
        
        # Handle arrow key presses for azimuth and elevation offset
        if event.key() == Qt.Key_Left or event.key() == Qt.Key_A:
            current = self.azimuth_offset.value()
            new = current - 0.1
            self.azimuth_offset.setValue(new)
            self.azimuth_offset_changed.emit(new)
            event.accept()  # Mark event as handled
        elif event.key() == Qt.Key_Right or event.key() == Qt.Key_D:
            current = self.azimuth_offset.value()
            new = current + 0.1
            self.azimuth_offset.setValue(new)
            self.azimuth_offset_changed.emit(new)
            event.accept()  # Mark event as handled
        elif event.key() == Qt.Key_Up or event.key() == Qt.Key_W:
            current = self.elevation_offset.value()
            new = current + 0.1
            self.elevation_offset.setValue(new)
            self.elevation_offset_changed.emit(new)
            event.accept()  # Mark event as handled
        elif event.key() == Qt.Key_Down or event.key() == Qt.Key_S:
            current = self.elevation_offset.value()
            new = current - 0.1
            self.elevation_offset.setValue(new)
            self.elevation_offset_changed.emit(new)
            event.accept()  # Mark event as handled
        elif event.key() == Qt.Key_Space:
            self.tracking_changed.emit(not self.tracking)
            event.accept()  # Mark event as handled
        elif event.key() == Qt.Key_Escape:
            self.clearFocus() # reset focuse because being focused on input field can break hotkeys
            self.setFocus()
            event.accept()  # Mark event as handled
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        '''
        This function overwrites the default (empty) closeEvent from QMainWindow
        Parameters:
            event (PySide6.QtGui.QKeyEvent): event
        '''
        print('Shutting down...')

        self.close_connection.emit() # -> motor controller
        event.accept()  # Ensures the window closes properly

    def UTC_local_time_button_func(self):
        '''
        Changes if the time in the find passes widget gets displayed in local time or UTC.
        NOTE: This is only about the displayed time. We always use UTC in the background.
        '''
        if self.utc_radio_button.isChecked(): # UTC
            self.start_time_input.setTimeZone(QTimeZone(b'UTC'))
            self.end_time_input.setTimeZone(QTimeZone(b'UTC'))
        else: # Local Time
            tz = self.config.local_tz.encode() # convert str to bytes
            self.start_time_input.setTimeZone(QTimeZone(tz))
            self.end_time_input.setTimeZone(QTimeZone(tz))

        self.start_time_input.setDateTime(QDateTime.currentDateTime())          # Default
        self.end_time_input.setDateTime(QDateTime.currentDateTime().addDays(1)) # Default

    def start_time_func(self):
        start_time = self.start_time_input.dateTime().toPython()
        start_time = start_time.replace(tzinfo=timezone.utc)
        self.find_passes_start_time_changed.emit(start_time) # -> main_loop

    def end_time_func(self):
        end_time = self.end_time_input.dateTime().toPython()
        end_time = end_time.replace(tzinfo=timezone.utc)
        self.find_passes_end_time_changed.emit(end_time) # -> main_loop

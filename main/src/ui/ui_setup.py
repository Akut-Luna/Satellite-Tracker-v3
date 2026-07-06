import os
import cartopy.crs as ccrs
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QStackedWidget,
    QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox, 
    QDateTimeEdit, QRadioButton, QCheckBox, QButtonGroup,
    QGroupBox, QGridLayout, QSpinBox, QDoubleSpinBox,  
)
from PySide6.QtCore import QDateTime, Qt, QTimeZone
from PySide6.QtGui import QGuiApplication
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas # must be imported after PySide

def set_style(self):
    '''
    Set font size and maximum size of UI elements
    '''

    self.setStyleSheet('QWidget { font-size: 11pt; }') 

    # ======================================== Find Passes ========================================
    self.find_passes_group.setMaximumHeight(220)

    # ===================================== Tracking Options ======================================
    self.tracking_modes_group.setMaximumHeight(220)

    # ------------------------------------------- List --------------------------------------------
    self.tracking_mode_list_dropdown.setMaxVisibleItems(20)

    # ------------------------------------------ RA/DEC -------------------------------------------

    # ----------------------------------------- OMM File ------------------------------------------

    # ------------------------------------------- SPICE -------------------------------------------

    # ------------------------------------------- AZ/EL -------------------------------------------
    self.az_el_widget.setMaximumWidth(300)

    # ========================================== Antenna ==========================================
    self.antenna_group.setMaximumSize(450, 194)
    
    # ------------------------------------------ Azimuth ------------------------------------------
    self.azimuth_label.setMaximumWidth(80)
    self.current_azimuth.setMaximumWidth(60)
    self.target_azimuth.setMaximumWidth(60)
    self.azimuth_offset.setMaximumWidth(85)
    self.azimuth_offset_reset_btn.setMaximumWidth(80)
    
    # ----------------------------------------- Elevation -----------------------------------------
    self.elevation_label.setMaximumWidth(80)
    self.current_elevation.setMaximumWidth(60)
    self.target_elevation.setMaximumWidth(60)
    self.elevation_offset.setMaximumWidth(85)
    self.elevation_offset_reset_btn.setMaximumWidth(80)

    # --------------------------------------- Doppler Shift ---------------------------------------
    self.doppler_initial_freq.setMaximumWidth(150)
    self.doppler_shifted_freq.setMaximumWidth(150)
    self.doppler_shift_label.setMaximumWidth(100)

    # =========================================== Data ============================================
    self.data_group.setMaximumSize(300, 194)

    # ========================================= Tracking ==========================================
    self.tracking_group.setMaximumHeight(194)
    self.tracking_btn.setMaximumWidth(170)
    self.tracking_layout.setAlignment(Qt.AlignCenter)

    # ========================================== Status ===========================================
    self.status_group.setMaximumHeight(194)

    # ============================================ Map ============================================

    # ========================================== Console ==========================================

def setup_find_passes_widget(self):
    '''
    Sets up the UI element 'Find Passes'
    '''
    self.find_passes_group = QGroupBox('Find Passes')
    find_passes_layout = QGridLayout(self.find_passes_group)

    # Radio buttons for UTC / Local Time
    self.time_zone_group = QButtonGroup(self)
    self.utc_radio_button = QRadioButton('UTC')
    self.utc_radio_button.setChecked(True)  # Default to UTC
    self.local_time_radio_button = QRadioButton('Local Time')
    # self.local_time_radio_button.toggled.connect(self.local_time_radio_button_changed.emit) # -> main_loop
    self.time_zone_group.addButton(self.utc_radio_button)
    self.time_zone_group.addButton(self.local_time_radio_button)

    find_passes_layout.addWidget(self.utc_radio_button, 0, 0)
    find_passes_layout.addWidget(self.local_time_radio_button, 0, 1)
    
    # Connect the radio button change signal to a function
    self.time_zone_group.buttonToggled.connect(self.UTC_local_time_button_func)

    # Start time
    find_passes_layout.addWidget(QLabel('Start time:'), 1, 0)
    self.start_time_input = QDateTimeEdit()
    self.start_time_input.setDateTime(QDateTime.currentDateTime())
    self.start_time_input.setTimeZone(QTimeZone(b'UTC'))
    self.start_time_input.setDisplayFormat('hh:mm dd.MM.yyyy')
    self.start_time_input.dateTimeChanged.connect(self.start_time_func)
    find_passes_layout.addWidget(self.start_time_input, 1, 1)
    
    # End time
    find_passes_layout.addWidget(QLabel('End time:'), 2, 0)
    self.end_time_input = QDateTimeEdit()
    self.end_time_input.setDateTime(QDateTime.currentDateTime().addDays(1))
    self.end_time_input.setTimeZone(QTimeZone(b'UTC'))
    self.end_time_input.setDisplayFormat('hh:mm dd.MM.yyyy')
    self.end_time_input.dateTimeChanged.connect(self.end_time_func)
    find_passes_layout.addWidget(self.end_time_input, 2, 1)
    
    # Min elevation
    find_passes_layout.addWidget(QLabel('Min elevation:'), 3, 0)
    self.min_elevation_input = QSpinBox()
    self.min_elevation_input.setRange(0, 90)
    self.min_elevation_input.setValue(0)
    self.min_elevation_input.setSuffix('°')
    # self.min_elevation_input.valueChanged.connect(self.find_passes_min_angle_changed.emit) # -> main_loop
    find_passes_layout.addWidget(self.min_elevation_input, 3, 1)
    
    # Find passes button
    self.find_passes_btn = QPushButton('Find Passes')
    # self.find_passes_btn.clicked.connect(self.go_find_passes.emit) # -> main_loop
    find_passes_layout.addWidget(self.find_passes_btn, 4, 0, 1, 2)

    # Next Pass Visualisation Button
    self.next_pass_visualisation_btn = QPushButton('Visualise Next Pass')
    # self.next_pass_visualisation_btn.clicked.connect(self.go_visualise_next_pass.emit) # -> core
    find_passes_layout.addWidget(self.next_pass_visualisation_btn, 5, 0, 1, 2)

    self.top_layout.addWidget(self.find_passes_group)

def setup_tracking_modes_widget(self):
    '''
    Sets up the UI element 'Tracking Modes'
    '''
    self.tracking_modes_group = QGroupBox('Tracking Modes')
    tracking_modes_layout = QVBoxLayout(self.tracking_modes_group)
    
    # tracking option selection
    self.tracking_mode_combo = QComboBox()
    self.tracking_mode_combo.addItems(['List', 'RA/DEC', 'OMM File', 'SPICE', 'AZ/EL'])
    self.tracking_mode_combo.currentIndexChanged.connect(self.on_tracking_mode_changed)
    tracking_modes_layout.addWidget(self.tracking_mode_combo)
    
    # Stacked widget to switch between tracking options input types
    self.tracking_mode_stack = QStackedWidget()

    # -------------------------------------- 0. List widget ---------------------------------------
    self.list_widget = QWidget()
    list_layout = QVBoxLayout(self.list_widget)

    # ------------------- top -------------------
    list_top_layout = QHBoxLayout()

    default_list = os.path.join('main', 'data', 'Lists', 'default_list.json')

    list_top_layout.addWidget(QLabel('List:'))
    self.list_input = QLineEdit()
    self.list_input.setReadOnly(True)
    self.list_input.setText(default_list)
    list_top_layout.addWidget(self.list_input)

    # browse button
    self.list_browse_btn = QPushButton('Browse')
    self.list_browse_btn.clicked.connect(self.browse_list)
    list_top_layout.addWidget(self.list_browse_btn)

    list_layout.addLayout(list_top_layout)

    # ----------------- middle ------------------
    self.tracking_mode_list_dropdown = QComboBox()
    self.tracking_mode_list_dropdown.addItems(self.get_target_names_from_file(default_list))
    # self.tracking_mode_list_dropdown.currentIndexChanged.connect(self.target_list_idx_changed.emit) # -> main_loop
    
    list_layout.addWidget(self.tracking_mode_list_dropdown)
    
    # ----------------- bottom ------------------
    self.List_add_to_list_btn = QPushButton('Add new target to list')
    # self.List_add_to_list_btn.clicked.connect(self.List_add_to_list.emit) # -> core
    list_layout.addWidget(self.List_add_to_list_btn)

    self.tracking_mode_stack.addWidget(self.list_widget)

    # -------------------------------------- 1. RA/DEC widget -------------------------------------
    self.ra_dec_widget = QWidget()
    ra_dec_layout = QGridLayout(self.ra_dec_widget)
    
    ra_dec_layout.addWidget(QLabel('RA [h]:'), 0, 0)
    self.ra_input = QLineEdit()
    # self.ra_input.textChanged.connect(self.RA_changed.emit) # -> main_loop
    ra_dec_layout.addWidget(self.ra_input, 0, 1)
    ra_dec_layout.addWidget(QLabel('Accepted format: xx.xxxx or xxh xxm xxs'), 0, 2)

    ra_dec_layout.addWidget(QLabel('DEC [°]:'), 1, 0)
    self.dec_input = QLineEdit()
    # self.dec_input.textChanged.connect(self.DEC_changed.emit) # -> main_loop
    ra_dec_layout.addWidget(self.dec_input, 1, 1)
    ra_dec_layout.addWidget(QLabel('Accepted format: xx.xxxx or +xx°' + " xx'" +' xx"'), 1, 2)
    self.tracking_mode_stack.addWidget(self.ra_dec_widget)

    # ------------------------------------- 2. OMM File widget ------------------------------------
    self.OMM_widget = QWidget()
    OMM_layout = QVBoxLayout(self.OMM_widget)

    # ------------------- top -------------------
    OMM_top_layout = QHBoxLayout()

    OMM_top_layout.addWidget(QLabel('OMM file:'))
    self.OMM_input = QLineEdit()
    self.OMM_input.setReadOnly(True)
    OMM_top_layout.addWidget(self.OMM_input)

    # browse button
    self.OMM_browse_btn = QPushButton('Browse')
    self.OMM_browse_btn.clicked.connect(self.browse_OMM)
    OMM_top_layout.addWidget(self.OMM_browse_btn)

    OMM_layout.addLayout(OMM_top_layout)

    # ----------------- middle ------------------
    OMM_middle_layout = QHBoxLayout()

    # satellite name
    OMM_middle_layout.addWidget(QLabel('Satellite Name:'))
    self.OMM_satellite_name_input = QLineEdit()
    # self.OMM_satellite_name_input.textChanged.connect(self.OMM_satellite_name_changed)
    OMM_middle_layout.addWidget(self.OMM_satellite_name_input)

    # NORAD id
    OMM_middle_layout.addWidget(QLabel('NORAD id:'))
    self.OMM_satellite_id_input = QLineEdit()
    # self.OMM_satellite_id_input.textChanged.connect(self.OMM_satellite_id_changed)
    OMM_middle_layout.addWidget(self.OMM_satellite_id_input)

    OMM_layout.addLayout(OMM_middle_layout)

    # ----------------- bottom ------------------
    OMM_bottom_layout = QHBoxLayout()

    # info text
    info_text = QLabel('Provide Satellite Name or id. If both are provided, id will be ignored.')
    OMM_bottom_layout.addWidget(info_text)

    # add to list button
    self.OMM_add_to_list_btn = QPushButton('Add to List')
    # self.OMM_add_to_list_btn.clicked.connect(self.OMM_add_to_list.emit) # -> main_loop
    OMM_bottom_layout.addWidget(self.OMM_add_to_list_btn)
    
    OMM_layout.addLayout(OMM_bottom_layout)
    self.tracking_mode_stack.addWidget(self.OMM_widget)

    # -------------------------------------- 3. SPICE widget --------------------------------------
    self.spice_widget = QWidget()
    spice_layout = QGridLayout(self.spice_widget)

    # (path) input
    spice_layout.addWidget(QLabel('SPICE Meta Kernel:'), 0, 0)
    self.spice_input = QLineEdit()
    self.spice_input.setReadOnly(True)
    spice_layout.addWidget(self.spice_input, 0, 1)

    # button
    self.spice_file_browse_btn = QPushButton('Browse')
    self.spice_file_browse_btn.clicked.connect(self.browse_spice)
    spice_layout.addWidget(self.spice_file_browse_btn, 0, 2)

    # target name
    spice_layout.addWidget(QLabel('Target Name:'), 1, 0)
    self.spice_target_name = QLineEdit()
    # self.spice_target_name.textChanged.connect(self.spice_target_name_changed.emit) # -> main_loop
    spice_layout.addWidget(self.spice_target_name, 1, 1)

    self.tracking_mode_stack.addWidget(self.spice_widget)

    # -------------------------------------- 4. AZ/EL widget --------------------------------------
    self.az_el_widget = QWidget()
    az_el_layout = QGridLayout(self.az_el_widget)

    az_el_layout.addWidget(QLabel('Azimuth [°]:'), 0, 0)
    self.az_input = QLineEdit()
    # self.az_input.textChanged.connect(self.az_deg_changed.emit) # -> main_loop
    az_el_layout.addWidget(self.az_input, 0, 1)

    az_el_layout.addWidget(QLabel('Elevation [°]:'), 1, 0)
    self.el_input = QLineEdit()
    # self.el_input.textChanged.connect(self.el_deg_changed.emit) # -> main_loop
    az_el_layout.addWidget(self.el_input, 1, 1)
    self.tracking_mode_stack.addWidget(self.az_el_widget)

    tracking_modes_layout.addWidget(self.tracking_mode_stack)
    self.top_layout.addWidget(self.tracking_modes_group)

def setup_antenna_widget(self):
    '''
    Sets up the UI element 'Antenna'
    '''
    # Antenna Group
    self.antenna_group = QGroupBox('Antenna')
    antenna_layout = QVBoxLayout(self.antenna_group)
    
    # =========================================== AZ EL ===========================================
    az_el_layout = QGridLayout()

    # ------------------------------------------ Azimuth ------------------------------------------
    self.azimuth_label = QLabel('Azimuth')
    az_el_layout.addWidget(self.azimuth_label, 1, 0)
    az_el_layout.addWidget(QLabel('Current'), 0, 1)
    self.current_azimuth = QLineEdit('0.0°')
    self.current_azimuth.setReadOnly(True)
    az_el_layout.addWidget(self.current_azimuth, 1, 1)
    
    az_el_layout.addWidget(QLabel('Target'), 0, 2)
    self.target_azimuth = QLineEdit('0.0°')
    self.target_azimuth.setReadOnly(True)
    az_el_layout.addWidget(self.target_azimuth, 1, 2)
    
    az_el_layout.addWidget(QLabel('Offset'), 0, 3)
    self.azimuth_offset = QDoubleSpinBox()
    self.azimuth_offset.setRange(-360, 360)
    self.azimuth_offset.setDecimals(1)
    self.azimuth_offset.setSingleStep(0.1)
    self.azimuth_offset.setValue(0.0)
    self.azimuth_offset.setSuffix('°')
    az_el_layout.addWidget(self.azimuth_offset, 1, 3)

    self.azimuth_offset_reset_btn = QPushButton('reset')
    self.azimuth_offset_reset_btn.clicked.connect(lambda: self.azimuth_offset.setValue(0.0))
    az_el_layout.addWidget(self.azimuth_offset_reset_btn, 1, 4)
    
    # ----------------------------------------- Elevation -----------------------------------------
    self.elevation_label = QLabel('Elevation')
    az_el_layout.addWidget(self.elevation_label, 2, 0)
    self.current_elevation = QLineEdit('0.0°')
    self.current_elevation.setReadOnly(True)
    az_el_layout.addWidget(self.current_elevation, 2, 1)
    
    self.target_elevation = QLineEdit('0.0°')
    self.target_elevation.setReadOnly(True)
    az_el_layout.addWidget(self.target_elevation, 2, 2)
    
    self.elevation_offset = QDoubleSpinBox()
    self.elevation_offset.setRange(-90, 90)
    self.elevation_offset.setDecimals(1)
    self.elevation_offset.setSingleStep(0.1)
    self.elevation_offset.setValue(0.0)
    self.elevation_offset.setSuffix('°')
    az_el_layout.addWidget(self.elevation_offset, 2, 3)

    self.elevation_offset_reset_btn = QPushButton('reset')
    self.elevation_offset_reset_btn.clicked.connect(lambda: self.elevation_offset.setValue(0.0))
    az_el_layout.addWidget(self.elevation_offset_reset_btn, 2, 4)

    # ----------------------------------------- Horizontal line -----------------------------------
    horizontal_line = QFrame()
    horizontal_line.setFrameShape(QFrame.HLine)
    horizontal_line.setFrameShadow(QFrame.Sunken)
    az_el_layout.addWidget(horizontal_line, 3, 0, 1, 5)
    
    antenna_layout.addLayout(az_el_layout)

    # ======================================= Doppler shift =======================================
    doppler_shift_layout = QGridLayout()

    # --------------------------------------- Doppler shift ---------------------------------------
    self.doppler_shift_label = QLabel('Doppler Shift')
    doppler_shift_layout.addWidget(self.doppler_shift_label, 2, 0)
    doppler_shift_layout.addWidget(QLabel('Emitted freq. [MHz]'), 1, 1)
    self.doppler_initial_freq = QLineEdit()
    self.doppler_initial_freq.setText('0.0')
    # self.doppler_initial_freq.textChanged.connect(self.doppler_emited_freq_changed)
    doppler_shift_layout.addWidget(self.doppler_initial_freq, 2, 1)

    doppler_shift_layout.addWidget(QLabel('Observed freq. [MHz]'), 1, 2)
    self.doppler_shifted_freq = QLineEdit()
    self.doppler_shifted_freq.setText('0.0')
    self.doppler_shifted_freq.setReadOnly(True)
    doppler_shift_layout.addWidget(self.doppler_shifted_freq, 2, 2)

    antenna_layout.addLayout(doppler_shift_layout)
    self.middle_layout.addWidget(self.antenna_group)

def setup_data_widget(self):
    '''
    Sets up the UI element 'Data'
    '''
    # Data Group
    self.data_group = QGroupBox('Data')
    data_layout = QGridLayout(self.data_group)

    # --------------------------------------- UTC -------------------------------------------------
    data_layout.addWidget(QLabel('UTC'), 0, 0)
    self.UTC_text = QDateTimeEdit()
    self.UTC_text.setTimeZone(QTimeZone(b'UTC'))
    self.UTC_text.setDisplayFormat('hh:mm:ss dd.MM.yyyy')
    self.UTC_text.setDateTime(QDateTime.currentDateTimeUtc())
    self.UTC_text.setReadOnly(True)
    data_layout.addWidget(self.UTC_text, 0, 1)

    # --------------------------------------- Altitude --------------------------------------------
    data_layout.addWidget(QLabel('Altitude'), 1, 0)
    self.altitude_text = QLineEdit()
    self.altitude_text.setText('0 km')
    self.altitude_text.setReadOnly(True)
    data_layout.addWidget(self.altitude_text, 1, 1)

    # --------------------------------------- Range -----------------------------------------------
    data_layout.addWidget(QLabel('Range'), 2, 0)
    self.range_text = QLineEdit()
    self.range_text.setText('0 km')
    self.range_text.setReadOnly(True)
    data_layout.addWidget(self.range_text, 2, 1)

    # --------------------------------------- Range Rate ------------------------------------------
    data_layout.addWidget(QLabel('Range Rate'), 3, 0)
    self.range_rate_text = QLineEdit()
    self.range_rate_text.setText('0 km/s')
    self.range_rate_text.setReadOnly(True)
    data_layout.addWidget(self.range_rate_text, 3, 1)
    
    self.middle_layout.addWidget(self.data_group)

def setup_tracking_widget(self):
    '''
    Sets up the UI element 'Tracking'
    '''
    # --------------------------------------- Tracking Group --------------------------------------
    self.tracking_group = QGroupBox('Tracking')
    self.tracking_layout = QVBoxLayout(self.tracking_group)

    # --------------------------------- Start/Stop Tracking button --------------------------------
    self.tracking_btn = QPushButton('Start Tracking')
    self.tracking_btn.setCheckable(True)
    self.tracking_btn.toggled.connect(self.toggle_tracking)
    self.tracking_layout.addWidget(self.tracking_btn)

    # ----------------------------------- Start Tracking at AOS -----------------------------------
    self.start_tracking_at_AOS_btn = QCheckBox('Start Tracking at AOS')
    # self.start_tracking_at_AOS_btn.toggled.connect(self.start_tracking_at_AOS_changed)
    self.start_tracking_at_AOS_btn.toggled.connect(lambda _: self.update_tracker_status(error=False))
    self.tracking_layout.addWidget(self.start_tracking_at_AOS_btn)

    self.middle_layout.addWidget(self.tracking_group)

def setup_status_widget(self):
    '''
    Sets up the UI element 'Status'
    # ---------------------------------------------------------------------------------------------
    '''
    self.status_group = QGroupBox('Status')
    self.status_layout = QVBoxLayout(self.status_group)

    # --------------------------------------- Antenna Status --------------------------------------
    antenna_layout = QHBoxLayout()
    self.antenna_status_label = QLabel('Antenna Status:')
    antenna_layout.addWidget(self.antenna_status_label)

    self.antenna_connection_status = QLabel('Not Connected')
    self.antenna_connection_status.setStyleSheet('color: red;')
    antenna_layout.addWidget(self.antenna_connection_status)
    antenna_layout.addStretch() # Push everything to the left
    self.status_layout.addLayout(antenna_layout)

    # --------------------------------------- Tracker Status --------------------------------------
    tracker_layout = QHBoxLayout()
    self.tracker_status_label = QLabel('Tracker Status:')
    tracker_layout.addWidget(self.tracker_status_label)

    self.tracker_status_status = QLabel('No Target Selected')
    if QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark:
        self.tracker_status_status.setStyleSheet('color: yellow;')
    else:
        self.tracker_status_status.setStyleSheet('color: orange;')
    tracker_layout.addWidget(self.tracker_status_status)
    tracker_layout.addStretch() # Push everything to the left
    self.status_layout.addLayout(tracker_layout)

    self.middle_layout.addWidget(self.status_group)

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
    self.setup_find_passes_widget()
    self.setup_tracking_modes_widget()
    main_layout.addLayout(self.top_layout)

    # Middle row: Antenna, Data, Tracking and Status
    self.middle_layout = QHBoxLayout()
    self.setup_antenna_widget()
    self.setup_data_widget()
    self.setup_tracking_widget()
    self.setup_status_widget()
    main_layout.addLayout(self.middle_layout)

    # Bottom row: World map and console
    bottom_layout = QHBoxLayout()
    
    # World map
    self.map_projection = ccrs.PlateCarree()
    self.map_figure = Figure(figsize=(8, 4))
    self.map_canvas = FigureCanvas(self.map_figure)
    self.map_ax = self.map_figure.add_subplot(111, projection=self.map_projection)
    self.update_map(None, None, None) # empty map
    
    bottom_layout.addWidget(self.map_canvas)
    
    # Console
    console_group = QGroupBox('Console')
    console_layout = QVBoxLayout(console_group)
    self.console = QTextEdit()
    self.console.setReadOnly(True)
    console_layout.addWidget(self.console)
    bottom_layout.addWidget(console_group)
    
    main_layout.addLayout(bottom_layout)

    self.set_style()
    
    # Log initial message
    self.log_message('Satellite Tracker initialized')

    # Set focus to the main window to prevent input widgets from capturing arrow keys
    self.setFocus()


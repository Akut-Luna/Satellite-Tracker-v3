import cartopy.crs as ccrs
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox, 
    QDateTimeEdit, QRadioButton, QCheckBox, QButtonGroup, QFileDialog,
    QGroupBox, QGridLayout, QSpinBox, QDoubleSpinBox,
    QStackedWidget, QFrame
)
from PySide6.QtCore import QDateTime, Qt, QTimer, QTimeZone, Signal
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas # must be imported after PySide

def set_style(self):
    '''
    Set font size and maximum size of UI elements
    '''

    self.setStyleSheet('QWidget { font-size: 11pt; }') 

    # ======================================== Find Passes ========================================
    self.find_passes_group.setMaximumHeight(210)

    # ===================================== Tracking Options ======================================
    self.tracking_modes_group.setMaximumHeight(210)

    # ------------------------------------------- List --------------------------------------------
    self.tracking_mode_list_dropdown.setMaxVisibleItems(20)

    # ------------------------------------------ RA/DEC -------------------------------------------
    self.ra_dec_widget.setMaximumWidth(300)

    # ----------------------------------------- OMM File ------------------------------------------
    # self.gp_file_add_to_list_btn.setMaximumWidth(100)

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
    self.time_zone_group.addButton(self.utc_radio_button)
    self.time_zone_group.addButton(self.local_time_radio_button)

    find_passes_layout.addWidget(self.utc_radio_button, 0, 0)
    find_passes_layout.addWidget(self.local_time_radio_button, 0, 1)
    
    # Connect the radio button change signal to a function
    # self.time_zone_group.buttonToggled.connect(self.UTC_local_time_button_func) # TODO

    # Start time
    find_passes_layout.addWidget(QLabel('Start time:'), 1, 0)
    self.start_time_input = QDateTimeEdit()
    self.start_time_input.setDateTime(QDateTime.currentDateTime())
    self.start_time_input.setTimeZone(QTimeZone(b'UTC'))
    self.start_time_input.setDisplayFormat('hh:mm dd.MM.yyyy')
    find_passes_layout.addWidget(self.start_time_input, 1, 1)
    
    # End time
    find_passes_layout.addWidget(QLabel('End time:'), 2, 0)
    self.end_time_input = QDateTimeEdit()
    self.end_time_input.setDateTime(QDateTime.currentDateTime().addDays(1))
    self.end_time_input.setTimeZone(QTimeZone(b'UTC'))
    self.end_time_input.setDisplayFormat('hh:mm dd.MM.yyyy')
    find_passes_layout.addWidget(self.end_time_input, 2, 1)
    
    # Min elevation
    find_passes_layout.addWidget(QLabel('Min elevation:'), 3, 0)
    self.min_elevation_input = QSpinBox()
    self.min_elevation_input.setRange(0, 90)
    self.min_elevation_input.setValue(0)
    self.min_elevation_input.setSuffix('°')
    find_passes_layout.addWidget(self.min_elevation_input, 3, 1)
    
    # Find passes button
    self.find_passes_btn = QPushButton('Find Passes')
    # self.find_passes_btn.clicked.connect(self.find_passes) # TODO
    find_passes_layout.addWidget(self.find_passes_btn, 4, 0, 1, 2)

    # Next Pass Visualisation Button
    self.next_pass_visualisation_btn = QPushButton('Visualise Next Pass')
    # self.next_pass_visualisation_btn.clicked.connect(self.visualise_next_pass) # TODO
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
    self.tracking_mode_list_dropdown = QComboBox()
    # self.tracking_mode_list_dropdown.addItems(self.get_satellite_names_from_file()) # TODO
    self.tracking_mode_list_dropdown.addItems(['Satellite 1', 'Satellite 2', 'Satellite 3', 'Satellite 4']) # TODO: TEMP
    self.tracking_mode_list_dropdown.currentIndexChanged.connect(self.list_idx_changed.emit) # -> main_loop
    list_layout.addWidget(self.tracking_mode_list_dropdown)
    self.tracking_mode_stack.addWidget(self.list_widget)

    # -------------------------------------- 1. RA/DEC widget -------------------------------------
    self.ra_dec_widget = QWidget()
    ra_dec_layout = QGridLayout(self.ra_dec_widget)
    
    ra_dec_layout.addWidget(QLabel('RA [h]:'), 0, 0)
    self.ra_input = QLineEdit()
    self.ra_input.textChanged.connect(self.RA_changed.emit) # if text changed emit a signal
    ra_dec_layout.addWidget(self.ra_input, 0, 1)

    ra_dec_layout.addWidget(QLabel('DEC [°]:'), 1, 0)
    self.dec_input = QLineEdit()
    self.dec_input.textChanged.connect(self.DEC_changed.emit)
    ra_dec_layout.addWidget(self.dec_input, 1, 1)
    self.tracking_mode_stack.addWidget(self.ra_dec_widget)

    # ------------------------------------- 2. OMM File widget ------------------------------------
    self.gp_file_widget = QWidget()
    gp_file_layout = QVBoxLayout(self.gp_file_widget)

    # ------------------- top -------------------
    gp_file_top_layout = QHBoxLayout()

    gp_file_top_layout.addWidget(QLabel('OMM file:'))
    self.gp_file_input = QLineEdit()
    self.gp_file_input.setReadOnly(True)
    gp_file_top_layout.addWidget(self.gp_file_input)

    # browse button
    self.gp_file_browse_btn = QPushButton('Browse')
    # self.gp_file_browse_btn.clicked.connect(self.browse_gp_file) # TODO
    gp_file_top_layout.addWidget(self.gp_file_browse_btn)

    gp_file_layout.addLayout(gp_file_top_layout)

    # ----------------- middle ------------------
    gp_file_middle_layout = QGridLayout()

    # satellite name
    gp_file_middle_layout.addWidget(QLabel('Satellite Name'), 0, 0)
    self.gp_file_satellite_name = QLineEdit()
    gp_file_middle_layout.addWidget(self.gp_file_satellite_name, 1, 0)

    # Int'l ID
    gp_file_middle_layout.addWidget(QLabel("Int'l ID"), 0, 1)
    self.gp_file_intl_id = QLineEdit()
    gp_file_middle_layout.addWidget(self.gp_file_intl_id, 1, 1)

    # NORAD
    gp_file_middle_layout.addWidget(QLabel('NORAD ID'), 0, 2)
    self.gp_file_norad_id = QLineEdit()
    gp_file_middle_layout.addWidget(self.gp_file_norad_id, 1, 2)

    gp_file_layout.addLayout(gp_file_middle_layout)

    # ----------------- bottom ------------------
    gp_file_bottom_layout = QHBoxLayout()

    # add to list button
    self.gp_file_add_to_list_btn = QPushButton('Add to List')
    # self.gp_file_add_to_list_btn.clicked.connect(self.add_satellite_to_list) # TODO
    gp_file_bottom_layout.addWidget(self.gp_file_add_to_list_btn)
    
    gp_file_layout.addLayout(gp_file_bottom_layout)
    self.tracking_mode_stack.addWidget(self.gp_file_widget)

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
    # self.spice_file_browse_btn.clicked.connect(self.browse_spice_file) # TODO
    spice_layout.addWidget(self.spice_file_browse_btn, 0, 2)

    # Satellite name
    spice_layout.addWidget(QLabel('Satellite Name:'), 1, 0)
    self.spice_name = QLineEdit()
    spice_layout.addWidget(self.spice_name, 1, 1)

    self.tracking_mode_stack.addWidget(self.spice_widget)

    # -------------------------------------- 4. AZ/EL widget --------------------------------------
    self.az_el_widget = QWidget()
    az_el_layout = QGridLayout(self.az_el_widget)

    az_el_layout.addWidget(QLabel('Azimuth [°]:'), 0, 0)
    self.az_input = QLineEdit()
    az_el_layout.addWidget(self.az_input, 0, 1)

    az_el_layout.addWidget(QLabel('Elevation [°]:'), 1, 0)
    self.el_input = QLineEdit()
    az_el_layout.addWidget(self.el_input, 1, 1)
    self.tracking_mode_stack.addWidget(self.az_el_widget)
    # ---------------------------------------------------------------------------------------------

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
    self.tracking_layout.addWidget(self.start_tracking_at_AOS_btn)

    # ------------------------------- Light Time Correction button --------------------------------
    # # Since the Horizon data is already ligth corrected, my light correction is not needed.
    # # I'm still leaving this feature in because it might be usefull in the future with data
    # # from a different source. In the config file you can set DISPLAY_LIGHT_TIME_CORRECTION_OPTION 
    # # to True in order to display this button, that allows the activation of this feature. 
    # if self.display_light_time_correction_option:
    #     self.light_time_correction_btn = QCheckBox('Light Time Correction')
    #     self.tracking_layout.addWidget(self.light_time_correction_btn)

    # ----------------------------------- Horizons direct button ----------------------------------
    # # During the Artemis II mission a mismatch between the calculations for AZ/EL of this program 
    # # based on Horizons data, and the AZ/EL data from Horizons itself was noticed. So an option 
    # # the use the AZ/EL data from Horizons direcly was added. In the config file you can set 
    # # DISPLAY_HORIZONS_DIRECTLY_OPTION to True in order to display this button, that allows 
    # # the activation of this feature. 
    # if self.display_horizons_directly_option:
    #     self.horizons_directly_btn = QCheckBox('Horizons Directly')
    #     self.tracking_layout.addWidget(self.horizons_directly_btn)
    #     self.horizons_directly_btn.setToolTip(
    #         'Use data (AZ, EL, Range, Range Rate) directly from Horizons,\ninstead of calculating it from the state vector.\nWorks only in List mode.'
    #     )
    self.middle_layout.addWidget(self.tracking_group)

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

    # Middle row: Antenna, Data and Tracking
    self.middle_layout = QHBoxLayout()
    self.setup_antenna_widget()
    self.setup_data_widget()
    self.setup_tracking_widget()
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
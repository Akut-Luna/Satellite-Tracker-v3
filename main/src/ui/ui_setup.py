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
    self.tracking_mode_combo.addItems(['List', 'RA/DEC', 'OMM File', 'SPICE', 'AZ/EL'])
    self.tracking_mode_combo.currentIndexChanged.connect(self.on_tracking_mode_changed)
    tracking_modes_layout.addWidget(self.tracking_mode_combo)
    
    # Stacked widget to switch between tracking options input types
    self.tracking_mode_stack = QStackedWidget()

    # 0. List widget --------------------------------------------------------------------------

    # 1. RA/DEC widget ------------------------------------------------------------------------
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

    # 2. TLE/OMM File widget ------------------------------------------------------------------

    # 3. SPICE widget -------------------------------------------------------------------------

    # 4. AZ/EL widget -------------------------------------------------------------------------
    self.az_el_widget = QWidget()
    az_el_layout = QGridLayout(self.az_el_widget)

    az_el_layout.addWidget(QLabel('Azimuth [°]:'), 0, 0)
    self.az_input = QLineEdit()
    az_el_layout.addWidget(self.az_input, 0, 1)

    az_el_layout.addWidget(QLabel('Elevation [°]:'), 1, 0)
    self.el_input = QLineEdit()
    az_el_layout.addWidget(self.el_input, 1, 1)
    self.tracking_mode_stack.addWidget(self.az_el_widget)
    # -----------------------------------------------------------------------------------------

    tracking_modes_layout.addWidget(self.tracking_mode_stack)
    self.top_layout.addWidget(self.tracking_modes_group)

def setup_antenna_widget(self):
    '''
    Sets up the UI element 'Antenna'
    '''
    # Antenna Group
    self.antenna_group = QGroupBox('Antenna')
    antenna_layout = QVBoxLayout(self.antenna_group)
    
    # ========================================= AZ EL =========================================
    az_el_layout = QGridLayout()

    # Azimuth ---------------------------------------------------------------------------------
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
    
    # Elevation -------------------------------------------------------------------------------
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

    # Horizontal line -------------------------------------------------------------------------
    horizontal_line = QFrame()
    horizontal_line.setFrameShape(QFrame.HLine)
    horizontal_line.setFrameShadow(QFrame.Sunken)
    az_el_layout.addWidget(horizontal_line, 3, 0, 1, 5)
    
    antenna_layout.addLayout(az_el_layout)

    # ===================================== Doppler shift =====================================
    doppler_shift_layout = QGridLayout()

    # Doppler shift ---------------------------------------------------------------------------
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

    # UTC ------------------------------------------------------------------------------------
    data_layout.addWidget(QLabel('UTC'), 0, 0)
    self.UTC_text = QDateTimeEdit()
    self.UTC_text.setTimeZone(QTimeZone(b'UTC'))
    self.UTC_text.setDisplayFormat('hh:mm:ss dd.MM.yyyy')
    self.UTC_text.setDateTime(QDateTime.currentDateTimeUtc())
    self.UTC_text.setReadOnly(True)
    data_layout.addWidget(self.UTC_text, 0, 1)

    # Altitude --------------------------------------------------------------------------------
    data_layout.addWidget(QLabel('Altitude'), 1, 0)
    self.altitude_text = QLineEdit()
    self.altitude_text.setText('0 km')
    self.altitude_text.setReadOnly(True)
    data_layout.addWidget(self.altitude_text, 1, 1)

    # Range -----------------------------------------------------------------------------------
    data_layout.addWidget(QLabel('Range'), 2, 0)
    self.range_text = QLineEdit()
    self.range_text.setText('0 km')
    self.range_text.setReadOnly(True)
    data_layout.addWidget(self.range_text, 2, 1)

    # Range Rate ------------------------------------------------------------------------------
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
    # Tracking Group
    self.tracking_group = QGroupBox('Tracking')
    tracking_layout = QVBoxLayout(self.tracking_group)

    # Start/Stop Tracking button --------------------------------------------------------------
    self.tracking_btn = QPushButton('Start Tracking')
    self.tracking_btn.setCheckable(True)
    self.tracking_btn.toggled.connect(self.toggle_tracking)
    tracking_layout.addWidget(self.tracking_btn)

    # Start Tracking at AOS -------------------------------------------------------------------
    self.start_tracking_at_AOS_btn = QCheckBox('Start Tracking at AOS')
    tracking_layout.addWidget(self.start_tracking_at_AOS_btn)

    # # Light Time Correction button ------------------------------------------------------------
    # # Since the Horizon data is already ligth corrected, my light correction is not needed.
    # # I'm still leaving this feature in because it might be usefull in the future with data
    # # from a different source. In the config file you can set DISPLAY_LIGHT_TIME_CORRECTION_OPTION 
    # # to True in order to display this button, that allows the activation of this feature. 
    # if self.display_light_time_correction_option:
    #     self.light_time_correction_btn = QCheckBox('Light Time Correction')
    #     self.tracking_layout.addWidget(self.light_time_correction_btn)

    # # Horizons direct button ------------------------------------------------------------------
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
    setup_find_passes_widget(self)
    setup_tracking_modes_widget(self)
    main_layout.addLayout(self.top_layout)

    # Middle row: Antenna, Data and Tracking
    self.middle_layout = QHBoxLayout()
    setup_antenna_widget(self)
    setup_data_widget(self)
    setup_tracking_widget(self)
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

    # self.set_style() # TODO
    
    # Log initial message
    self.log_message('Satellite Tracker initialized')

    # Set focus to the main window to prevent input widgets from capturing arrow keys
    self.setFocus()
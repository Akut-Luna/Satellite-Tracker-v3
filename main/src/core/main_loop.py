import os
import spiceypy
import traceback
from utils.time_convertions import utc_now
from skyfield.api import load
from PySide6.QtCore import QObject, Signal, QTimer

from utils.calculations import correction_matrix
from utils.time_convertions import local_time_to_UTC
from utils.tracking_modes import (
    tracking_mode_List, tracking_mode_List_core, tracking_mode_RA_DEC, 
    tracking_mode_OMM, tracking_mode_SPICE, tracking_mode_AZ_EL
)
from utils.helper import (
    ra_dec_parser, load_planet_ephemeris, load_target_list_json, load_target_list_data,
    should_ground_track_get_calculated, OMM_add_to_list, find_passes, 
)
from utils.get_data import (
    save_metadata, load_metadata, query_celestrak_api, query_horizons_api, update_data_if_needed
)

class MainLoop(QObject):
    # ------------ bind imported functions (makes it act like normal member functions) ------------
    tracking_mode_List      = tracking_mode_List
    tracking_mode_List_core = tracking_mode_List_core
    tracking_mode_RA_DEC    = tracking_mode_RA_DEC
    tracking_mode_OMM       = tracking_mode_OMM
    tracking_mode_SPICE     = tracking_mode_SPICE
    tracking_mode_AZ_EL     = tracking_mode_AZ_EL

    # helper
    load_planet_ephemeris = load_planet_ephemeris
    load_target_list_json = load_target_list_json
    load_target_list_data = load_target_list_data
    save_metadata = save_metadata
    load_metadata = load_metadata
    query_horizons_api = query_horizons_api
    query_celestrak_api = query_celestrak_api
    update_data_if_needed = update_data_if_needed
    should_ground_track_get_calculated = should_ground_track_get_calculated
    OMM_add_to_list = OMM_add_to_list
    find_passes = find_passes
    local_time_to_UTC = local_time_to_UTC

    # ------------------------------------ Signals (send data) ------------------------------------
    go_update_ui = Signal(dict)     # Send az, el, doppler, etc. to UI
    go_update_motors = Signal(dict) # Send az, el to motors
    go_update_f0 = Signal(float)
    log = Signal(str)
    ground_track_changed = Signal(object)
    tracking_changed = Signal(bool)
    update_antenna_status = Signal()
    uncheck_start_tracking_at_AOS_btn = Signal()
    add_to_list_dropdown = Signal(str)
    # ---------------------------------------------------------------------------------------------

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.load_planet_ephemeris()
        self.skyfield_ts = load.timescale()

        # ------------------------------- variabels to keep track of ------------------------------
        # from UI
        self.tracking_mode = 0
        self.tracking = False
        self.ra_hours = 0.0
        self.dec_degrees = 0.0
        self.az_deg = 0.0               # for tracking mode AZ/EL only
        self.el_deg = 0.0               # for tracking mode AZ/EL only
        self.OMM_df = None              # gets loaded by browse_OMM()
        self.OMM_satellite_name = ''    # gets loaded by browse_OMM()
        self.OMM_satellite_id = -1      # gets loaded by browse_OMM()
        self.OMM_satellite = None       # gets set by tracking_mode_OMM()
        self.doppler_emited_freq = 0.0
        self.target_list_idx = 0
        self.target_list_path = os.path.join('main', 'data', 'Lists', 'default_list.json')
        self.azimuth_offset = 0.0
        self.elevation_offset = 0.0
        self.start_tracking_at_AOS = False
        self.spice_kernels_loaded = False
        self.spice_target_name = ''
        self.find_passes_start_time = None
        self.find_passes_end_time = None
        self.find_passes_min_angle = 0
        self.local_time_radio_button_checked = False

        # local
        self.last_time_ground_track_got_calculated = None
        self.finished_start_up = False       # needs to be before load_target_list()
        self.metadata = self.load_metadata() # needs to be before load_target_list()
        self.target_list = self.load_target_list_json() # first load the list from JSON
        self.load_target_list_data()                    # then fill it with data

    def log_message(self, message):
        self.log.emit(message) # -> ui

        # before start up finished we print to terminal because UI is not visible yet
        if not self.finished_start_up:
            print(message)

    # ------------------------------------ Slots (receive data) -----------------------------------
    def update_ra_hours(self, ra_value:str):
        '''
        Parameters:
            ra_value (str): RA value in h
        '''
        try:
            if ra_value == '':
                self.ra_hours = 0.0
            else:
                self.ra_hours = ra_dec_parser(ra_value)
        except Exception as e:
            self.log_message(f'Error: {e}')
            print(traceback.format_exc())

    def update_dec_degrees(self, dec_value:str):
        '''
        Parameters:
            dec_value (str): DEC value in deg
        '''
        try:
            if dec_value == '':
                self.dec_degrees = 0.0
            else:
                self.dec_degrees = ra_dec_parser(dec_value)
        except Exception as e:
            self.log_message(f'Error: {e}')
            print(traceback.format_exc())

    def update_tracking_mode(self, index):
        self.last_time_ground_track_got_calculated = None
        self.tracking_mode = index
        if index == 0:
            current_target = self.target_list[self.target_list_idx]
            f0 = current_target['frequency']
            self.go_update_f0.emit(f0) # -> ui

    def update_tracking(self, tracking):
        self.tracking = tracking

    def toggle_tracking(self, checked):
        '''
        This function tells AppCore to tell everyone to update self.tracking

        Parameters:
            checked (bool): True -> turn tracking on, False -> turn tracking off
        '''
        self.tracking_changed.emit(checked) # -> app_core
    
    def update_target_list_idx(self, index):
        self.target_list_idx = index
        current_target = self.target_list[index]
        f0 = current_target['frequency']
        self.go_update_f0.emit(f0) # -> ui
    
    def update_OMM_df(self, df):
        self.OMM_df = df

    def update_OMM_satellite_name(self, name):
        self.OMM_satellite_name = name.upper()

    def update_OMM_satellite_id(self, sat_id):
        if sat_id != '':
            try:
                self.OMM_satellite_id = int(sat_id)
            except:
                self.log_message(f'Invalid ID: {sat_id}')
        else:
            self.OMM_satellite_id = -1

    def update_doppler_emited_freq(self, freq):
        if freq != '':
            try:
                self.doppler_emited_freq = float(freq)
            except:
                self.log_message(f'Invalid frequency: {freq}')
        else:
            self.doppler_emited_freq = 0.0

    def update_target_list_path(self, path):
        self.target_list_path = path
        self.target_list = self.load_target_list_json() # update list in memory
        self.load_target_list_data()                    # update list in memory

    def update_target_list(self):
        self.target_list = self.load_target_list_json() # first load the list from JSON
        self.load_target_list_data()                    # then fill it with data

    def update_azimuth_offset(self, offset):
        self.azimuth_offset = offset

    def update_elevation_offset(self, offset):
        self.elevation_offset = offset
    
    def update_start_tracking_at_AOS(self, status):
        self.start_tracking_at_AOS = status
    
    def update_spice_kernels(self, path):
        # Load all kernels from meta-kernel
        try:
            spiceypy.furnsh(path)
            self.spice_kernels_loaded = True
        except Exception as e:
            self.log_message(f'Could not load SPICE Kernels: {e}')
            print(traceback.format_exc())

    def update_spice_target_name(self, name):
        self.spice_target_name = name
    
    def update_az_deg(self, az):
        if az == '':
            az = 0
        else:
            az = float(az)

        if az < 0 or 360 < az:
            self.log_message('Azimuth needs to be between 0° and 360°')
            self.az_deg = None
        else:
            self.az_deg = az
    
    def update_el_deg(self, el):
        if el == '':
            el = 0
        else:
            el = float(el)

        if el < 0 or 90 < el:
            self.log_message('Elevation needs to be between 0° and 90°')
            self.el_deg = None
        else:
            self.el_deg = el

    def update_find_passes_start_time(self, datetime):
        self.find_passes_start_time = datetime

    def update_find_passes_end_time(self, datetime):
        self.find_passes_end_time = datetime

    def update_find_passes_min_angle(self, angle):
        self.find_passes_min_angle = angle

    def update_local_time_radio_button(self, checked):
        self.local_time_radio_button_checked = checked
    # ---------------------------------------------------------------------------------------------

    def start_loop(self, interval_ms):
        self.timer = QTimer()
        self.timer.timeout.connect(self.main_loop) # every interval_ms: call main_loop
        self.timer.start(interval_ms)

    def load_init_f0(self):
        current_target = self.target_list[self.target_list_idx]
        f0 = current_target['frequency']
        self.go_update_f0.emit(f0)

    def main_loop(self):
        try:
            # ----------------------------------- Tracking Modes ----------------------------------
            t = utc_now()

            # not all methods return all parameters but the variables need to exist
            az = 0.0
            el = 0.0
            az_rate = None
            el_rate = None
            slant_range = None
            range_rate = None
            latitude = None 
            longitude = None
            altitude = None
            f1 = None

            try:
                if self.tracking_mode == 0:    # List
                    az, az_rate, el, el_rate, slant_range, range_rate, latitude, longitude, altitude, f1 = self.tracking_mode_List(t)

                elif self.tracking_mode == 1:  # RA/DEC
                    az, el, latitude, longitude, altitude = self.tracking_mode_RA_DEC(t)

                elif self.tracking_mode == 2:  # OMM File
                    az, az_rate, el, el_rate, slant_range, range_rate, latitude, longitude, altitude, f1 = self.tracking_mode_OMM(t)

                elif self.tracking_mode == 3:  # SPICE
                    az, az_rate, el, el_rate, slant_range, range_rate, latitude, longitude, altitude, f1 = self.tracking_mode_SPICE(t)
                        
                elif self.tracking_mode == 4:  # AZ/EL
                    az, el = self.tracking_mode_AZ_EL()
            except Exception as e:
                self.log_message(f'Error calculating target data: {e}')
                print(traceback.format_exc())

            if az is not None and el is not None:
                # ----------------------- Correction for not ideal Antenna ------------------------
                try:
                    az, el = correction_matrix(
                        az, el, 
                        self.config.correction_roll, 
                        self.config.correction_pitch, 
                        self.config.correction_yaw
                    )
                except Exception as e:
                    self.log_message(f'Error calculating correction matrix: {e}')
                    print(traceback.format_exc())

                # --------------------------------- manual offset ---------------------------------
                az += self.azimuth_offset
                el += self.elevation_offset

                # ------------------------------ start tacking at AOS -----------------------------
                if self.start_tracking_at_AOS:
                    if not self.tracking and el > 0:
                        self.toggle_tracking(True)
                        if self.config.auto_uncheck_start_tracking_at_AOS_btn:
                            self.uncheck_start_tracking_at_AOS_btn.emit()  # -> ui
                        self.log_message('Tracking was started automatically at expected AOS.')

                # ------------------------------ stop tracking at LOS -----------------------------
                if self.tracking and el < 0:
                    self.toggle_tracking(False)
                    self.log_message('Tracking was stopped because the satellite is under the horizon.')

                # ------------------------------------- Motors ------------------------------------
                data = {
                    'az'      : az,
                    'el'      : el,
                    'az_rate' : az_rate,
                    'el_rate' : el_rate,
                    't'       : t
                }

                self.go_update_motors.emit(data) # -> motor_controller

            # --------------------------------- Update data on UI ---------------------------------
            data = {
                'az'          : az,
                'el'          : el,
                'slant_range' : slant_range,
                'range_rate'  : range_rate,
                'latitude'    : latitude,
                'longitude'   : longitude,
                'altitude'    : altitude,
                'f1'          : f1
            }

            self.go_update_ui.emit(data) # -> ui
            self.update_antenna_status.emit() # -> motor_controller
        
        except Exception as e:
            self.log_message(f'Error: {str(e)}')
            print(traceback.format_exc())        

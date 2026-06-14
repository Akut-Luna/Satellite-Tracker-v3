from PySide6.QtCore import QObject, Signal, QTimer
from utils.time_convertions import utc_now
import traceback
import shutil
import os
from skyfield.api import load
import numpy as np
from utils.tracking_modes import (
    tracking_mode_List, tracking_mode_RA_DEC, tracking_mode_OMM, tracking_mode_SPICE, tracking_mode_AZ_EL
)

from utils.helper import ra_dec_parser, load_planet_ephemeris, load_target_list
from utils.calculations import correction_matrix
from utils.get_data import load_metadata, query_celestrak_api, save_metadata, update_data_if_needed

class MainLoop(QObject):
    # ------------ bind imported functions (makes it act like normal member functions) ------------
    tracking_mode_List   = tracking_mode_List
    tracking_mode_RA_DEC = tracking_mode_RA_DEC
    tracking_mode_OMM    = tracking_mode_OMM
    tracking_mode_SPICE  = tracking_mode_SPICE
    tracking_mode_AZ_EL  = tracking_mode_AZ_EL

    # helper
    load_planet_ephemeris = load_planet_ephemeris
    load_target_list = load_target_list
    load_metadata = load_metadata
    query_celestrak_api = query_celestrak_api
    save_metadata = save_metadata
    update_data_if_needed = update_data_if_needed

    # ------------------------------------ Signals (send data) ------------------------------------
    go_update_ui = Signal(dict)     # Send az, el, doppler, etc. to UI
    go_update_motors = Signal(dict) # Send az, el to motors
    go_update_f0 = Signal(float)
    log = Signal(str)
    flight_path_changed = Signal(object) # np.array or None # TODO: maybe handle with empty array?
    tracking_changed = Signal(bool)
    update_antenna_status = Signal()
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
        self.OMM_df = None              # gets loaded by browse_OMM()
        self.OMM_satellite_name = ''    # gets loaded by browse_OMM()
        self.OMM_satellite_id = -1      # gets loaded by browse_OMM()
        self.OMM_satellite = None       # gets set by tracking_mode_OMM()
        self.doppler_init_freq = 0.0
        self.target_list_idx = 0
        self.target_list_path = os.path.join('main', 'data', 'Lists', 'default_list.json')

        # local
        self.last_time_flight_path_got_calculated = None
        self.flight_path = None
        self.target_list = self.load_target_list()
        self.metadata = self.load_metadata()
        # self.spice_kernels_loaded = False # gets set by browse_spice_file() # TODO

    def log_message(self, message):
        self.log.emit(message) # -> ui

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
            if self.tracking:
                self.log_message(f'Error: {e}')
                print(traceback.format_exc())
            return

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
            if self.tracking:
                self.log_message(f'Error: {e}')
                print(traceback.format_exc())
            return
    
    def update_tracking_mode(self, index):
        self.last_time_flight_path_got_calculated = None
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

    def update_doppler_init_freq(self, freq):
        if freq != '':
            try:
                self.doppler_init_freq = float(freq)
            except:
                self.log_message(f'Invalid frequency: {freq}')
        else:
            self.doppler_init_freq = 0.0

    def update_target_list_path(self, path):
        self.target_list_path = path
        self.target_list = self.load_target_list() # update list in memory
    # ---------------------------------------------------------------------------------------------

    def start_loop(self, interval_ms):
        self.timer = QTimer()
        self.timer.timeout.connect(self.main_loop) # every interval_ms: call main_loop
        self.timer.start(interval_ms)

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
                if self.tracking:
                    self.log_message(f'Error calculating satellite data: {e}')
                    print(traceback.format_exc())

            # ------------------------- Correction for not ideal Antenna --------------------------
            try:
                az, el = correction_matrix(az, el, roll=0, pitch=0, yaw=0) # TODO: load angle from settings
            except Exception as e:
                if self.tracking:
                    self.log_message(f'Error calculating correction matrix: {e}')
                    print(traceback.format_exc())

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

            # -------------------------------------------------------------------------------------

            # manual offset # TODO
            # az += self.azimuth_offset.value()
            # el += self.elevation_offset.value()

            # # start tacking at AOS
            # if self.start_tracking_at_AOS_btn.isChecked(): # TODO
            #     if not self.tracking and el > 0 and self.tracking_mode in [0,2,3]:
            #         self.toggle_tracking(True)
            #         if self.config.auto_uncheck_start_tracking_at_AOS_btn:
            #             self.start_tracking_at_AOS_btn.setChecked(False)  # TODO
            #         self.log_message('Tracking was started automatically at expected AOS.')

            # stop tracking when satellite is under the horizon
            if self.tracking and el < 0:
                self.toggle_tracking(False)
                self.log_message('Tracking was stopped because the satellite is under the horizon.')

            
            # Motors ------------------------------------------------------------------------------

            # if self.socket is not None:
            #     # get current position from antenna
            #     current_az, current_el = self.talk_to_motor_controller('status')
                
            #     self.current_azimuth.setText(f'{current_az:.1f}°')
            #     self.current_elevation.setText(f'{current_el:.1f}°')

            #     if self.should_update_motors(current_az, current_el, az, el) and self.tracking:
            #         # calculate target position based on angular rate
            #         now = self.skyfield_time_to_datetime(t)
            #         if az_rate is not None and el_rate is not None:
            #             if self.last_time_motor_got_updated is not None:
            #                 delta_t = (now - self.last_time_motor_got_updated).total_seconds()
            #                 az += az_rate*delta_t
            #                 el += el_rate*delta_t
            #         self.last_time_motor_got_updated = now

            #         az = np.clip(az, 0, 360)
            #         el = np.clip(el, 0, 90)
            #         self.talk_to_motor_controller('set', az, el)
            
            data = {
                'az'      : az,
                'el'      : el,
                'az_rate' : az_rate,
                'el_rate' : el_rate
            }

            self.go_update_motors.emit(data) # -> motor_controller
        
        except Exception as e:
            if self.tracking:
                self.log_message(f'Error: {str(e)}')
                print(traceback.format_exc())        

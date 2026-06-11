from PySide6.QtCore import QObject, Signal, QTimer
from utils.time_convertions import utc_now
import traceback
import shutil
import os
from skyfield.api import load, Loader
import numpy as np
from utils.tracking_modes import (
    tracking_mode_List, tracking_mode_RA_DEC, tracking_mode_OMM, tracking_mode_SPICE, tracking_mode_AZ_EL
)

from utils.calculations import correction_matrix

class MainLoop(QObject):
    # ------------ bind imported functions (makes it act like normal member functions) ------------
    tracking_mode_List   = tracking_mode_List
    tracking_mode_RA_DEC = tracking_mode_RA_DEC
    tracking_mode_OMM    = tracking_mode_OMM
    tracking_mode_SPICE  = tracking_mode_SPICE
    tracking_mode_AZ_EL  = tracking_mode_AZ_EL

    # ------------------------------------ Signals (send data) ------------------------------------
    go_update_ui = Signal(dict)     # Send az, el, doppler, etc. to UI
    go_update_motors = Signal(dict) # Send az, el to motors
    log = Signal(str)
    flight_path_changed = Signal(object) # np.array or None # TODO: maybe handle with empty array?
    tracking_changed = Signal(bool)
    # ---------------------------------------------------------------------------------------------

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.load_planet_ephemeris()
        self.ts = load.timescale()

        # ------------------------------- variabels to keep track of ------------------------------

        # local
        self.last_time_flight_path_got_calculated = None
        self.flight_path = None

        # from UI
        self.tracking_mode = 1
        self.tracking = False
        self.ra_hours = 0.0
        self.dec_degrees = 0.0

    def log_message(self, message):
        self.log.emit(message)

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
                self.ra_hours = float(ra_value)
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
                self.dec_degrees = float(dec_value)
        except Exception as e:
            if self.tracking:
                self.log_message(f'Error: {e}')
                print(traceback.format_exc())
            return
    
    def update_tracking_mode(self, index):
        self.last_time_flight_path_got_calculated = None
        self.tracking_mode = index

    def update_tracking(self, tracking):
        self.tracking = tracking
        # TODO (maybe allready done) all the stuff that need to happen on this thread when traking is toggeld

    def toggle_tracking(self, checked):
        '''
        This Slot gets call by ui and by this file

        Parameters:
            checked (bool): True -> turn tracking on, False -> turn tracking off
        '''

        self.tracking = checked
        self.tracking_changed.emit(checked)
    # ---------------------------------------------------------------------------------------------

    def load_planet_ephemeris(self):
        filename = 'de421.bsp'
        ephemeris_folder = os.path.join('main', 'data', 'Ephemeris')
        ephemeris_file = os.path.join(ephemeris_folder, filename)

        # if needed: download
        if not os.path.exists(ephemeris_file) and not os.path.exists(filename):
            tmp_loader = Loader('.')
            tmp_loader.download(filename) 

        # if needed: move to folder
        if os.path.exists(filename):
            os.makedirs(ephemeris_folder, exist_ok=True)
            shutil.move(filename, ephemeris_file)

        self.planet_ephemeris = load(ephemeris_file)  

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
            f1 = 0.0

            try:
                if self.tracking_mode == 0:    # List
                    # az, az_rate, el, el_rate, slant_range, range_rate, latitude, longitude, altitude, f1 = self.tracking_mode_List(t)
                    pass

                elif self.tracking_mode == 1:  # RA/DEC
                    az, el, latitude, longitude, altitude = self.tracking_mode_RA_DEC(t)

                elif self.tracking_mode == 2:  # OMM File
                    # az, az_rate, el, el_rate, slant_range, range_rate, latitude, longitude, altitude, f1 = self.tracking_mode_TLE_OMM(t)
                    pass

                elif self.tracking_mode == 3:  # SPICE
                    # az, az_rate, el, el_rate, slant_range, range_rate, latitude, longitude, altitude, f1 = self.tracking_mode_SPICE(t)
                    pass
                        
                elif self.tracking_mode == 4:  # AZ/EL
                    # az, el = self.tracking_mode_AZ_EL()
                    pass

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

            self.go_update_ui.emit(data)

            # -------------------------------------------------------------------------------------

            # manual offset
            # az += self.azimuth_offset.value()
            # el += self.elevation_offset.value()

            # start tacking at AOS
            # if self.start_tracking_at_AOS_btn.isChecked():
            #     if not self.tracking and el > 0 and tracking_mode in [0,2,3]:
            #         self.toggle_tracking(True)
            #         if self.auto_uncheck_start_tracking_at_AOS_btn:
            #             self.start_tracking_at_AOS_btn.setChecked(False)
            #         self.log_message('Tracking was started automatically at expected AOS.')

            # stop tracking when satellite is under the horizon
            # if self.tracking and el < 0:
            #     self.toggle_tracking(False)
            #     self.log_message('Tracking was stopped because the satellite is under the horizon.')

            
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

            self.go_update_motors.emit(data)
        
        except Exception as e:
            if self.tracking:
                self.log_message(f'Error: {str(e)}')
                print(traceback.format_exc())        




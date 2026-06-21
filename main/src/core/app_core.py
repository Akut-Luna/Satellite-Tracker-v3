import os
from dotenv import load_dotenv 
from PySide6.QtCore import QObject, QThread, Signal, Slot

from core.main_loop import MainLoop
from core.config import AppConfig
from ui.ui_main import SatelliteTrackerApp
from utils.motor_controller import MotorWorker
from utils.sub_windows.List_add_to_list import ListAddToListWindow


class AppCore(QObject):
    tracking_changed = Signal(bool)
    '''
    This class is the "core" of the Tracker App. It will hold the different threads.
    '''

    def __init__(self):
        super().__init__()
        self.tracking = False

        # -------------------------------- load settings from file --------------------------------
        load_dotenv(os.path.join('main', 'config', 'config_app.env'))
        load_dotenv(os.path.join('main', 'config', 'config_antenna.env'))
        
        # Antenna
        antenna_latitude  = float(os.getenv('LATITUDE'))
        antenna_longitude = float(os.getenv('LONGITUDE'))
        antenna_altitude  = float(os.getenv('ALTITUDE'))
        local_tz = os.getenv('LOCAL_TZ') # local time zone
        min_angle_change_before_update = float(os.getenv('MIN_ANGLE_CHANGE_BEFORE_UPDATE'))
        correction_roll  = float(os.getenv('CORRECTION_ROLL'))
        correction_pitch = float(os.getenv('CORRECTION_PITCH'))
        correction_yaw   = float(os.getenv('CORRECTION_YAW'))

        # Data
        time_resolution_horizons_state_vector = int(os.getenv('TIME_RESOLUTION_HORIZONS_STATE_VECTOR'))
        time_resolution_horizons_directly = int(os.getenv('TIME_RESOLUTION_HORIZONS_DIRECTLY'))

        # Tracking
        auto_uncheck_start_tracking_at_AOS_btn = os.getenv('AUTO_UNCHECK_START_TRACKING_AT_AOS_BTN').upper() == 'TRUE'

        # Motor
        motor_IP = os.getenv('IP_ADRESS')
        motor_port = int(os.getenv('PORT'))

        # Map
        ground_track_steps = int(os.getenv('GROUND_TRACK_STEPS'))
        min_before_recalculate_ground_track = int(os.getenv('MIN_BEFORE_RECALCULATING_GROUND_TRACK'))

        # immutable config object (passed to workers / exposed to UI)
        self.config = AppConfig(
            antenna_latitude=antenna_latitude,
            antenna_longitude=antenna_longitude,
            antenna_altitude=antenna_altitude,
            local_tz=local_tz,
            min_angle_change_before_update=min_angle_change_before_update,
            motor_IP=motor_IP,
            motor_port=motor_port,
            ground_track_steps=ground_track_steps,
            min_before_recalculate_ground_track=min_before_recalculate_ground_track,
            auto_uncheck_start_tracking_at_AOS_btn=auto_uncheck_start_tracking_at_AOS_btn,
            time_resolution_horizons_state_vector=time_resolution_horizons_state_vector,
            time_resolution_horizons_directly=time_resolution_horizons_directly,
            correction_roll=correction_roll,
            correction_pitch=correction_pitch,
            correction_yaw=correction_yaw  
        )

        # ----------------------------------- initialize workers ----------------------------------
        # UI 'worker' (needs to live on the main thread)
        self.main_window = SatelliteTrackerApp(self.config) # -> ui/ui_main.py 
        
        # main loop worker 
        self.main_loop_worker = MainLoop(self.config) # -> core/main_loop.py
        
        # motor worker
        self.motor_worker = MotorWorker(self.config) # -> utils/motor_controller.py

        # ----------------------------------- initialize threads ----------------------------------
        self.main_loop_thread = QThread()
        self.motor_thread = QThread()
        
        # --------------------------- move workers to separate threads ----------------------------
        self.main_loop_worker.moveToThread(self.main_loop_thread)
        self.motor_worker.moveToThread(self.motor_thread)

        # ------------------------------- connect Signals with Slots ------------------------------
        # start timer once main_loop_thread has started
        self.main_loop_thread.started.connect(lambda: self.main_loop_worker.start_loop(500))

        # try to connect to motor controller once motor_thread has started
        self.motor_thread.started.connect(self.motor_worker.establish_connection)
        
        # ------------ init setup that can only happen once everything else is loaded -------------
        self.main_loop_thread.started.connect(self.main_loop_worker.load_init_f0)

        # ----------- UI -> Main Loop -----------
        self.main_window.RA_changed.connect(self.main_loop_worker.update_ra_hours)
        self.main_window.DEC_changed.connect(self.main_loop_worker.update_dec_degrees)
        self.main_window.tracking_mode_changed.connect(self.main_loop_worker.update_tracking_mode)
        self.main_window.target_list_idx_changed.connect(self.main_loop_worker.update_target_list_idx)
        self.main_window.OMM_df_changed.connect(self.main_loop_worker.update_OMM_df)
        self.main_window.OMM_satellite_name_changed.connect(self.main_loop_worker.update_OMM_satellite_name)
        self.main_window.OMM_satellite_id_changed.connect(self.main_loop_worker.update_OMM_satellite_id)
        self.main_window.doppler_init_freq_changed.connect(self.main_loop_worker.update_doppler_init_freq)
        self.main_window.target_list_path_changed.connect(self.main_loop_worker.update_target_list_path)
        self.main_window.azimuth_offset_changed.connect(self.main_loop_worker.update_azimuth_offset)
        self.main_window.elevation_offset_changed.connect(self.main_loop_worker.update_elevation_offset)
        self.main_window.start_tracking_at_AOS_changed.connect(self.main_loop_worker.update_start_tracking_at_AOS)
        self.main_window.OMM_add_to_list.connect(self.main_loop_worker.OMM_add_to_list)
        
        # ------------- UI -> Core  -------------
        self.main_window.List_add_to_list.connect(self.open_List_add_to_list_window)

        # ------- UI -> Motor Controller  -------

        # ----------- Main Loop -> UI -----------
        self.main_loop_worker.go_update_ui.connect(self.main_window.update_ui)
        self.main_loop_worker.ground_track_changed.connect(self.main_window.update_ground_track)
        self.main_loop_worker.go_update_f0.connect(self.main_window.update_ui_f0)
        self.main_loop_worker.uncheck_start_tracking_at_AOS_btn.connect(self.main_window.uncheck_start_tracking_at_AOS_btn)
        self.main_loop_worker.add_to_list_dropdown.connect(self.main_window.add_to_list_dropdown)

        # ---- Main Loop -> Motor Controller ----
        self.main_loop_worker.go_update_motors.connect(self.motor_worker.move_motors)
        self.main_loop_worker.update_antenna_status.connect(self.motor_worker.update_antenna_status)
        
        # ---- Motor Controller -> Main Loop ----

        # ------- Motor Controller -> UI --------
        self.motor_worker.antenna_status_changed.connect(self.main_window.update_antenna_status)

        # ----------------- logs ----------------
        self.main_loop_worker.log.connect(self.main_window.log_message)
        self.motor_worker.log.connect(self.main_window.log_message)

        # -------- tracking coordination --------
        self.main_window.tracking_changed.connect(self.set_tracking)         # UI -> App Core
        self.main_loop_worker.tracking_changed.connect(self.set_tracking)    # Main Loop -> App Core
        self.tracking_changed.connect(self.main_window.update_tracking)      # App Core -> UI
        self.tracking_changed.connect(self.main_loop_worker.update_tracking) # App Core -> Main Loop
        self.tracking_changed.connect(self.motor_worker.update_tracking)     # App Core -> Motor Controller

    # ------------------------------------ Slots (receive data) -----------------------------------
    @Slot(bool)
    def set_tracking(self, tracking: bool):
        if self.tracking == tracking:
            return

        self.tracking = tracking
        self.tracking_changed.emit(tracking) # -> ui, main_loop, motor_controller

    @Slot(bool)
    def open_List_add_to_list_window(self):
        '''
        This is for the 'add to list' button in List mode, not for the 'add to list' in OMM file mode.
        Parameters:
        '''
        self.List_add_to_list_window = ListAddToListWindow(self.main_loop_worker.target_list_path)
        self.List_add_to_list_window.show()
        
        # ------------------------------- connect Signals with Slots ------------------------------
        # add to list window -> ui
        self.List_add_to_list_window.update_ui.connect(self.main_window.add_to_list_dropdown)
        self.List_add_to_list_window.log.connect(self.main_window.log_message)

        # add to list window -> main_loop
        self.List_add_to_list_window.new_target_added.connect(self.main_loop_worker.update_target_list)

    # ---------------------------------------------------------------------------------------------

    def start(self):
        print('Loading...')

        # start threads
        self.main_loop_thread.start()
        self.motor_thread.start()

        # show window
        self.main_window.show()

        # before start up finished we use print() instead of log_message()
        self.main_loop_worker.finished_start_up = True

    def shutdown(self):
        # stop threads
        self.main_loop_thread.quit()
        self.main_loop_thread.wait()

        # wait for threads to finish cleaning up their memory
        self.motor_thread.quit()
        self.motor_thread.wait()
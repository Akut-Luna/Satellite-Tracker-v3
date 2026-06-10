import os
from dotenv import load_dotenv 
from PySide6.QtCore import QThread

from ui.ui_update import update_ui
from core.main_loop import MainLoop
from core.config import AppConfig
from ui.ui_main import SatelliteTrackerApp
from utils.motor_controller import MotorWorker

class AppCore:
    '''
    This class is the "core" of the Tracker App. It will hold the different threads.
    '''

    def __init__(self):
        # -------------------------------- load settings from file --------------------------------
        load_dotenv(os.path.join('main', 'config', 'config_app.env'))
        load_dotenv(os.path.join('main', 'config', 'config_antenna.env'))
        
        # Antenna
        antenna_latitude = float(os.getenv('LATITUDE'))
        antenna_longitude = float(os.getenv('LONGITUDE'))
        antenna_altitude = float(os.getenv('ALTITUDE'))
        local_tz = os.getenv('LOCAL_TZ') # local time zone
        min_angle_change_before_update = float(os.getenv('MIN_ANGLE_CHANGE_BEFORE_UPDATE'))

        # Motor
        motor_IP = os.getenv('IP_ADRESS')
        motor_port = int(os.getenv('PORT'))

        # Map
        flight_path_steps = int(os.getenv('FLIGHT_PATH_STEPS'))
        min_before_recalculate_flight_path = int(os.getenv('MIN_BEFORE_RECALCULATING_FLIGHT_PATH'))


        # immutable config object (passed to workers / exposed to UI)
        self.config = AppConfig(
            antenna_latitude=antenna_latitude,
            antenna_longitude=antenna_longitude,
            antenna_altitude=antenna_altitude,
            local_tz=local_tz,
            min_angle_change_before_update=min_angle_change_before_update,
            motor_IP=motor_IP,
            motor_port=motor_port,
            flight_path_steps=flight_path_steps,
            min_before_recalculate_flight_path=min_before_recalculate_flight_path
        )

        # ----------------------------------- initialize workers ----------------------------------
        # UI 'worker' (needs to live on the main thread)
        self.main_window = SatelliteTrackerApp(self.config) # -> ui/ui_main.py 
        
        # main loop worker 
        self.main_loop_worker = MainLoop(self.config) # -> core/main_loop.py
        
        # motor worker
        self.motor_worker = MotorWorker(self.config.motor_IP, self.config.motor_port) # -> utils/motor_controller.py

        # ----------------------------------- initialize threads ----------------------------------
        self.main_loop_thread = QThread()
        self.motor_thread = QThread()
        
        # --------------------------- move workers to separate threads ----------------------------
        self.main_loop_worker.moveToThread(self.main_loop_thread)
        self.motor_worker.moveToThread(self.motor_thread)

        # ------------------------------- connect Signals with Slots ------------------------------
        # start timer once main_loop_thread has started
        self.main_loop_thread.started.connect(
            lambda: self.main_loop_worker.start_loop(500)
        )

        # broadcast changes in the UI (by user)
        self.main_window.RA_changed.connect(self.main_loop_worker.update_ra_hours)
        self.main_window.DEC_changed.connect(self.main_loop_worker.update_dec_degrees)

        # logs
        self.main_loop_worker.log.connect(self.main_window.log_message)
        self.motor_worker.log.connect(self.main_window.log_message)

        # update UI
        self.main_loop_worker.go_update_ui.connect(self.main_window.update_ui)

        # update Motors
        # self.main_loop_worker.go_update_motors.connect(TODO)

    def start(self):
        # start threads
        self.main_loop_thread.start()
        self.motor_thread.start()

        # show window
        self.main_window.show()

    def shutdown(self):
        # stop threads
        self.main_loop_thread.quit()
        self.main_loop_thread.wait()

        # wait for threads to finish cleaning up their memory
        self.motor_thread.quit()
        self.motor_thread.wait()
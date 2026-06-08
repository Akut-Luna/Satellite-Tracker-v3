import os
from dotenv import load_dotenv 
from PySide6.QtCore import QThread

from ui.ui_update import update_ui
from core.main_loop import MainLoop
from ui.ui_main import SatelliteTrackerApp
from utils.motor_controller import MotorWorker

class AppCore:
    '''
    This class is the "core" of the Tracker App. It will hold all important "global" variabels and the 
    different threads.
    '''

    def __init__(self):
        self.main_window = SatelliteTrackerApp()

        # load settings
        load_dotenv(os.path.join('main', 'config', 'config_app.env'))
        load_dotenv(os.path.join('main', 'config', 'config_antenna.env'))
        self.antenna_latitude = float(os.getenv('LATITUDE'))
        self.antenna_longitude = float(os.getenv('LONGITUDE'))
        self.antenna_altitude = float(os.getenv('ALTITUDE'))
        self.min_angle_change_before_update = float(os.getenv('MIN_ANGLE_CHANGE_BEFORE_UPDATE'))
        self.local_tz = os.getenv('LOCAL_TZ') # local time zone

        # Motor
        self.motor_IP = os.getenv('IP_ADRESS')
        self.motor_port = int(os.getenv('PORT'))
        self.last_time_motor_got_updated = None

        # ------------------------------------- initialize workers ------------------------------------
        self.main_loop_worker = MainLoop() # -> core/main_loop.py
        self.motor_worker = MotorWorker(self.motor_IP, self.motor_port) # -> utils/motor_controller.py

        # ------------------------------------- initialize threads ------------------------------------
        self.main_loop_thread = QThread()
        self.motor_thread = QThread()
        
        # ----------------------------- move workers to separate threads ------------------------------
        self.main_loop_worker.moveToThread(self.main_loop_thread)
        self.motor_worker.moveToThread(self.motor_thread)

        # ------------------------------------- connect to signals ------------------------------------
        # start timer once main_loop_thread has started
        self.main_loop_thread.started.connect(
            lambda: self.main_loop_worker.start_loop(500)
        )

        # broadcast changes in the UI (by user)
        self.main_window.RA_changed.connect(self.main_loop_worker.update_current_RA)
        self.main_window.DEC_changed.connect(self.main_loop_worker.update_current_DEC)

        # update UI
        self.main_loop_worker.final_data.connect(update_ui)

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
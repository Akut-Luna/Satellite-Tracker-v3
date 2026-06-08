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

        # ------------------------------------- initialize workers ------------------------------------
        self.main_loop_worker = MainLoop() # -> core/main_loop.py
        self.motor_worker = MotorWorker(ip='127.0.0.1', port=65432) # -> utils/motor_controller.py

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
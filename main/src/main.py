import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread
from ui.ui_main import SatelliteTrackerApp
from ui.ui_update import update_ui
from utils.motor_controller import MotorWorker
from core.main_loop import MainLoop

def main():
    app = QApplication(sys.argv)
    main_window = SatelliteTrackerApp()
    
    # ===================================== Worker and Threads ====================================
    # ------------------------------------- initialize workers ------------------------------------
    main_loop_worker = MainLoop() # -> core/main_loop.py
    motor_worker = MotorWorker(ip="127.0.0.1", port=65432) # -> utils/motor_controller.py

    # ------------------------------------- initialize threads ------------------------------------
    '''storing them as attributes of main_window so they aren't destroyed'''
    main_window.main_loop_thread = QThread()
    main_window.motor_thread = QThread()
    
    # ----------------------------- move workers to separate threads ------------------------------
    main_loop_worker.moveToThread(main_window.main_loop_thread)
    motor_worker.moveToThread(main_window.motor_thread)

    # ------------------------------------- connect to signals ------------------------------------

    # start timer once thread has started
    main_window.main_loop_thread.started.connect(
        lambda: main_loop_worker.start_loop(500)
    ) 

    # update UI
    main_loop_worker.final_data.connect(update_ui)

    '''NEXT: build RA/DEC stack from UI to motor controller '''
    # ------------------------------------- start the threads -------------------------------------
    main_window.main_loop_thread.start()
    main_window.motor_thread.start()

    # ---------------------------------------- run the app ----------------------------------------
    main_window.show()

    # app.exec() -> When the windows is closed the code will resume frome here, and start the shutdown
    exit_code = app.exec() 
    
    # -------------------------------------- clean shutdown ---------------------------------------
    # stop threads
    main_window.main_loop_thread.quit()
    main_window.motor_thread.quit()
    
    # wait for threads to finish
    main_window.main_loop_thread.wait()
    main_window.motor_thread.wait()
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
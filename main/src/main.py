import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread
from ui.ui_main import SatelliteTrackerApp
from utils.motor_controller import MotorWorker
from core.main_loop import MainLoop

def main():
    app = QApplication(sys.argv)
    
    # -------- initialize UI and workers --------
    main_window = SatelliteTrackerApp()
    main_loop_worker = MainLoop()
    motor_worker = MotorWorker(ip="127.0.0.1", port=65432)
    
    # ----- move workers to separate threads ----
    main_loop_thread = QThread()
    main_loop_worker.moveToThread(main_loop_thread)

    motor_thread = QThread()
    motor_worker.moveToThread(motor_thread)
    

    '''
    NEXT: build RA/DEC stack from UI to motor controller 
    
    '''


    # --------- Connect Signals & Slots ---------
    # # UI -> Worker
    # '''
    #     if request_motor_move.emit(data) in ui_main.py gets called
    #     then send_command(data) in motor_controller.py gets executed
    # '''
    # main_window.request_motor_move.connect(motor_worker.send_command)
    
    # # Worker -> UI
    # motor_worker.log_signal.connect(main_window.log_message)
    
    # # Start thread and connect
    # motor_thread.start()
    # motor_worker.connect_controller() # Start connection attempt

    # # 1. Calc -> UI (Update the Map and Labels)
    # calc_worker.results_ready.connect(window.update_ui_elements)

    # # 2. Calc -> Motor (Tell the motor where to go)
    # calc_worker.results_ready.connect(
    #     lambda data: motor_worker.send_command(data['target_az'], data['target_el'])
    # )

    # # Start logic
    # calc_thread.start()
    # calc_worker.start_loop(500) # Run every 500ms

    main_window.show()
    
    # Clean shutdown
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread
from ui.ui_main import SatelliteTrackerApp
from utils.motor_controller import MotorWorker

def main():
    app = QApplication(sys.argv)
    
    # 1. Initialize UI and Worker
    main_window = SatelliteTrackerApp()
    motor_worker = MotorWorker(ip="127.0.0.1", port=65432)
    
    # 2. Move worker to a separate thread
    motor_thread = QThread()
    motor_worker.moveToThread(motor_thread)
    
    # 3. Connect Signals & Slots
    # UI -> Worker
    '''
        if request_motor_move.emit(data) in ui_main.py gets called
        then send_command(data) in motor_controller.py gets executed
    '''
    main_window.request_motor_move.connect(motor_worker.send_command)
    
    # Worker -> UI
    motor_worker.log_signal.connect(main_window.log_message)
    
    # Start thread and connect
    motor_thread.start()
    motor_worker.connect_controller() # Start connection attempt

    main_window.show()
    
    # Clean shutdown
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
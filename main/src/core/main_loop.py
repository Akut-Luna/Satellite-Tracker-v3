
'''
    this will be the new update_continuously
'''
from PySide6.QtCore import QObject, Signal, QTimer

class MainLoop(QObject):
    final_data = Signal(dict) # Send az, el, doppler, etc. to UI

    def __init__(self):
        super().__init__()

    def start_loop(self, interval_ms):
        self.timer = QTimer()
        self.timer.timeout.connect(self.main_loop) # every interval_ms: call main_loop
        self.timer.start(interval_ms)

    def main_loop(self):

        data = {} # TODO
        print('hi from main loop')

        self.final_data.emit(data)


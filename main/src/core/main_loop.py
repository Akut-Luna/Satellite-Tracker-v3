
'''
    this will be the new update_continuously
'''
# here:
from PySide6.QtCore import QObject, Signal, QTimer

class MainLoop(QObject):
    final_data = Signal(dict) # Send az, el, doppler, etc. to UI

    def __init__(self):
        super().__init__()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.main_loop)

    def start_loop(self, interval_ms):
        self.timer.start(interval_ms)

    def main_loop(self):

        data = {} # TODO

        self.final_data.emit(data)


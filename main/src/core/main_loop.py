
'''
    this will be the new update_continuously
'''

import time 
from PySide6.QtCore import QObject, Signal, QTimer

class MainLoop(QObject):
    final_data = Signal(dict) # Send az, el, doppler, etc. to UI

    def __init__(self):
        super().__init__()
        self.t0 = time.time()

        # state of the UI
        self.current_ra = 0.0
        self.current_dec = 0.0

    def update_current_RA(self, ra_value):
        '''
        This slot receives data from the UI signals
        '''
        self.current_ra = float(ra_value)
        print(f"Worker RA updated to: {self.current_ra}")

    def update_current_DEC(self, dec_value):
        '''
        This slot receives data from the UI signals
        '''
        self.current_dec = float(dec_value)
        print(f"Worker DEC updated to: {self.current_dec}")

    def start_loop(self, interval_ms):
        self.timer = QTimer()
        self.timer.timeout.connect(self.main_loop) # every interval_ms: call main_loop
        self.timer.start(interval_ms)

    def main_loop(self):

        # TODO get data from UI

        data = {
            'time' : time.time() - self.t0
        } 
        print('hi from main loop')

        self.final_data.emit(data)


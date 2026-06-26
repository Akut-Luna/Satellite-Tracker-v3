import os
import numpy as np
import matplotlib.pyplot as plt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas # must be imported after PySide

class NexPassVisualisationWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Next Pass Visualisation')
        self.setWindowIcon(QIcon(os.path.join('main', 'images', 'satellite_icon_white.svg')))
        layout = QVBoxLayout(self)
        
        self.fig, self.ax = plt.subplots()
        canvas = FigureCanvas(self.fig)
        layout.addWidget(canvas)

        self.ax.set_aspect('equal')
        self.ax.set_xlim(-1.1, 1.1)
        self.ax.set_ylim(-1.1, 1.1)

        # draw concentric circles for elevation
        for r in [1, 2/3, 1/3, 0]:  # 0°, 30°, 60° elevation rings
            circle = plt.Circle((0, 0), r, fill=False, color='gray')
            self.ax.text(0.1, r, f'{int((1-r)*90)}°', ha='center', va='bottom', fontsize=12, color='gray')
            self.ax.add_patch(circle)

        self.ax.hlines([0], [-1.05], [1.05], color='gray')
        self.ax.vlines([0], [-1.05], [1.05], color='gray')

        # Cardinal labels
        self.ax.text(0, 1.1, 'N', ha='center', va='bottom', fontsize=10)
        self.ax.text(1.1, 0, 'E', ha='left', va='center', fontsize=10)
        self.ax.text(0, -1.1, 'S', ha='center', va='top', fontsize=10)
        self.ax.text(-1.1, 0, 'W', ha='right', va='center', fontsize=10)

        self.ax.axis('off')

    def az_el_to_xy(self, az_deg, el_deg):
        r = (90 - el_deg) / 90  # scale to [0,1]
        theta = -np.radians(az_deg) + np.pi/2 # N is up and azimuth increases cockwise
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        return x, y
    
    def label_plot(self, text, x, y):
        if x > 0: # right
            self.ax.text(x+0.05, y, text, ha='left', va='center', fontsize=10)
        if x < 0: # left
            self.ax.text(x-0.05, y, text, ha='right', va='center', fontsize=10)

    def plot(self, data, start_time, end_time, UTC):
        '''
        Parameters:
            data (list): shape (N,2) az, el values for the next path
            start_time (datetime): time of AOS 
            end_time (datetime): time of LOS
            UTC (bool): flag that shows if time is in UTC or Local Time
        '''
        az = data[:,0]
        el = data[:,1]

        x, y = self.az_el_to_xy(az, el)
        self.ax.plot(x,y)

        # Labels
        if UTC:
            tz = 'UTC'
        else:
            tz = 'Local Time'
        
        start_time_str = str(start_time.time()).split('.')[0]
        end_time_str = str(end_time.time()).split('.')[0]
            
        self.label_plot(f'AOS ({tz})\n{start_time_str}', x[0], y[0])
        self.label_plot(f'LOS ({tz})\n{end_time_str}', x[-1], y[-1])


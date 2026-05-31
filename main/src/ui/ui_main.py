from PySide6.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget, QTextEdit
from PySide6.QtCore import Signal

class SatelliteTrackerApp(QMainWindow):
    # Signal to request action from worker
    request_motor_move = Signal(float, float)

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Satellite Tracker')
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.console = QTextEdit(readOnly=True)
        self.btn = QPushButton("Move Motor")
        self.btn.clicked.connect(lambda: self.request_motor_move.emit(45.0, 10.0))
        
        layout.addWidget(self.btn)
        layout.addWidget(self.console)
        
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def log_message(self, msg):
        self.console.append(msg)
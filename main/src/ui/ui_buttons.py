import traceback
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox, 
    QDateTimeEdit, QRadioButton, QCheckBox, QButtonGroup, QFileDialog,
    QGroupBox, QGridLayout, QSpinBox, QDoubleSpinBox,
    QStackedWidget, QFrame
)
import os

def browse_list(self):
    file_path, _ = QFileDialog.getOpenFileName(
        self, 'Select List', '', '*.json'
    )
    if file_path:
        while self.tracking_mode_list_dropdown.count() > 0:
            self.tracking_mode_list_dropdown.removeItem(0)
        self.tracking_mode_list_dropdown.addItems(self.get_target_names_from_file(file_path))
        base_path = os.getcwd()
        relative_path = os.path.relpath(file_path, base_path) # absolut path is a bit long
        self.list_input.setText(relative_path)


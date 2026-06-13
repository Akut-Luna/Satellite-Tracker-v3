import traceback
from PySide6.QtWidgets import QFileDialog
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
        try:
            relative_path = os.path.relpath(file_path, base_path) # absolut path is a bit long
            self.list_input.setText(relative_path)
        except:
            self.list_input.setText(file_path)


def add_to_list(self):
    pass # TODO


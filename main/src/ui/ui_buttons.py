import traceback
from PySide6.QtWidgets import QFileDialog
import os
import spiceypy
import pandas as pd


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

def browse_OMM_file(self):
    file_path, _ = QFileDialog.getOpenFileName(
        self, 'Select OMM File (.csv)', 'test', '(*.csv)'
    )
    if file_path:
        try: # read file
            self.omm_df = pd.read_csv(file_path)
            
            base_path = os.getcwd()
            try:
                relative_path = os.path.relpath(file_path, base_path) # absolut path is a bit long
                self.OMM_file_input.setText(relative_path)
            except:
                self.OMM_file_input.setText(file_path)
        except Exception as e:
            self.log_message(f'Error reading data from file {file_path}: {e}')
            print(traceback.format_exc())

def browse_spice_file(self):
    file_path, _ = QFileDialog.getOpenFileName(
        self, 'Select SPICE Meta Kernel', '', 'All Files (*)'
    )
    if file_path:
        self.spice_input.setText(file_path)
        
        base_path = os.getcwd()
        try:
            relative_path = os.path.relpath(file_path, base_path) # absolut path is a bit long
            self.OMM_file_input.setText(relative_path)
        except:
            self.OMM_file_input.setText(file_path)

        # Load all kernels from meta-kernel
        try:
            spiceypy.furnsh(file_path)
            self.spice_kernels_loaded = True
        except Exception as e:
            self.log_message(f'Could not load SPICE Kernels: {e}')
            print(traceback.format_exc())


def add_to_list(self):
    pass # TODO


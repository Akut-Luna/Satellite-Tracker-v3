import traceback
from PySide6.QtWidgets import QFileDialog
import os
import pandas as pd

def browse_list(self):
    base_path = os.getcwd()
    default_folder = os.path.join(base_path, 'main', 'data', 'Lists')
    os.makedirs(default_folder, exist_ok=True)
    file_path, _ = QFileDialog.getOpenFileName(
        self, 'Select List', f'{default_folder}', '*.json'
    )
    if file_path:
        # remove old list
        while self.tracking_mode_list_dropdown.count() > 0:
            self.tracking_mode_list_dropdown.removeItem(0)

        # add new list
        self.tracking_mode_list_dropdown.addItems(self.get_target_names_from_file(file_path))

        self.target_list_path_changed.emit(file_path) # -> main_loop

        try: # update UI
            file_path = os.path.relpath(file_path, base_path) # absolut path is a bit long
            self.list_input.setText(file_path)
        except:
            pass # it will automatically set the absolut path

def browse_OMM(self):
    base_path = os.getcwd()
    default_folder = os.path.join(base_path, 'main', 'data', 'OMM')
    os.makedirs(default_folder, exist_ok=True)
    file_path, _ = QFileDialog.getOpenFileName(
        self, 'Select OMM File (.csv)', f'{default_folder}', '(*.csv)'
    )
    if file_path:
        try: # read file
            OMM_df = pd.read_csv(file_path)
            self.OMM_df_changed.emit(OMM_df) # -> main_loop
        except Exception as e:
            self.log_message(f'Error reading data from file {file_path}: {e}')
            print(traceback.format_exc())
        
        try: # update UI
            file_path = os.path.relpath(file_path, base_path) # absolut path is a bit long
            self.OMM_input.setText(file_path)
        except:
            pass # it will automatically set the absolut path

def browse_spice(self):
    base_path = os.getcwd()
    default_folder = os.path.join(base_path, 'main', 'data', 'Kernels')
    os.makedirs(default_folder, exist_ok=True)
    file_path, _ = QFileDialog.getOpenFileName(
        self, 'Select SPICE Meta Kernel', f'{default_folder}', 'All Files (*)'
    )
    if file_path:
        self.spice_kernels_changed.emit(file_path) # -> main_loop
        
        self.spice_input.setText(file_path)
        base_path = os.getcwd()
        try:
            file_path = os.path.relpath(file_path, base_path) # absolut path is a bit long
            self.spice_input.setText(file_path)
        except:
            pass # it will automatically set the absolut path

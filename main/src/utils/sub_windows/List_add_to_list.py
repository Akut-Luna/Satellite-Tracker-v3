import os
import json
import traceback
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QComboBox, 
    QGridLayout, QStackedWidget
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon

from utils.helper import ra_dec_parser

class ListAddToListWindow(QWidget):
    # ------------------------------------ Signals (send data) ------------------------------------
    update_ui = Signal(str)
    log = Signal(str)
    new_target_added = Signal()
    # ---------------------------------------------------------------------------------------------

    def __init__(self, target_list_path):
        super().__init__()
        self.setWindowTitle('Add new target to list')
        self.setWindowIcon(QIcon(os.path.join('main', 'images', 'satellite_icon_white.svg')))
        self.setGeometry(100, 100, 1000, 250) # set inital pos and size

        self.target_list_path = target_list_path

        # ui
        self.setup_ui()
        self.set_style()

    def log_message(self, message):
        self.log.emit(message) # -> ui

    def setup_ui(self):
        # Main layout for the window
        main_layout = QVBoxLayout(self)

        # target type selection
        target_type_layout = QHBoxLayout()
        target_type_layout.addWidget(QLabel('Target Type:'))
        self.target_type_combo = QComboBox()
        self.target_type_combo.addItems(['LEO', 'DS', 'ASTRO'])
        self.target_type_combo.currentIndexChanged.connect(self.target_type_changed)
        target_type_layout.addWidget(self.target_type_combo, 1)

        main_layout.addLayout(target_type_layout)
        
        # Stacked widget to switch between target type input options
        self.target_type_stack = QStackedWidget()
        main_layout.addWidget(self.target_type_stack)

        # ---------------------------------------- 0. LEO -----------------------------------------
        self.leo_widget = QWidget()
        leo_layout = QGridLayout(self.leo_widget)

        # Name
        leo_layout.addWidget(QLabel('Name:'), 0, 0)
        self.leo_name_input = QLineEdit()
        leo_layout.addWidget(self.leo_name_input, 0, 1)
        
        # Horizons id
        leo_layout.addWidget(QLabel('NORAD id:'), 1, 0)
        self.leo_id_input = QLineEdit()
        leo_layout.addWidget(self.leo_id_input, 1, 1)
        
        # frequency
        leo_layout.addWidget(QLabel('Frequency [MHz]:'), 2, 0)
        self.leo_frequency_input = QLineEdit()
        self.leo_frequency_input.setText('0.0')
        leo_layout.addWidget(self.leo_frequency_input, 2, 1)
        
        self.target_type_stack.addWidget(self.leo_widget)
        
        # ----------------------------------------- 1. DS -----------------------------------------
        self.ds_widget = QWidget()
        ds_layout = QGridLayout(self.ds_widget)

        # Name
        ds_layout.addWidget(QLabel('Name:'), 0, 0)
        self.ds_name_input = QLineEdit()
        ds_layout.addWidget(self.ds_name_input, 0, 1)
        
        # Horizons id
        ds_layout.addWidget(QLabel('Horizons id:'), 1, 0)
        self.ds_id_input = QLineEdit()
        ds_layout.addWidget(self.ds_id_input, 1, 1)
        
        # frequency
        ds_layout.addWidget(QLabel('Frequency [MHz]:'), 2, 0)
        self.ds_frequency_input = QLineEdit()
        self.ds_frequency_input.setText('0.0')
        ds_layout.addWidget(self.ds_frequency_input, 2, 1)

        self.target_type_stack.addWidget(self.ds_widget)

        # --------------------------------------- 2. ASTRO ----------------------------------------
        self.astro_widget = QWidget()
        astro_layout = QGridLayout(self.astro_widget)
        
        # Name
        astro_layout.addWidget(QLabel('Name:'), 0, 0)
        self.astro_name_input = QLineEdit()
        astro_layout.addWidget(self.astro_name_input, 0, 1, 1, 2)

        # RA
        astro_layout.addWidget(QLabel('RA [h]:'), 1, 0)
        self.astro_ra_input = QLineEdit()
        astro_layout.addWidget(self.astro_ra_input, 1, 1)
        astro_layout.addWidget(QLabel('Accepted format: xx.xxxx or xxh xxm xxs'), 1, 2)

        # DEC
        astro_layout.addWidget(QLabel('DEC [°]:'), 2, 0)
        self.astro_dec_input = QLineEdit()
        astro_layout.addWidget(self.astro_dec_input, 2, 1)
        astro_layout.addWidget(QLabel('Accepted format: xx.xxxx or +xx°' + " xx'" +' xx"'), 2, 2)
        
        # frequency
        astro_layout.addWidget(QLabel('Frequency [MHz]:'), 3, 0)
        self.astro_frequency_input = QLineEdit()
        self.astro_frequency_input.setText('0.0')
        astro_layout.addWidget(self.astro_frequency_input, 3, 1, 1, 2)

        self.target_type_stack.addWidget(self.astro_widget)
        # -----------------------------------------------------------------------------------------

        self.add_btn = QPushButton('Add')
        self.add_btn.clicked.connect(self.add_to_list)
        main_layout.addWidget(self.add_btn)

        self.setLayout(main_layout)
    
    def set_style(self):
        '''
        Set font size and maximum size of UI elements
        '''

        self.setStyleSheet('QWidget { font-size: 11pt; }') 

    def target_type_changed(self, index):
        self.target_type_stack.setCurrentIndex(index)

    def add_to_list(self):
        json_file = self.target_list_path
        
        if self.target_type_combo.currentIndex() == 0: # LEO --------------------------------------
            target_name = self.leo_name_input.text()
            if target_name == '':
                self.log_message('Provide target name.')
                return

            try:
                f0 = float(self.leo_frequency_input.text())
            except:
                self.log_message('Provide valid frequency.')
                return
                            
            try:
                target_id = int(self.leo_id_input.text())
            except:
                self.log_message('Provide valid NORAD id.')
                return
            
            new_entry = {
                'type': 'LEO',
                'name': target_name,
                'frequency': f0,
                'NORAD': target_id
            }

            # Load existing data or start with an empty list
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f) 
            except (FileNotFoundError, json.JSONDecodeError):
                data = []

            # Check if target is already in JSON
            if not any(entry.get('NORAD') == target_id for entry in data):
                # save to JSON
                data.append(new_entry)
                with open(json_file, 'w') as f:
                    json.dump(data, f, indent=4)
                self.log_message(f'{target_name} was added to {self.target_list_path}.')
            else:
                self.log_message(f'{target_name} is already in {self.target_list_path}.')
                return

            self.leo_name_input.setText('')
            self.leo_id_input.setText('')
            self.leo_frequency_input.setText('0.0')

        elif self.target_type_combo.currentIndex() == 1: # DS -------------------------------------
            target_name = self.ds_name_input.text()
            if target_name == '':
                self.log_message('Provide target name.')
                return
                            
            try:
                f0 = float(self.ds_frequency_input.text())
            except:
                self.log_message('Provide valid frequency.')
                return
                            
            try:
                target_id = int(self.ds_id_input.text())
            except:
                self.log_message('Provide valid Horizons id.')
                return
            
            new_entry = {
                'type': 'DS',
                'name': target_name,
                'frequency': f0,
                'Horizons': target_id
            }
        
            # Load existing data or start with an empty list
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                data = []

            # Check if target is already in JSON
            if not any(entry.get('Horizons') == target_id for entry in data):
                # save to JSON
                data.append(new_entry)
                with open(json_file, 'w') as f:
                    json.dump(data, f, indent=4)
                self.log_message(f'{target_name} was added to {self.target_list_path}.')
            else:
                self.log_message(f'{target_name} is already in {self.target_list_path}.')
                return
            
            self.ds_name_input.setText('')
            self.ds_id_input.setText('')
            self.ds_frequency_input.setText('0.0')

        elif self.target_type_combo.currentIndex() == 2: # ASTRO ----------------------------------
            target_name = self.astro_name_input.text()
            if target_name == '':
                self.log_message('Provide target name.')
                return

            try:
                ra_value = self.astro_ra_input.text()
                if ra_value == '':
                    ra_hours = 0.0
                else:
                    ra_hours = ra_dec_parser(ra_value)
            except Exception as e:
                self.log_message(f'Error parsing RA: {e}')
                print(traceback.format_exc())
                return

            try:
                dec_value = self.astro_dec_input.text()
                if dec_value == '':
                    dec_degrees = 0.0
                else:
                    dec_degrees = ra_dec_parser(dec_value)
            except Exception as e:
                self.log_message(f'Error parsing DEC: {e}')
                print(traceback.format_exc())
                return

            try:
                f0 = float(self.astro_frequency_input.text())
            except:
                self.log_message('Provide valid frequency.')
                return

            new_entry = {
                'type': 'ASTRO',
                'name': target_name,
                'frequency': f0,
                'RA': ra_hours,
                'DEC': dec_degrees
            }

            # Load existing data or start with an empty list
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                data = []

            # Check if target is already in JSON
            if not any((entry.get('RA') == new_entry['RA'] and entry.get('DEC') == new_entry['DEC']) for entry in data):
                data.append(new_entry)
                with open(json_file, 'w') as f:
                    json.dump(data, f, indent=4)
                self.log_message(f'{target_name} was added to {self.target_list_path}.')
            else:
                self.log_message(f'{target_name} is already in {self.target_list_path}.')
                return

            self.astro_name_input.setText('')
            self.astro_frequency_input.setText('0.0')
            self.astro_ra_input.setText('')
            self.astro_dec_input.setText('')

        self.update_ui.emit(target_name)
        self.new_target_added.emit()

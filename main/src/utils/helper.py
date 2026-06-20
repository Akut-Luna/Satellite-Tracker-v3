import re
import os
import json
import shutil
import traceback
import numpy as np
import pandas as pd
from datetime import datetime
from scipy.interpolate import interp1d
from skyfield.api import load, Loader, EarthSatellite

def load_planet_ephemeris(self):
    filename = 'de421.bsp'
    ephemeris_folder = os.path.join('main', 'data', 'Ephemeris')
    ephemeris_file = os.path.join(ephemeris_folder, filename)

    # if needed: download
    if not os.path.exists(ephemeris_file) and not os.path.exists(filename):
        tmp_loader = Loader('.')
        tmp_loader.download(filename) 

    # if needed: move to folder
    if os.path.exists(filename):
        os.makedirs(ephemeris_folder, exist_ok=True)
        shutil.move(filename, ephemeris_file)

    self.planet_ephemeris = load(ephemeris_file)  

def get_target_names_from_file(self, list_path:str):
    try:
        with open(list_path, 'r') as file:
            target_data = json.load(file)
            target_names = [target['name'] for target in target_data] 
            return target_names
    except Exception as e:
        print(traceback.format_exc())
        print(                                                  )
        print('>>>>>>>> IF PROGRAM CRASHED AT START UP <<<<<<<<')
        print(                                                  )
        print('  Check that main/data/Lists/default_list.json  ')
        print('  exists and contains a vaild list.             ')
        print(                                                  )
        print('>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<')
        print(                                                  )
        self.log_message(f'Error reading target list file: {e}')
        return []

def ra_dec_parser(value: str) -> float:
    s = value.strip().replace(",", ".")

    try:
        res = float(value) # if it can be turned into a float
        return res         # it is allready in the decimal form
    except ValueError:
        pass

    s = (
        s.replace("º", "°")
        .replace("′", "'")
        .replace("’", "'")
        .replace("″", '"')
        .replace("''", '"')
    )

    matches = re.findall(
        r"([+-]?\d+(?:\.\d+)?)\s*(h|m|s|°|d|'|\")", s, flags=re.IGNORECASE
    )

    if not matches:
        raise ValueError(f"Could not parse coordinate string: {value}")
        
    sign = -1 if "-" in s else 1
    units = {u: 0.0 for u in ["h", "m", "s", "°", "'", '"']}

    for num, unit in matches:
        units[unit.lower()] = abs(float(num))

    if any(u in s.lower() for u in ("h", "m", "s")):
        return sign * (units["h"] + units["m"] / 60 + units["s"] / 3600) # RA
    return sign * (units["°"] + units["'"] / 60 + units['"'] / 3600)     # DEC

def OMM_add_to_list(self):
    if self.OMM_satellite is not None:
        sat_name = self.OMM_satellite.name
        sat_id = self.OMM_satellite.model.satnum
        f0 = self.doppler_init_freq

        new_entry = {
            'type': 'LEO',
            'name': sat_name,
            'frequency': f0,
            'NORAD': sat_id
        }

        json_file = self.target_list_path

        # Load existing data or start with an empty list
        try:                                    # we can't use self.target_list becasue
            with open(json_file, 'r') as file:  # it also contains the data which we
                data = json.load(file)          # don't want to save in the JSON
        except (FileNotFoundError, json.JSONDecodeError):
            data = []

        # Check if the satellie is already in JSON
        if not any(entry.get('NORAD') == sat_id for entry in data):
            # save to JSON
            data.append(new_entry)
            with open(json_file, 'w') as file:
                json.dump(data, file, indent=4)
            self.log_message(f'{sat_name} was added to the list.')

            # add to list in memory
            new_entry['EarthSatellite'] = self.OMM_satellite
            self.target_list.append(new_entry)
            self.add_to_list.emit(sat_name) # -> ui
        else:
            self.log_message(f'{sat_name} is already in the list.')

    else:
        self.log_message('No satellite selected!')

def make_interpolators(df):
    # turn time into a monoton increasing number
    start_time = datetime.strptime(df['time_UTC'].min(), '%Y-%m-%d %H:%M:%S.%f')
    times = pd.to_datetime(df['time_UTC'])
    x = (times - start_time).dt.total_seconds().to_numpy()

    # create a dictionary of interpolators for all numeric columns
    cols = df.columns.drop("time_UTC")
    interpolators = {
        col: interp1d(x, df[col].values, kind="cubic") for col in cols
    }

    return interpolators, start_time

def load_target_list_json(self):
    '''
    This function first loads the currently selected list from JSON.
    '''
    try: # load list
        with open(self.target_list_path, 'r') as file:
            target_list = json.load(file)
            return target_list
    except Exception as e:
        print(traceback.format_exc())
        print(                                                  )
        print('>>>>>>>> IF PROGRAM CRASHED AT START UP <<<<<<<<')
        print(                                                  )
        print('  Check that main/data/Lists/default_list.json  ')
        print('  exists and contains a vaild list.             ')
        print(                                                  )
        print('>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<')
        print(                                                  )
        self.log_message(f'Error reading target list file: {e}')
        return []
    
def load_target_list_data(self, OMM_only=False, Horizons_id=None):
    '''
    Then it will load the needed data for each target and add it to the list.
            Parameters:
            celestrak_only (bool): Flag if we want to only (re)load the CelesTrak data
            ID (int): Id of spacecraft. When we want to only (re)load the Horizon data for a specific spacecraft

    '''    
    try: # load OMM data
        default_OMM_path = os.path.join('main', 'data', 'OMM', 'all_active_satellites.csv')
        OMM_df = pd.read_csv(default_OMM_path)
    except Exception as e:
        print(traceback.format_exc())
        print(                                                          )
        print('>>>>>>>>>>>> IF PROGRAM CRASHED AT START UP <<<<<<<<<<<<')
        print(                                                          )
        print('  Check that main/data/OMM/all_active_satellites.json   ')
        print('  exists and contains data.                             ')
        print(                                                          )
        print('>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<<')
        print(                                                          )
        self.log_message(f'Error reading OMM data: {e}')

    try:
        for target in self.target_list:
            target['type'] = target['type'].upper() # just to be safe

            if target['type'] == 'LEO': # ---------------------------------------------------------
                fields = OMM_df[OMM_df['NORAD_CAT_ID'] == target['NORAD']]
                if not fields.empty:
                    fields = fields.iloc[0].to_dict()
                    satellite = EarthSatellite.from_omm(self.skyfield_ts, fields)
                    target['EarthSatellite'] = satellite
                else:
                    self.log_message(f'Data for {target} is empty.')

            elif target['type'] == 'DS': # --------------------------------------------------------
                spacecraft_id = target['Horizons'] 
                
                if OMM_only: # When only OMM data was updated there
                    continue # is no need to reload Horizon data.

                if Horizons_id is not None:          # When the Horizons data for one target got updated
                    if Horizons_id != spacecraft_id: # there is no need to update the other targets too.
                        continue

                '''
                NOTE: We do not combine the two data sets into one. The reason for this is, that the can 
                have different resolutions. So using two different interpolators is easier. 
                '''

                # first load the data that comes directly from Horizons
                df = None
                file_name = f'{spacecraft_id}_from_observer_ephemerides.csv'
                file_path = os.path.join('main', 'data', 'Horizons', file_name)
                if os.path.exists(file_path):
                    df = pd.read_csv(file_path)
                else:
                    self.log_message(f'File does not exist: {file_path}')
                    try:
                        # download data
                        self.log_message(f'Downloading new data for Spacecraft {spacecraft_id}...')
                        self.query_horizons_api(spacecraft_id)
                        
                        # and try again
                        df = pd.read_csv(file_path)
                    except Exception as e:
                        self.log_message(f'Error downloading and reading data: {str(e)}')
                        print(traceback.format_exc())

                if df is not None:
                    interpolators, start_time = make_interpolators(df)
                    target['interpolators_directly'] = interpolators
                    target['start_time_directly'] = start_time
                
                # then load the data calculated from state vectors
                df = None
                file_name = f'{spacecraft_id}_from_state_vectors.csv'
                file_path = os.path.join('main', 'data', 'Horizons', file_name)
                if os.path.exists(file_path):
                    df = pd.read_csv(file_path)
                else:
                    self.log_message(f'File does not exist: {file_path}')
                    try:
                        # download data
                        self.log_message(f'Downloading new data for Spacecraft {spacecraft_id}...')
                        self.query_horizons_api(spacecraft_id)
                        
                        # and try again
                        df = pd.read_csv(file_path)
                    except Exception as e:
                        self.log_message(f'Error downloading and reading data: {str(e)}')
                        print(traceback.format_exc())

                if df is not None:
                    interpolators, start_time = make_interpolators(df)
                    target['interpolators_from_vector'] = interpolators
                    target['start_time_from_vector'] = start_time
    
            elif target['type'] == 'ASTRO': # -----------------------------------------------------
                pass # for ASTRO there is nothing to do

            else: # -------------------------------------------------------------------------------
                self.log_message(f'Unknowen target type: {target['type']}')

    except Exception as e:
        print(traceback.format_exc())
        self.log_message(f'Error while adding data to target list: {e}')
        return []
    
def should_flight_path_get_calculated(self, now_datetime):
    if self.last_time_flight_path_got_calculated is not None:
        delta_t_min = (now_datetime - self.last_time_flight_path_got_calculated).total_seconds() // 60
    else:
        delta_t_min = self.config.min_before_recalculate_flight_path
        self.last_time_flight_path_got_calculated = now_datetime

    return delta_t_min >= self.config.min_before_recalculate_flight_path


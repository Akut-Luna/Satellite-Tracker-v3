import re
import os
import json
import shutil
import traceback
import numpy as np
import pandas as pd
from datetime import datetime
from scipy.optimize import brentq
from scipy.interpolate import interp1d
from skyfield.api import load, Loader, EarthSatellite, wgs84

from utils.time_convertions import datetime_to_skyfield_time, skyfield_time_to_datetime, local_time_to_UTC, UTC_to_local_time

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
    s = value.strip().replace(',', '.')

    try:
        res = float(value) # if it can be turned into a float
        return res         # it is allready in the decimal form
    except ValueError:
        pass

    s = (
        s.replace('º', '°')
        .replace('′', "'")
        .replace('’', "'")
        .replace('″', '"')
        .replace("''", '"')
    )

    matches = re.findall(
        r"([+-]?\d+(?:\.\d+)?)\s*(h|m|s|°|d|'|\")", s, flags=re.IGNORECASE
    )

    if not matches:
        raise ValueError(f'Could not parse coordinate string: {value}')
        
    sign = -1 if '-' in s else 1
    units = {u: 0.0 for u in ['h', 'm', 's', '°', "'", '"']}

    for num, unit in matches:
        units[unit.lower()] = abs(float(num))

    if any(u in s.lower() for u in ('h', 'm', 's')):
        return sign * (units['h'] + units['m'] / 60 + units['s'] / 3600) # RA
    return sign * (units['°'] + units["'"] / 60 + units['"'] / 3600)     # DEC

def OMM_add_to_list(self):
    if self.OMM_satellite is not None:
        sat_name = self.OMM_satellite.name
        sat_id = self.OMM_satellite.model.satnum
        f0 = self.doppler_emited_freq

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
            self.log_message(f'{sat_name} was added to {self.target_list_path}.')

            # add to list in memory
            new_entry['EarthSatellite'] = self.OMM_satellite
            self.target_list.append(new_entry)
            self.add_to_list_dropdown.emit(sat_name) # -> ui
        else:
            self.log_message(f'{sat_name} is already in {self.target_list_path}.')

    else:
        self.log_message('No satellite selected!')

def make_interpolators(df):
    # turn time into a monoton increasing number
    start_time = datetime.strptime(df['time_UTC'].min(), '%Y-%m-%d %H:%M:%S.%f')
    times = pd.to_datetime(df['time_UTC'])
    x = (times - start_time).dt.total_seconds().to_numpy()

    # create a dictionary of interpolators for all numeric columns
    cols = df.columns.drop('time_UTC')
    interpolators = {
        col: interp1d(x, df[col].values, kind='cubic') for col in cols
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
                spacecraft_name = target['name']

                if OMM_only: # When only OMM data was updated there
                    continue # is no need to reload Horizon data.

                if Horizons_id is not None:          # When the Horizons data for one target got updated
                    if Horizons_id != spacecraft_id: # there is no need to update the other targets too.
                        continue

                '''
                NOTE: We do not combine the two data sets into one. The reason for this is, that the can 
                have different resolutions. So using two different interpolators is easier. 
                '''

                # ------------- first load the data that comes directly from Horizons -------------
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
                        self.query_horizons_api(spacecraft_id, spacecraft_name)
                        
                        # and try again
                        df = pd.read_csv(file_path)
                    except Exception as e:
                        self.log_message(f'Error downloading and reading data: {str(e)}')
                        print(traceback.format_exc())

                if df is not None:
                    interpolators, start_time = make_interpolators(df)
                    target['interpolators_directly'] = interpolators
                    target['start_time_directly'] = start_time
                                    
                # ---------------- then load the data calculated from state vectors ---------------
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
                        self.query_horizons_api(spacecraft_id, spacecraft_name)
                        
                        # and try again
                        df = pd.read_csv(file_path)
                    except Exception as e:
                        self.log_message(f'Error downloading and reading data: {str(e)}')
                        print(traceback.format_exc())

                if df is not None:
                    interpolators, start_time = make_interpolators(df)
                    target['interpolators_from_vector'] = interpolators
                    target['start_time_from_vector'] = start_time
                    
                    # save df for use in find passes
                    find_passes_df = df[['time_UTC', 'el_deg']]
                    target['find_passes_df'] = find_passes_df
    
            elif target['type'] == 'ASTRO': # -----------------------------------------------------
                pass # for ASTRO there is nothing to do

            else: # -------------------------------------------------------------------------------
                self.log_message(f'Unknowen target type: {target['type']}')

    except Exception as e:
        print(traceback.format_exc())
        self.log_message(f'Error while adding data to target list: {e}')
        return []
    
def should_ground_track_get_calculated(self, now_datetime):
    if self.last_time_ground_track_got_calculated is not None:
        delta_t_min = (now_datetime - self.last_time_ground_track_got_calculated).total_seconds() // 60
    else:
        delta_t_min = self.config.min_before_recalculate_ground_track
        self.last_time_ground_track_got_calculated = now_datetime

    return delta_t_min >= self.config.min_before_recalculate_ground_track

def find_passes(self, return_data=False):
    '''
    Finds the times when the satellite is rising over / setting under the horizon.

    Parameters:
        return_data (bool): if True it will not print to console and return the data. 

    Returns:
        passes (list): (N,2) dim list with AOS datetime and LOS datetime
    '''
    def find_passes_LEO(current_target, antenna_pos):
        # convert to Skyfield time
        start_time = datetime_to_skyfield_time(self.skyfield_ts, start_time)
        end_time = datetime_to_skyfield_time(self.skyfield_ts, end_time)

        satellite = current_target['EarthSatellite']
        times, events = satellite.find_events(antenna_pos, start_time, end_time, altitude_degrees=min_elevation)

        passes = []
        new_pass = []
        for t, event in zip(times, events):
            if event == 0: # satellite rises over horizon
                new_pass.append(t)
            elif event == 2 and len(new_pass) == 1: # satellite sets under horizon
                new_pass.append(t)
                passes.append(new_pass)
                new_pass = []

        for i in range(len(passes)):
            passes[i][0] = skyfield_time_to_datetime(passes[i][0])
            passes[i][1] = skyfield_time_to_datetime(passes[i][1])

        # convert back to data time
        start_time = skyfield_time_to_datetime(start_time)
        end_time = skyfield_time_to_datetime(end_time)

        return passes

    start_time = self.find_passes_start_time
    end_time = self.find_passes_end_time
    min_elevation = self.find_passes_min_angle

    if start_time >= end_time:
        self.log_message('End time must be after start time.')
        return
    
    # convert to UTC if needed
    if self.local_time_radio_button_checked:
        start_time = local_time_to_UTC(start_time)
        end_time = local_time_to_UTC(end_time)

    # ---------------------------------------- find passes ----------------------------------------
    self.log_message('Calculating passes...')
    if self.tracking_mode == 0: # List
        current_target = self.target_list[self.target_list_idx]

        if current_target['type'] == 'LEO':
            antenna_pos = wgs84.latlon(
                self.config.antenna_latitude, 
                self.config.antenna_longitude, 
                self.config.antenna_altitude
            )
            passes = find_passes_LEO(current_target, antenna_pos)

        elif current_target['type'] == 'DS':
            # Create a boolean mask
            above = df['elevation'] > threshold

            # AOS: False -> True
            aos_events = df[~above.shift(1, fill_value=False) & above]

            # LOS: True -> False
            los_events = df[above.shift(1, fill_value=True) & ~above]

            # --- fine ---
            # Function to find roots for: E(t) - threshold = 0
            func = lambda t: interpolator(t) - threshold

            # Find root within a specific time interval [t1, t2] where a crossing exists
            exact_time = brentq(func, t1, t2)




        elif current_target['type'] == 'ASTRO':
            pass # TODO

    else:
        self.log_message("The 'Find Passes' feature only works for the tracking mode 'List'.")
        return

    # convert back to Local Time if needed
    if self.local_time_radio_button_checked:
        start_time = UTC_to_local_time(start_time)
        end_time = UTC_to_local_time(end_time)

        for i in range(len(passes)):
            passes[i][0] = UTC_to_local_time(passes[i][0])
            passes[i][1] = UTC_to_local_time(passes[i][1])

    # ---------------------------------- Print results in console ---------------------------------
    if passes:
        if return_data:            
            return passes
        else:
            tz = 'UTC'
            if self.local_time_radio_button_checked:
                tz = 'Local Time'

            plural = 'es'
            if len(passes) == 1:
                plural = ''

            self.log_message(f'Found {len(passes)} pass{plural} for minimum elevation angle of {min_elevation}°')
            
            for i, p in enumerate(passes):
                self.log_message(f'---------------- Pass {i+1} ----------------')
                self.log_message(f'AOS: {p[0].strftime('%H:%M %d.%m.%Y')} {tz}')
                self.log_message(f'LOS: {p[1].strftime('%H:%M %d.%m.%Y')} {tz}')
    else:
        self.log_message('No passes found for the selected time range')

    #     if 'Horizons' in current_satellite['catalogs']: # Horizons
    #         current_time = start_time
    #         time_step = timedelta(minutes=10)  # Start with 10-minute steps
    #         min_time_step = timedelta(minutes=1)  # Minimum step size for precise detection
    #         max_time_step = timedelta(minutes=10)  # Maximum step size for precise detection
    #         passes = []
    #         new_pass = []

    #         last_el = None

    #         while current_time <= end_time:
    #             '''
    #             NOTE: idea for simpler rewrite
    #             - go in 10 min steps
    #             - if corssing crossing threshold:
    #                 - go back by 10 min
    #                 - go in 1 min steps
    #                 - if corssing crossing threshold:
    #                     - if last_el < el:
    #                         - AOS
    #                     - else:
    #                         - LOS
    #                     - go in 10 min steps                 
    #             '''
    #             _, topocentric = self.calculate_satellite_and_topocentric(current_satellite, self.datetime_to_skyfield_time(current_time))
    #             el, _, _, _, _, _ = topocentric.frame_latlon_and_rates(self.skyfield_antenna_pos)
    #             el = el.degrees

    #             # If this is the first point
    #             if last_el is None:
    #                 if el >= min_elevation:
    #                     new_pass.append(current_time)

    #                 last_el = el
    #                 current_time += time_step
    #                 continue
                
    #             # Check if we're crossing the elevation threshold
    #             crossing_threshold = (last_el < min_elevation and min_elevation <= el) or (last_el > min_elevation and min_elevation >= el)
                
    #             if crossing_threshold and time_step > min_time_step: # we went too far
    #                 # Back up and use a smaller step to find the crossing more precisely
    #                 current_time -= time_step
    #                 time_step = min_time_step
    #             else:
    #                 # Process the current point
    #                 if last_el < min_elevation and el >= min_elevation:  # AOS (Acquisition of Signal)
    #                     new_pass.append(current_time)
    #                 elif last_el >= min_elevation and el < min_elevation:  # LOS (Loss of Signal)
    #                     if len(new_pass) == 1:
    #                         new_pass.append(current_time)
    #                         passes.append(new_pass)
    #                         new_pass = []
                        
    #                 # Use larger steps when we're far from the threshold
    #                 delta_to_target = abs(el - min_elevation) # deg

    #                 if delta_to_target > 5:
    #                     time_step = max_time_step
    #                 elif delta_to_target > 1:
    #                     time_step_in_min = time_step.total_seconds()//60
    #                     rate = abs(el - last_el)/time_step_in_min # deg/min

    #                     time_step_temp = delta_to_target / rate # min
    #                     time_step_temp = int(time_step_temp) - 1 # min
    #                     time_step_temp = max(min_time_step.total_seconds()//60, time_step_temp)
    #                     time_step_temp = min(max_time_step.total_seconds()//60, time_step_temp)
    #                     time_step = timedelta(minutes=time_step_temp)
    #                 else:
    #                     time_step = min_time_step
                    
    #                 last_el = el
    #                 current_time += time_step
                    
    #         # Handle the case where we end in the middle of a pass
    #         if len(new_pass) == 1:
    #             new_pass.append(current_time)
    #             passes.append(new_pass)
        

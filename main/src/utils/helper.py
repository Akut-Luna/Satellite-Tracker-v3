import os
import re
import json
import shutil
import traceback
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from scipy.optimize import bisect
from scipy.interpolate import interp1d
from skyfield.api import load, Loader, EarthSatellite, wgs84

from utils.sub_windows.next_path_visualisation import NexPassVisualisationWindow
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

def get_target_names_from_file(self, list_path):
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
                    
                    # save df for use in find passes
                    find_passes_df = df[['time_UTC', 'el_deg']]
                    target['find_passes_df'] = find_passes_df

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
        if delta_t_min < 0: # if delta t is negative soemthing went wrong
            return True     # and we should definitly update
    else:
        delta_t_min = self.config.min_before_recalculate_ground_track
        self.last_time_ground_track_got_calculated = now_datetime

    return delta_t_min >= self.config.min_before_recalculate_ground_track

def find_passes(self, return_data=False):
    '''
    Finds the times when the satellite is rising over / setting under the horizon.

    Parameters:
        return_data (bool): if True we will not print to console and return the data. 

    Returns:
        passes (list): (N,2) dim list with AOS datetime and LOS datetime
    '''
    def find_passes_LEO(current_target, antenna_pos, start_time, end_time):
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

    def find_passes_DS(start_time, end_time):
        df = current_target['find_passes_df'].copy()

        # Convert strings to datetime and localize to UTC to match input parameters
        df['time_UTC'] = pd.to_datetime(df['time_UTC']).dt.tz_localize('UTC')
        data_start = df['time_UTC'].iloc[0]
        data_end = df['time_UTC'].iloc[-1]
        
        # Ensure start/end times are also pandas-compatible UTC datetimes
        start_dt = pd.to_datetime(start_time)
        end_dt = pd.to_datetime(end_time)

        mask = (df['time_UTC'] >= start_dt) & (df['time_UTC'] <= end_dt)
        df = df.loc[mask].reset_index(drop=True)
        
        passes = []

        # If there's no data in the requested interval, nothing to do
        if df.empty:
            self.log_message('No data in the requested time window.')
        else:
            el = df['el_deg']
            times = df['time_UTC']

            if start_dt < data_start:
                self.log_message(f'Warning: Local data starts only after {data_start.strftime('%H:%M %d.%m.%Y')} UTC.')
            if end_dt > data_end:
                self.log_message(f'Warning: Local data lasts only until {data_end.strftime('%H:%M %d.%m.%Y')} UTC.')

            # Helper to estimate crossing time between two samples by linear interpolation
            def interp_crossing(t1, e1, t2, e2, threshold):
                try:
                    if e2 == e1: # flat segment: choose middle
                        return t1 + (t2 - t1) / 2
                    frac = (threshold - e1) / (e2 - e1)
                    frac = max(0.0, min(1.0, frac))
                    return t1 + (t2 - t1) * frac
                except Exception:
                    return t2

            # -------------- find indices at which we are corssing the threshold --------------
            above = el > self.find_passes_min_angle   # True = above threshold, False = below threshold
            int_s = above.astype(int)                 # True and False -> 1 and 0
            diff = int_s.diff().fillna(0).astype(int) # calculates the difference between consecutive steps
            aos_crossing_indices = diff[diff ==  1].index  # corssing the threshold (0 -> 1)
            los_crossing_indices = diff[diff == -1].index  # corssing the threshold (1 -> 0)

            # --------------- find times at which we are corssing the threshold ---------------
            # ------------- AOS -------------
            aos_times = []
            for idx in aos_crossing_indices: # if first sample is an AOS, use the sample time
                if idx == 0:                 # else interpolate between this timestep and the previous one
                    t_cross = times.iloc[0]
                else:
                    t_cross = interp_crossing(times.iloc[idx-1], el.iloc[idx-1], times.iloc[idx], el.iloc[idx], self.find_passes_min_angle)
                aos_times.append(t_cross)

            # if already above threshold at the first data point 
            effective_start = max(data_start, start_dt)
            if above.iloc[0]: 
                if not aos_times or aos_times[0] > times.iloc[0]:
                    aos_times.insert(0, effective_start)

            # Ensure consistency as python datetime objects without nanoseconds warnings
            aos_times = [t.to_pydatetime() if hasattr(t, 'to_pydatetime') else t for t in pd.to_datetime(aos_times).floor('us')]
            
            # ------------- LOS -------------
            los_times = []
            for idx in los_crossing_indices: # if first sample is an AOS, use the sample time
                if idx == 0:                 # else interpolate between this timestep and the previous one
                    t_cross = times.iloc[0]
                else:
                    t_cross = interp_crossing(times.iloc[idx-1], el.iloc[idx-1], times.iloc[idx], el.iloc[idx], self.find_passes_min_angle)
                los_times.append(t_cross)

            # if still above threshold at the last data point
            effective_end = min(data_end, end_dt)
            if above.iloc[-1]: 
                if not los_times or los_times[-1] < times.iloc[-1]:
                    los_times.append(effective_end)

            # Ensure consistency as python datetime objects without nanoseconds warnings
            los_times = [t.to_pydatetime() if hasattr(t, 'to_pydatetime') else t for t in pd.to_datetime(los_times).floor('us')]
            
            # -------- ensure each AOS is paired with the next LOS that occurs after it -------
            i, j = 0, 0
            while i < len(aos_times) and j < len(los_times):
                if aos_times[i] <= los_times[j]:
                    passes.append([aos_times[i], los_times[j]])
                    i += 1
                    j += 1
                else: # LOS before next AOS: skip this LOS
                    j += 1

            # if there are leftover AOS without LOS (pass extends beyond data), close at last data point
            while i < len(aos_times):
                passes.append([aos_times[i], pd.to_datetime(times.iloc[-1]).to_pydatetime()])
                i += 1

        return passes

    def find_passes_ASTRO(self, current_target, start_time, end_time):
        start_dt = pd.to_datetime(start_time).to_pydatetime()
        end_dt = pd.to_datetime(end_time).to_pydatetime()
        threshold = self.find_passes_min_angle
        ra_hours = current_target['RA']
        dec_degrees = current_target['DEC']
        
        # Coarse Search (10 minutes resolution)
        duration_minutes = (end_dt - start_dt).total_seconds() / 60
        periods = max(2, int(duration_minutes // 10))
        time_grid = pd.date_range(start=start_dt, end=end_dt, periods=periods)
        elevations = np.array([self.tracking_mode_RA_DEC(t, ra_hours=ra_hours, dec_degrees=dec_degrees, calc_ground_track=False)[1] for t in time_grid])
        
        above = elevations >= threshold
        int_s = above.astype(int)
        diff = np.diff(int_s, prepend=int_s[0])
        
        # Root-finding helper for precise crossing
        def el_root_func(t_ts):
            # Ensure consistency as python datetime objects without nanoseconds warnings
            t_dt = pd.to_datetime(t_ts, unit='s', utc=True).round('us').to_pydatetime()
            return self.tracking_mode_RA_DEC(t_dt, ra_hours=ra_hours, dec_degrees=dec_degrees, calc_ground_track=False)[1] - threshold

        # --- Find AOS Times ---
        aos_times = []
        # Identify 0 -> 1 crossings
        aos_indices = np.where(diff == 1)[0]
        for idx in aos_indices:
            t_low = time_grid[idx-1].timestamp()
            t_high = time_grid[idx].timestamp()
            t_cross = bisect(el_root_func, t_low, t_high, xtol=1)
            aos_times.append(pd.to_datetime(t_cross, unit='s', utc=True))

        # Handle start-of-window edge case
        if above[0]:
            if not aos_times or aos_times[0] > start_dt:
                aos_times.insert(0, start_dt)

        # --- Find LOS Times ---
        los_times = []
        # Identify 1 -> 0 crossings
        los_indices = np.where(diff == -1)[0]
        for idx in los_indices:
            t_low = time_grid[idx-1].timestamp()
            t_high = time_grid[idx].timestamp()
            t_cross = bisect(el_root_func, t_low, t_high, xtol=0.1)
            los_times.append(pd.to_datetime(t_cross, unit='s', utc=True))

        # Handle end-of-window edge case
        if above[-1]:
            if not los_times or los_times[-1] < end_dt:
                los_times.append(end_dt)

        # Clean nanoseconds and convert to pydatetime (matches original)
        aos_times = [t.floor('us').to_pydatetime() for t in pd.to_datetime(aos_times)]
        los_times = [t.floor('us').to_pydatetime() for t in pd.to_datetime(los_times)]

        # --- Pair AOS and LOS (Matching original logic) ---
        passes = []
        i, j = 0, 0
        while i < len(aos_times) and j < len(los_times):
            if aos_times[i] <= los_times[j]:
                passes.append([aos_times[i], los_times[j]])
                i += 1
                j += 1
            else: 
                j += 1 # Skip LOS if before AOS

        # Close any leftover AOS at the very end of the requested window
        while i < len(aos_times):
            passes.append([aos_times[i], end_dt])
            i += 1

        return passes

    start_time = self.find_passes_start_time
    end_time = self.find_passes_end_time
    min_elevation = self.find_passes_min_angle

    if start_time >= end_time:
        self.log_message("'Start time' must be before 'End time'.")
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
            passes = find_passes_LEO(current_target, antenna_pos, start_time, end_time)

        elif current_target['type'] == 'DS':
            passes = find_passes_DS(start_time, end_time)

        elif current_target['type'] == 'ASTRO':
            passes = find_passes_ASTRO(self, current_target, start_time, end_time)

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

    # ---------------------------------- Print results to console ---------------------------------
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

def visualise_next_pass(self, data):
    start_time = data[0][0]
    end_time = data[0][1]
    delta_t = int((end_time - start_time).total_seconds())
    
    step_size = 1 # seconds per step
    while delta_t > 500:            # There is absolutly not need to plot more then 500 points.
        delta_t = delta_t // 10     # Therefore we can optimise the calculation by reducing the 
        step_size *= 10             # amount of calculated points
    
    data = np.zeros((delta_t,2))
    if self.tracking_mode == 0: # List
        for i in range(delta_t):
            current_time = start_time + timedelta(seconds=i*step_size)

            az, _, el, _, _, _, _, _, _, _ = self.tracking_mode_List(current_time, calc_ground_track=False)
            
            data[i,0] = az
            data[i,1] = el

    UTC = not self.local_time_radio_button_checked # flag that shows if time is in UTC or Local Time

    self.plot_window = NexPassVisualisationWindow()
    self.plot_window.plot(data, start_time, end_time, UTC)
    self.plot_window.show()

import os
import re
import json
import requests
import traceback
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from astropy import units as u
from astropy.time import Time
from astropy.constants import c as speed_of_light
from astropy.coordinates import (
    CartesianRepresentation, CartesianDifferential, GCRS, ITRS, 
    EarthLocation, AltAz, get_body_barycentric_posvel
)
from astroquery.jplhorizons import Horizons
from scipy.interpolate import interp1d

from utils.time_convertions import utc_now

def update_data_if_needed(self, current_target):
    '''
    Checks how old the current data is and updates if needed.
    
    Parameters:
        current_target (dir): data about the target from self.target_list

    '''
    t = utc_now().isoformat()
    t_30_min_later = (datetime.fromisoformat(t) + timedelta(minutes=30)).isoformat()

    # check if Horizons or CelesTrak data is used
    if current_target['type'] == 'LEO':
        last_download = self.metadata['OMM']['last download']
        time_difference = datetime.fromisoformat(t) - datetime.fromisoformat(last_download)

        need_to_update = False
        # update if data is older then 2h but not while tracking
        if time_difference.total_seconds() > 2 * 3600 and not self.tracking:
            need_to_update = True

        # update if data is older then 24h even if we are tracking
        elif time_difference.total_seconds() > 24 * 3600:
            need_to_update = True

        if need_to_update:
            self.log_message('Downloading new OMM data...')
            self.query_celestrak_api()
            self.load_target_list(OMM_only=True) # update list in memory

    elif current_target['type'] == 'DS':
        spacecraft_id = current_target['Horizons']
        need_to_update = False
        
        # if data does not exist we need to update even during tracking
        if not (str(spacecraft_id) in self.metadata['DS']):
            need_to_update = True
        else:
            metadata = self.metadata['DS'][f'{spacecraft_id}']
                       
            # if we have run out of data we need to update even during tracking
            if metadata['valid until'] < t:
                need_to_update = True

            # if we are not tracking and there is less then 30 min of data left we update
            elif not self.tracking and metadata['valid until'] < t_30_min_later:
                need_to_update = True

        if need_to_update:
            self.log_message(f'Downloading new data for Spacecraft {spacecraft_id} ...')
            self.query_horizons_api(spacecraft_id)
            self.self.load_target_list(Horizons_id=spacecraft_id) # update list in memory

    elif current_target['type'] == 'ASTRO':
        pass # for ASTRO there is no data to update

    else:
        self.log_message(f'Unknowen target type: {current_target['type']}')

def save_metadata(self):
    config_file_path = os.path.join('main', 'data', 'Metadata', 'metadata.json')
    try:
        with open(config_file_path, 'w') as file:
            json.dump(self.metadata, file, indent=4)
    except Exception as e:
        self.log_message(f'Error saving metadata file: {e}')
        print(traceback.format_exc())

def load_metadata(self):
    path = os.path.join('main', 'data', 'Metadata', 'metadata.json')
    try:
        with open(path, 'r') as file:
            return json.load(file)
    except Exception as e:
        self.log_message(f'Error reading satellite metadata file: {e}')
        print(traceback.format_exc())
        return {}

def query_celestrak_api(self):
    file_path = os.path.join('main', 'data', 'OMM', 'all_active_satellites.csv')
    url = 'https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=csv'

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        with open(file_path, 'wb') as file:
            file.write(response.content)
        self.log_message(f'Data downloaded and saved to {file_path}')
    
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            '''
            A 403 means that it has been less than 2h since the last sucessfull download.
            CelesTrak will block any further requests for the next 2h. Therefore we can 
            just update the metadata such that we stop sending requests.
            '''
            pass
        else:
            self.log_message(f'HTTP error occurred: {e}')
    
    except requests.exceptions.ConnectionError:
        self.log_message('Error downloading data from CelesTrak: No internet connection.')
        print('No internet connection.')
        return False
    
    except Exception as e:
        self.log_message(f'Error downloading data from CelesTrak: {e}')
        print(traceback.format_exc())
        return False
    
    # Update metadata
    self.metadata['OMM']['last download'] = utc_now().isoformat()
    self.save_metadata()

def query_horizons_api(self, spacecraft_id):
    '''
    Parameters:
        spacecraft_id (int): id of spacecraft of celestial body in Horizons (JPL) catalog

    We calculate the needed data two times.

    The first time we query the Horizons API for the state vector in ICRF ref frame with
    the solar system barycenter as origin. From there we calculate the rest using astropy.

    The second time we query the Horizons API directly for the AZ, EL, etc. values.

    By comparing both methods for several days of the Artemis II mission, I found that the AZ and EL values
    differ in a strange periodic pattern, with a period of one day. I assume either some mistake in the many
    conversions between the different time formats, or in the calculations from state vector to AZ/EL there is
    some mistake that depends on the time of day, aka the angle of antenna on its circle around the Earth's axis.

    The average difference is around 0.5 deg, and the average max difference is around 0.8 deg. There is however
    one outlier where the difference goes up to 5 deg.

    Overall we can consider the values from the second method to be more accurate. They agree perfectly with
    the values in the Horizons Web interface, which makes sense since both come straight from Horizons.

    There are two reasons why we don't use the second method exclusively:

    1. We want to keep the first method for the case that Horizons becomes unavailable for some reason
    and we would have to connect to a different source for state vectors.

    2. With the second method we cannot calculate the subpoint.

    Therefore we use both methods and will use the AZ, EL, etc. data from the second method and
    the subpoint data from the first.
    '''
    start_time = (utc_now()).strftime('%Y-%m-%dT%H:%M:%S')
    end_time = (utc_now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S')

    # -------------- vectors table --------------
    def fetch_data_vectors(spacecraft_id, start, stop):
        time_res = f'{self.config.time_resolution_horizons_state_vector}m'
        obj = Horizons(
            id=spacecraft_id,       # The ID of the spacecraft
            location='@0',          # Sun barycenter as origin
            epochs={                
                'start': start,     # Start time
                'stop': stop,       # End time
                'step': time_res    # Step size
            }
        )
        return obj.vectors(refplane='earth') # ICRF

    def query_vectors_data(spacecraft_id, start_time, end_time):
        current_start = start_time
        current_end = end_time
        table = None
        tried_new_start_time = False
        tried_new_end_time = False
        
        for attempt in range(3):
            try:
                table = fetch_data_vectors(spacecraft_id, current_start, current_end)
                break # Sucess!
            except Exception as e:
                Horizons.clear_cache() # if something fails try clearing the cache
                if tried_new_start_time and tried_new_end_time:
                    self.log_message('Error: No Data in the requested time frame available.')
                    break

                error_text = str(e)
                match = re.search(r'(prior to|after) A\.D\.\s+([\d\-A-Z\s:\.]+)(?=\s+TD)', error_text)
                if match:
                    condition, new_timestamp = match.group(1), match.group(2).strip()
                    if condition == 'prior to':
                        self.log_message(f'Attempt {attempt+1}/3 Error: Available data starts after requested start time. Trying again with new start time {new_timestamp}.')
                        tried_new_start_time = True
                        current_start = new_timestamp
                    else: 
                        self.log_message(f'Attempt {attempt+1}/3 Error: Available data end before requested end time. Trying again with new end time {new_timestamp}.')
                        tried_new_end_time = True
                        current_end = new_timestamp
                else:
                    self.log_message(error_text) 
                    break

        if table and len(table) > 0:
            # AU -> km | AU/d -> km/s
            for col in ['x', 'y', 'z']: table[col] = table[col].to(u.km)
            for col in ['vx', 'vy', 'vz']: table[col] = table[col].to(u.km / u.s)
            
            # we save 'datetime_jd' (TDB JD) to ensure perfect interpolation precision
            df = table[['datetime_jd', 'x', 'y', 'z', 'vx', 'vy', 'vz']].to_pandas()

            return df, current_start, current_end
        else:
            self.log_message('Error: No Data in the requested time frame available.')

    def process_vectors_data(df, antenna_lat, antenna_lon, antenna_alt_m):   
        # 1. Use the TDB JD column directly for the interpolation x-axis
        times_tdb_jd = df['datetime_jd'].values
        
        # Use cubic for smooth velocity rates, linear if the dataset is noisy
        interp_pos = interp1d(times_tdb_jd, df[['x', 'y', 'z']].values, axis=0, kind='linear', fill_value='extrapolate')
        interp_vel = interp1d(times_tdb_jd, df[['vx', 'vy', 'vz']].values, axis=0, kind='linear', fill_value='extrapolate')
        
        # 2. Time setup for Earth states
        # We must convert JDs (TDB) to an Astropy Time object to get Earth's GCRS state
        times_obs = Time(times_tdb_jd, format='jd', scale='tdb')
        
        # 3. Vectorized Earth State (at t_observation relative to @0)
        # This returns the position and velocity of Earth relative to the Solar System Barycenter
        earth_pos_bc, earth_vel_bc = get_body_barycentric_posvel('earth', times_obs)

        earth_p = earth_pos_bc.xyz.to(u.km).T  # Shape (N, 3)
        earth_v = earth_vel_bc.xyz.to(u.km/u.s).T

        # 4. Light Time Correction
        target_p_geom = df[['x', 'y', 'z']].values * u.km
        dist_approx = np.linalg.norm((target_p_geom - earth_p), axis=1)
        lt_days = (dist_approx / speed_of_light).to(u.day).value  # Shift in days for JD math

        # 5. Emission Times (t_emit = t_obs - light_time)
        t_emit_jd = times_tdb_jd - lt_days
        pos_emit = interp_pos(t_emit_jd) * u.km
        vel_emit = interp_vel(t_emit_jd) * u.km/u.s

        # 6. Relative States & Frame Transformation
        rel_p = pos_emit - earth_p
        rel_v = vel_emit - earth_v
        
        representation = CartesianRepresentation(
            x=rel_p[:, 0], 
            y=rel_p[:, 1], 
            z=rel_p[:, 2],
            differentials=CartesianDifferential(
                d_x=rel_v[:, 0], 
                d_y=rel_v[:, 1], 
                d_z=rel_v[:, 2]
            )
        )

        target_gcrs = GCRS(representation, obstime=times_obs)

        loc = EarthLocation(lat=antenna_lat*u.deg, lon=antenna_lon*u.deg, height=antenna_alt_m*u.m)
        altaz_frame = AltAz(obstime=times_obs, location=loc)
        aa = target_gcrs.transform_to(altaz_frame)
        
        # 7. Vectorized Subpoint (Ground Track)
        # Transform from GCRS (Inertial) to ITRS (Earth-Fixed)
        itrs_frame = ITRS(obstime=times_obs)
        target_itrs = target_gcrs.transform_to(itrs_frame)
        
        # earth_location returns an EarthLocation object containing arrays of lat, lon, height
        subpoint = target_itrs.earth_location

        # save to file
        return pd.DataFrame({
            'time_UTC': times_obs.utc.iso, # TDB JD -> UTC ISO String
            'az_deg': aa.az.deg,
            'el_deg': aa.alt.deg,
            'az_rate_deg_s': aa.pm_az_cosalt.to(u.deg/u.s).value,
            'el_rate_deg_s': aa.pm_alt.to(u.deg/u.s).value,
            'slant_range_km': aa.distance.km,
            'range_rate_km_s': aa.radial_velocity.to(u.km/u.s).value,
            'subpoint_lat': subpoint.lat.deg,
            'subpoint_lon': subpoint.lon.deg,
            'subpoint_alt_km': subpoint.height.to(u.km).value
        })

    self.log_message(f'Downloading vector table for spacecraft: {spacecraft_id}...') 

    # get data
    df, st, et = query_vectors_data(spacecraft_id, start_time, end_time)
    if df is None:
        return # did not manage to get data

    df = process_vectors_data(
        df, 
        self.config.antenna_latitude, 
        self.config.antenna_longitude, 
        self.config.antenna_altitude, 
    )
    
    # save data
    file_name = f'{spacecraft_id}_from_state_vectors.csv'
    file_folder = os.path.join('main', 'data', 'Horizons')
    os.makedirs(file_folder, exist_ok=True)
    file_path = os.path.join(file_folder, file_name)
    df.to_csv(file_path, index=False)
    self.log_message(f'Data saved to {file_path}') 

    # -------------- observer table -------------
    def fetch_data_observer(spacecraft_id, start, stop):
        # NOTE: lighttime correction is enabled by default for observer tables.
        time_res = f'{self.config.time_resolution_horizons_directly}m'
        
        # 4 = Apparent AZ & EL
        # 5 = Rates; AZ & EL 
        # 20 = Observer range & range-rate
        quantities = '4,5,20' 
        obj = Horizons(
            id=spacecraft_id,
            location={
                'lon': self.config.antenna_longitude, 
                'lat': self.config.antenna_latitude, 
                'elevation': self.config.antenna_altitude / 1000
            },
            epochs={                
                'start': start,     # Start time
                'stop': stop,       # End time
                'step': time_res    # Step size
            }
        )
        return obj.ephemerides(quantities=quantities, refraction=True) # antenna-centric ephemerides

    def query_observer_data(spacecraft_id, start_time, end_time):
        
        table = fetch_data_observer(spacecraft_id, start_time, end_time)
        
        if table and len(table) > 0:
            # NOTE: we don't get subpoint from observer table
            times_obs = Time(table['datetime_jd'], format='jd', scale='tdb')
            return pd.DataFrame({
                'time_UTC': times_obs.utc.iso,                      # TDB JD -> UTC 
                'az_deg': table['AZ'],                              # already in deg
                'el_deg': table['EL'],                              # already in deg
                'az_rate_deg_s': table['AZ_rate'].to(u.deg / u.s),  # arcsec/s -> deg/s
                'el_rate_deg_s': table['EL_rate'].to(u.deg / u.s),  # arcsec/s -> deg/s
                'slant_range_km': table['delta'].to(u.km),          # AU -> km
                'range_rate_km_s': table['delta_rate'],             # already in km/s
            })
        else:
            self.log_message('Error: No Data in the requested time frame available.') 

    self.log_message(f'Downloading observer table for spacecraft: {spacecraft_id}...') 

    '''
    For the vector table Horizons gives errors in TD time.
    For the observer table Horizons gives errors in U time.
    Because of the small differences between TD and U
    the time that worked for the vector table, might not work
    for the observer table. So, we will increase/decrease the 
    time by 1 min unit it works.
    If we have to change the time by 10 min, we assume something 
    went wrong and abort.
    '''
    for attempt in range(10):
        if st != start_time: # start_time got adjusted
            # %b handles the abbreviated month name (e.g., APR)
            st = datetime.strptime(st, '%Y-%b-%d %H:%M:%S.%f')
            st += timedelta(minutes=1)
            st = st.strftime('%Y-%b-%d %H:%M:%S.%f')[:-2].upper()
        
        if et != end_time: # end_time got adjusted
            # %b handles the abbreviated month name (e.g., APR)
            et = datetime.strptime(et, '%Y-%b-%d %H:%M:%S.%f')
            et -= timedelta(minutes=1)
            et = et.strftime('%Y-%b-%d %H:%M:%S.%f')[:-2].upper()

        # get data
        try:
            df = query_observer_data(spacecraft_id, st, et)
            if df is not None:
                break # Success!
        except:
            pass

    if df is None:
        if attempt == 9:
            self.log_message(f'While looking for observer data for spacecraft {spacecraft_id}, we could not find valid start and end times.')
            self.log_message(f'last attempt: st = {st} and et = {et}')
        return # did not manage to get data
    
    # save data
    file_name = f'{spacecraft_id}_from_observer_ephemerides.csv'
    file_folder = os.path.join('main', 'data', 'Horizons')
    os.makedirs(file_folder, exist_ok=True)
    file_path = os.path.join(file_folder, file_name)
    df.to_csv(file_path, index=False)
    self.log_message(f'Data saved to {file_path}') 

    # update metadata
    formats = ['%Y-%m-%dT%H:%M:%S', '%Y-%b-%d %H:%M:%S.%f']
    final_end_time = None

    for fmt in formats:
        try:
            final_end_time = datetime.strptime(et, fmt)
            break
        except ValueError:
            continue

    if not final_end_time:
        raise ValueError(f'Time data {et} does not match any recognized format')    
    
    self.metadata['DS'][f'{spacecraft_id}']['last download'] = utc_now().isoformat()
    self.metadata['DS'][f'{spacecraft_id}']['valid until'] = final_end_time.isoformat()
    self.save_metadata()

# TODO: mulitprocessing?


from astropy.coordinates import ICRS, AltAz, SkyCoord, ITRS, EarthLocation
from skyfield.api import wgs84, Star
import astropy.units as u
import traceback
from datetime import timedelta
import numpy as np
import time

from utils.time_convertions import datetime_to_astropy_time

def tracking_mode_List(self, t):
    pass

def tracking_mode_RA_DEC(self, t):
    '''
    Parameters:
        t (datetime): time of observation

    Returns:
        az (float): Azimuth in degrees 
        el (float): Elevation in degrees
        latitude (float): Subpoint latitude in degrees
        longitude (float): Subpoint longitude in degrees
        altitude (float): Altitude of satellite above the ground in km

    NOTE: IF TRACKING IS TURNED OFF, ALL ERROR MESSAGES ARE GETTING IGNORED! 
    The reason for that is that, if the user has not yet finished typing in all necessary information the program would 
    raise lots of errors. So, the idea is that we just display the data that we can calculate with the information
    that we curretly have. However as soon as tracking is turned on we have to assume that the user has entered all 
    necessary information. Now we no longer ignore error messages in order to warn the user, if the given information is
    not valid.
    '''
    
    obstime = datetime_to_astropy_time(t)
    obsloc = EarthLocation(
        lat=self.config.antenna_latitude*u.deg, 
        lon=self.config.antenna_longitude*u.deg
    )
    
    # earth fixed, non rotating ref frame
    sky_pos = SkyCoord(
        ra=self.ra_hours * u.hourangle, 
        dec=self.dec_degrees * u.deg,
        distance=(1e9 + 6378) * u.km,
        frame='gcrs', 
        obstime=obstime
    )

    # earth fixed, rotating ref frame
    itrs_pos = sky_pos.transform_to(ITRS(obstime=obstime))

    # topocentric (pov of antenna)
    topocentric_frame = AltAz(obstime=obstime, location=obsloc)
    aa = sky_pos.transform_to(topocentric_frame)
    
    az = aa.az.value
    el = aa.alt.value

    # subpoint on WGS84 ellipsoid 
    subpoint = itrs_pos.earth_location

    latitude = subpoint.lat.value    # deg
    longitude = subpoint.lon.value   # deg
    altitude = subpoint.height.value # km
    
    # flight path -----------------------------------------------------------------------------
    '''
    Note: Skyfield is less precise than astropy, but faster by a factor of 10. 
    Therefore we are using Skyfield for the calculation of the flight_path.
    '''

    if self.last_time_flight_path_got_calculated is not None:
        delta_t_min = (t - self.last_time_flight_path_got_calculated).total_seconds() // 60
    else:
        delta_t_min = self.config.min_before_recalculate_flight_path
        self.last_time_flight_path_got_calculated = t

    if delta_t_min >= self.config.min_before_recalculate_flight_path:
        try:
            # Vectorized calculation
            target_dir = Star(ra_hours=self.ra_hours, dec_degrees=self.dec_degrees)
            if self.config.flight_path_steps > 0:
                future_times = [t + timedelta(minutes=i) for i in range(self.config.flight_path_steps)]
                future_times = self.ts.from_datetimes(future_times)
                
                # Note: Since RA/Dec is fixed in GCRS, we observe from Earth center
                path_astrometric = self.planet_ephemeris['earth'].at(future_times).observe(target_dir)
                path_subpoints = wgs84.subpoint(path_astrometric)
                
                flight_path = np.column_stack((
                    path_subpoints.latitude.degrees, 
                    path_subpoints.longitude.degrees
                ))
            else:
                flight_path = np.zeros((0, 2))

            self.flight_path_changed.emit(flight_path) # -> ui
            self.last_time_flight_path_got_calculated = t

        except Exception as e:
            if self.tracking:
                self.log_message(f'Error calculating flight path: {str(e)}')
                print(traceback.format_exc())

    return az, el, latitude, longitude, altitude

def tracking_mode_OMM(self, t):
    '''
    Parameters:
        t (skyfield timescale): Skyfield time

    Returns:
        az (float): Azimuth in degrees 
        az_rate (float): Azimuth rate in degrees per second
        el (float): Elevation in degrees
        el_rate (float): Elevation rate in degrees per second
        slant_range (float): Distance from antenna to satellite in km
        range_rate (float): Range rate in km/s
        latitude (float): Subpoint latitude in degrees
        longitude (float): Subpoint longitude in degrees
        altitude (float): Altitude of satellite above the ground in km
        f1 (float): Doppler shifted frequency in MHz            

    NOTE: IF TRACKING IS TURNED OFF, (ALMOST) ALL ERROR MESSAGES ARE GETTING IGNORED! 
    The reason for that is that, if the user has not yet finished typing in all necessary information the program would 
    raise lots of errors. So, the idea is that we just display the data that we can calculate with the information
    that we curretly have. However as soon as tracking is turned on we have to assume that the user has entered all 
    necessary information. Now we no longer ignore error messages in order to warn the user, if the given information is
    not valid.
    '''

    satellite_name = self.OMM_file_satellite_name.text().upper()
    satellite_intl_id = self.OMM_file_intl_id.text()
    if self.OMM_file_norad_id.text() == '':
        satellite_norad_id = -1
    else:
        satellite_norad_id = int(self.OMM_file_norad_id.text())

    satellite = None

    if os.path.isfile(file_path) and (satellite_name != '' or satellite_intl_id != '' or satellite_norad_id != -1):
        if file_ending == 'csv': # OMM ------------------------------------------------

            # find satellite in data
            if satellite_name != '':
                row = self.omm_df[self.omm_df['OBJECT_NAME'] == satellite_name]
                if row.empty and self.tracking:
                    self.log_message(f'Could not find {satellite_name} in file {file_path}')

            elif satellite_intl_id != '':
                row = self.omm_df[self.omm_df['OBJECT_ID'] == satellite_intl_id]
                if row.empty and self.tracking:
                    self.log_message(f'Could not find {satellite_intl_id} in file {file_path}')
            
            elif satellite_norad_id != -1:
                row = self.omm_df[self.omm_df['NORAD_CAT_ID'] == satellite_norad_id]
                if row.empty and self.tracking:
                    self.log_message(f'Could not find {satellite_norad_id} in file {file_path}')

            if not row.empty: # create EarthSatellite
                fields = row.to_dict(orient='records')[0]
                satellite = EarthSatellite.from_omm(self.skyfield_ts, fields)

        elif file_ending == 'tle': # TLE ----------------------------------------------

            if satellite_name != '':
                try:                
                    satellite = self.tle_by_name[satellite_name]
                except:
                    if self.tracking:
                        self.log_message(f'Could not find {satellite_name} in file {file_path}')
            
            elif satellite_intl_id != '':
                # adjust to TLE norm for international designator
                if '-' in satellite_intl_id:
                    satellite_intl_id = satellite_intl_id[2:].replace('-', '')

                try:                
                    satellite = self.tle_by_intl[satellite_intl_id]
                except:
                    if self.tracking:
                        self.log_message(f'Could not find {satellite_intl_id} in file {file_path}')
            
            elif satellite_norad_id != -1:
                try:                
                    satellite = self.tle_by_norad[satellite_norad_id]
                except:
                    if self.tracking:
                        self.log_message(f'Could not find {satellite_norad_id} in file {file_path}')
                        
        else:
            self.log_message('Invalide file')

        if satellite is not None:
            self.OMM_file_satellite = satellite

            # relative position vector
            relative_pos = satellite - self.skyfield_antenna_pos 
            
            # relative position object
            topocentric = relative_pos.at(t)
            satellite = satellite.at(t)

            el, az, slant_range, el_rate, az_rate, range_rate = topocentric.frame_latlon_and_rates(self.skyfield_antenna_pos)

            subpoint = wgs84.subpoint_of(satellite)
            altitude = wgs84.height_of(satellite)

            # units ---------------------------------------------------------------------------
            az = az.degrees
            el = el.degrees
            slant_range = slant_range.km

            az_rate = az_rate.degrees.per_second
            el_rate = el_rate.degrees.per_second
            range_rate = range_rate.km_per_s
            
            latitude = subpoint.latitude.degrees
            longitude = subpoint.longitude.degrees
            altitude = altitude.km

            # doppler shift -------------------------------------------------------------------
            # get frequency from UI
            if self.doppler_initial_freq.text() == '':
                f0 = 0 
            else:
                f0 = float(self.doppler_initial_freq.text())
            
            try:
                f1 = self.doppler_shift(f0, range_rate)
            except Exception as e:
                if self.tracking:
                    self.log_message(f'Error calculating doppler shift: {str(e)}')
                    print(traceback.format_exc())
    
            # flight path -----------------------------------------------------------------------------
            now_datetime = self.skyfield_time_to_datetime(t)
            if self.last_time_flight_path_got_calculated is not None:
                delta_t_min = (now_datetime - self.last_time_flight_path_got_calculated).total_seconds() // 60
            else:
                delta_t_min = self.min_before_recalculate_flight_path
                self.last_time_flight_path_got_calculated = now_datetime

            if delta_t_min >= self.min_before_recalculate_flight_path:
                try:
                    flight_path = np.zeros((self.flight_path_steps,2))
                    for i in range(self.flight_path_steps):
                        t = self.datetime_to_skyfield_time(now_datetime + timedelta(minutes=i))
                        satellite = self.OMM_file_satellite.at(t)
                        subpoint = wgs84.subpoint_of(satellite)
                        flight_path[i][0] = subpoint.latitude.degrees
                        flight_path[i][1] = subpoint.longitude.degrees
                    
                    self.flight_path = flight_path
                    self.last_time_flight_path_got_calculated = now_datetime

                except Exception as e:
                    if self.tracking:
                        self.log_message(f'Error calculating flight path: {str(e)}')
                        print(traceback.format_exc())

            return az, az_rate, el, el_rate, slant_range, range_rate, latitude, longitude, altitude, f1

def tracking_mode_SPICE(self, t):
    pass

def tracking_mode_AZ_EL(self):
    '''            
    Returns:
        az (float): Azimuth in degrees 
        el (float): Elevation in degrees
    '''
    
    if self.az_input.text() == '':
        az = 0
    else:
        az = float(self.az_input.text())

    if self.el_input.text() == '':
        el = 0
    else:
        el = float(self.el_input.text())

    if az < 0 or 360 < az:
        self.log_message('Azimuth need to be between 0° and 360°')
        return
    if el < 0 or 90 < el:
        self.log_message('Elevation need to be between 0° and 90°')
        return
    
    # flight path -----------------------------------------------------------------------------
    self.flight_path_changed.emit(None) # -> ui

    return az, el
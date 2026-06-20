import os
import traceback
import numpy as np
import astropy.units as u
from datetime import timedelta
from skyfield.api import wgs84, Star, EarthSatellite
from astropy.coordinates import AltAz, SkyCoord, ITRS, EarthLocation

from utils.time_convertions import datetime_to_astropy_time, datetime_to_skyfield_time
from utils.calculations import doppler_shift

def tracking_mode_List(self, now_datetime):
    '''
    Parameters:
        now_datetime (datetime): time of observation
    
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
    '''
    current_target = self.target_list[self.target_list_idx]
    # TODO: put the following in its own function: func(current_target, now_datetime)
    # this function could then be reused in a future planer feature
    self.update_data_if_needed(current_target)                 

    if current_target['type'] == 'LEO': # ---------------------------------------------------------
        t = datetime_to_skyfield_time(self.skyfield_ts, now_datetime)
        try:
            antenna_pos = wgs84.latlon(
                self.config.antenna_latitude, 
                self.config.antenna_longitude, 
                self.config.antenna_altitude
            )

            # relative position vector
            satellite = current_target['EarthSatellite']
            list_satellite = satellite # save for use in flight path
            relative_pos = satellite - antenna_pos 
            
            # relative position object
            topocentric = relative_pos.at(t)
            satellite = satellite.at(t) # geocentric

        except Exception as e:
            self.log_message(f'Error calculating satellite position: {str(e)}')
            print(traceback.format_exc())

        el, az, slant_range, el_rate, az_rate, range_rate = topocentric.frame_latlon_and_rates(antenna_pos)

        subpoint = wgs84.subpoint_of(satellite)
        altitude = wgs84.height_of(satellite)

        # ----------------------------------------- units -----------------------------------------
        az = az.degrees
        el = el.degrees
        slant_range = slant_range.km

        az_rate = az_rate.degrees.per_second
        el_rate = el_rate.degrees.per_second
        range_rate = range_rate.km_per_s
        
        latitude = subpoint.latitude.degrees
        longitude = subpoint.longitude.degrees
        altitude = altitude.km

        # ------------------------------------- doppler shift -------------------------------------
        f0 = self.doppler_init_freq
        try:
            f1 = doppler_shift(f0, range_rate)
        except Exception as e:
            self.log_message(f'Error calculating doppler shift: {str(e)}')
            print(traceback.format_exc())

        # -------------------------------------- flight path --------------------------------------
        if self.should_flight_path_get_calculated(now_datetime):
            try:
                if self.config.flight_path_steps > 0:
                    future_times = [now_datetime + timedelta(minutes=i) for i in range(self.config.flight_path_steps)]
                    future_times = self.skyfield_ts.from_datetimes(future_times)
                    satellites = list_satellite.at(future_times)
                    subpoints = wgs84.subpoint_of(satellites)
                    flight_path = np.column_stack((
                        subpoints.latitude.degrees,
                        subpoints.longitude.degrees
                    ))
                else:
                    flight_path = np.zeros((0, 2))
                
                self.flight_path_changed.emit(flight_path) # -> ui
                self.last_time_flight_path_got_calculated = now_datetime

            except Exception as e:
                self.log_message(f'Error calculating flight path: {str(e)}')
                print(traceback.format_exc())
        return az, az_rate, el, el_rate, slant_range, range_rate, latitude, longitude, altitude, f1
    
    elif current_target['type'] == 'DS': # --------------------------------------------------------
        # ------------------------------ data from Horizons directly ------------------------------
        interpolators = current_target['interpolators_directly']
        start_time = current_target['start_time_directly']
        start_time = start_time.replace(tzinfo=now_datetime.tzinfo)
        target_x = (now_datetime - start_time).total_seconds()

        az = float(interpolators['az_deg'](target_x))
        el = float(interpolators['el_deg'](target_x))

        az_rate = float(interpolators['az_rate_deg_s'](target_x))
        el_rate = float(interpolators['el_rate_deg_s'](target_x))

        slant_range = float(interpolators['slant_range_km'](target_x))
        range_rate = float(interpolators['range_rate_km_s'](target_x))

        # --------------------------- data calculated from state vector ---------------------------
        interpolators = current_target['interpolators_from_vector'] # NOTE: start_time_form_vector 
        start_time = current_target['start_time_from_vector']       # could differ from 
        start_time = start_time.replace(tzinfo=now_datetime.tzinfo) # start_time_directly so, we 
        target_x = (now_datetime - start_time).total_seconds()      # recalculate target_x

        latitude = float(interpolators['subpoint_lat'](target_x))
        longitude = float(interpolators['subpoint_lon'](target_x))
        altitude = float(interpolators['subpoint_alt_km'](target_x))

        # ------------------------------------- doppler shift -------------------------------------
        f0 = self.doppler_init_freq
        try:
            f1 = doppler_shift(f0, range_rate)
        except Exception as e:
            self.log_message(f'Error calculating doppler shift: {str(e)}')
            print(traceback.format_exc())

        # -------------------------------------- flight path --------------------------------------
        if self.should_flight_path_get_calculated(now_datetime):
            try:
                if self.config.flight_path_steps > 0:
                    base_offset = (now_datetime - start_time).total_seconds()
                    future_x = [base_offset + (i * 60) for i in range(self.config.flight_path_steps)]
                    latitudes = [float(lat) for lat in interpolators['subpoint_lat'](future_x)]
                    longitudes = [float(lon) for lon in interpolators['subpoint_lon'](future_x)]
                    flight_path = np.column_stack((
                        latitudes,
                        longitudes
                    ))
                else:
                    flight_path = np.zeros((0, 2))
                
                self.flight_path_changed.emit(flight_path) # -> ui
                self.last_time_flight_path_got_calculated = now_datetime

            except Exception as e:
                self.log_message(f'Error calculating flight path: {str(e)}')
                print(traceback.format_exc())
        return az, az_rate, el, el_rate, slant_range, range_rate, latitude, longitude, altitude, f1

    elif current_target['type'] == 'ASTRO': # -----------------------------------------------------
        ra = current_target['RA']
        dec = current_target['DEC']
        az, el, latitude, longitude, altitude = self.tracking_mode_RA_DEC(now_datetime, ra, dec)
        return az, None, el, None, None, None, latitude, longitude, altitude, None

    else: # ---------------------------------------------------------------------------------------
        self.log_message(f'Unknowen target type: {current_target['type']}')
    
    return None, None, None, None, None, None, None, None, None, None

def tracking_mode_RA_DEC(self, now_datetime, ra_hours=None, dec_degrees=None):
    '''
    Parameters:
        now_datetime (datetime): time of observation
        ra_hours (float): RA if called by tracking_mode_list()
        dec_degrees (float): DEC if called by tracking_mode_list()

    Returns:
        az (float): Azimuth in degrees 
        el (float): Elevation in degrees
        latitude (float): Subpoint latitude in degrees
        longitude (float): Subpoint longitude in degrees
        altitude (float): Altitude of satellite above the ground in km
    '''
    
    obstime = datetime_to_astropy_time(now_datetime)
    obsloc = EarthLocation(
        lat=self.config.antenna_latitude*u.deg, 
        lon=self.config.antenna_longitude*u.deg
    )

    if dec_degrees is None:             # if the arguments are None
        dec_degrees = self.dec_degrees  # we are using the data from the ui
    if ra_hours is None:                # if the are not None
        ra_hours = self.ra_hours        # we are using the data from the list

    # earth fixed, non rotating ref frame
    sky_pos = SkyCoord(
        ra=ra_hours * u.hourangle, 
        dec=dec_degrees * u.deg,
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
    
    # ---------------------------------------- flight path ----------------------------------------
    '''
    Note: Skyfield is less precise than astropy, but faster by a factor of 10. 
    Therefore we are using Skyfield for the calculation of the flight_path.
    '''
    if self.should_flight_path_get_calculated(now_datetime):
        try:
            # Vectorized calculation
            target_dir = Star(ra_hours=ra_hours, dec_degrees=dec_degrees)
            if self.config.flight_path_steps > 0:
                future_times = [now_datetime + timedelta(minutes=i) for i in range(self.config.flight_path_steps)]
                future_times = self.skyfield_ts.from_datetimes(future_times)
                
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
            self.last_time_flight_path_got_calculated = now_datetime

        except Exception as e:
            self.log_message(f'Error calculating flight path: {str(e)}')
            print(traceback.format_exc())
    return az, el, latitude, longitude, altitude

def tracking_mode_OMM(self, now_datetime):
    '''
    Parameters:
        now_datetime (datetime): time of observation

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
    '''

    satellite = None
    sat_id = self.OMM_satellite_id
    sat_name = self.OMM_satellite_name

    if self.OMM_df is not None and (sat_name != '' or sat_id != -1):
        # find satellite in data
        '''
        NOTE: while tracking is turned off, we will not inform the user
        about an error! If the user has not yet finished typing in all 
        necessary information, the get spamed with error messages. 
        If tracking is turned on we can assume that the user has finished
        entering all necessary information and needs to be informed if
        something is wrong.
        '''
        if sat_name != '':
            row = self.OMM_df[self.OMM_df['OBJECT_NAME'] == sat_name]
            if row.empty and self.tracking:
                raise ValueError(f'Could not find ID {sat_id} in data.')

        elif sat_id != -1:
            row = self.OMM_df[self.OMM_df['NORAD_CAT_ID'] == sat_id]
            if row.empty and self.tracking:
                raise ValueError(f'Could not find ID {sat_id} in data.')

        # create EarthSatellite
        try:
            fields = row.to_dict(orient='records')[0]
            satellite = EarthSatellite.from_omm(self.skyfield_ts, fields)
        except Exception as e:
            if self.tracking:
                raise ValueError(f'Could not create EarthSatellite: {str(e)}')

        if satellite is not None:
            '''
            Skyfield is optimized for this case, so we are using Skyfield instead of astropy here.
            '''
            t = datetime_to_skyfield_time(self.skyfield_ts, now_datetime)
            self.OMM_satellite = satellite
            antenna_pos = wgs84.latlon(
                self.config.antenna_latitude, 
                self.config.antenna_longitude, 
                self.config.antenna_altitude
            )

            # relative position vector
            relative_pos = satellite - antenna_pos 
            
            # relative position object
            topocentric = relative_pos.at(t)
            satellite = satellite.at(t)

            el, az, slant_range, el_rate, az_rate, range_rate = topocentric.frame_latlon_and_rates(antenna_pos)

            subpoint = wgs84.subpoint_of(satellite)
            altitude = wgs84.height_of(satellite)

            # --------------------------------------- units ---------------------------------------
            az = az.degrees
            el = el.degrees
            slant_range = slant_range.km

            az_rate = az_rate.degrees.per_second
            el_rate = el_rate.degrees.per_second
            range_rate = range_rate.km_per_s
            
            latitude = subpoint.latitude.degrees
            longitude = subpoint.longitude.degrees
            altitude = altitude.km

            # ----------------------------------- doppler shift -----------------------------------
            f0 = self.doppler_init_freq
            try:
                f1 = doppler_shift(f0, range_rate)
            except Exception as e:
                self.log_message(f'Error calculating doppler shift: {str(e)}')
                print(traceback.format_exc())

            # ------------------------------------ flight path ------------------------------------
            if self.should_flight_path_get_calculated(now_datetime):
                try:
                    if self.config.flight_path_steps > 0:
                        future_times = [now_datetime + timedelta(minutes=i) for i in range(self.config.flight_path_steps)]
                        future_times = self.skyfield_ts.from_datetimes(future_times)
                        satellites = self.OMM_satellite.at(future_times)
                        subpoints = wgs84.subpoint_of(satellites)
                        flight_path = np.column_stack((
                            subpoints.latitude.degrees,
                            subpoints.longitude.degrees
                        ))
                    else:
                        flight_path = np.zeros((0, 2))
                    
                    self.flight_path_changed.emit(flight_path) # -> ui
                    self.last_time_flight_path_got_calculated = now_datetime

                except Exception as e:
                    self.log_message(f'Error calculating flight path: {str(e)}')
                    print(traceback.format_exc())
            return az, az_rate, el, el_rate, slant_range, range_rate, latitude, longitude, altitude, f1
    return None, None, None, None, None, None, None, None, None, None

def tracking_mode_SPICE(self, now_datetime):
    return None, None, None, None, None, None, None, None, None, None

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
        self.log_message('Azimuth needs to be between 0° and 360°')
        return None, None
    if el < 0 or 90 < el:
        self.log_message('Elevation needs to be between 0° and 90°')
        return None, None
    
    # ---------------------------------------- flight path ----------------------------------------
    self.flight_path_changed.emit(np.zeros((0, 2))) # -> ui

    return az, el

def tracking_mode_Schedule(self, now_datetime):
    return None, None, None, None, None, None, None, None, None, None

# TODO LIST:
# rename flight path -> ground track
# tracking mode Spice
# find passes
# tracking mode schedule


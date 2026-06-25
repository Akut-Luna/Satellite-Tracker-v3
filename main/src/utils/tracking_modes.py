import spiceypy
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
    return self.tracking_mode_List_core(now_datetime, current_target)

def tracking_mode_List_core(self, now_datetime, current_target):
    '''
    This function gets used by both tracking mode List and Schedule.

    Parameters:
        now_datetime (datetime): time of observation
        current_target (dict): current target dict
    
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
            list_satellite = satellite # save for use in ground track
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
        f0 = self.doppler_emited_freq
        try:
            f1 = doppler_shift(f0, range_rate)
        except Exception as e:
            self.log_message(f'Error calculating doppler shift: {str(e)}')
            print(traceback.format_exc())

        # -------------------------------------- ground track --------------------------------------
        if self.should_ground_track_get_calculated(now_datetime):
            try:
                if self.config.ground_track_steps > 0:
                    future_times = [now_datetime + timedelta(minutes=i) for i in range(self.config.ground_track_steps)]
                    future_times = self.skyfield_ts.from_datetimes(future_times)
                    satellites = list_satellite.at(future_times)
                    subpoints = wgs84.subpoint_of(satellites)
                    ground_track = np.column_stack((
                        subpoints.latitude.degrees,
                        subpoints.longitude.degrees
                    ))
                else:
                    ground_track = np.zeros((0, 2))
                
                self.ground_track_changed.emit(ground_track) # -> ui
                self.last_time_ground_track_got_calculated = now_datetime

            except Exception as e:
                self.log_message(f'Error calculating ground track: {str(e)}')
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
        f0 = self.doppler_emited_freq
        try:
            f1 = doppler_shift(f0, range_rate)
        except Exception as e:
            self.log_message(f'Error calculating doppler shift: {str(e)}')
            print(traceback.format_exc())

        # -------------------------------------- ground track --------------------------------------
        if self.should_ground_track_get_calculated(now_datetime):
            try:
                if self.config.ground_track_steps > 0:
                    base_offset = (now_datetime - start_time).total_seconds()
                    future_x = [base_offset + (i * 60) for i in range(self.config.ground_track_steps)]
                    latitudes = [float(lat) for lat in interpolators['subpoint_lat'](future_x)]
                    longitudes = [float(lon) for lon in interpolators['subpoint_lon'](future_x)]
                    ground_track = np.column_stack((
                        latitudes,
                        longitudes
                    ))
                else:
                    ground_track = np.zeros((0, 2))
                
                self.ground_track_changed.emit(ground_track) # -> ui
                self.last_time_ground_track_got_calculated = now_datetime

            except Exception as e:
                self.log_message(f'Error calculating ground track: {str(e)}')
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

def tracking_mode_RA_DEC(self, now_datetime, ra_hours=None, dec_degrees=None, calc_ground_track=True):
    '''
    Parameters:
        now_datetime (datetime): time of observation
        ra_hours (float): RA if called by tracking_mode_list_core()
        dec_degrees (float): DEC if called by tracking_mode_list_core()
        calc_ground_track (bool): if called by the find passes feature, ground track should not be calculated

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
    
    if not calc_ground_track:
        return az, el, latitude, longitude, altitude
    # ---------------------------------------- ground track ----------------------------------------
    '''
    Note: Skyfield is less precise than astropy, but faster by a factor of 10. 
    Therefore we are using Skyfield for the calculation of the ground_track.
    '''
    if self.should_ground_track_get_calculated(now_datetime):
        try:
            # Vectorized calculation
            target_dir = Star(ra_hours=ra_hours, dec_degrees=dec_degrees)
            if self.config.ground_track_steps > 0:
                future_times = [now_datetime + timedelta(minutes=i) for i in range(self.config.ground_track_steps)]
                future_times = self.skyfield_ts.from_datetimes(future_times)
                
                # Note: Since RA/Dec is fixed in GCRS, we observe from Earth center
                path_astrometric = self.planet_ephemeris['earth'].at(future_times).observe(target_dir)
                path_subpoints = wgs84.subpoint(path_astrometric)
                
                ground_track = np.column_stack((
                    path_subpoints.latitude.degrees, 
                    path_subpoints.longitude.degrees
                ))
            else:
                ground_track = np.zeros((0, 2))

            self.ground_track_changed.emit(ground_track) # -> ui
            self.last_time_ground_track_got_calculated = now_datetime

        except Exception as e:
            self.log_message(f'Error calculating ground track: {str(e)}')
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
            f0 = self.doppler_emited_freq
            try:
                f1 = doppler_shift(f0, range_rate)
            except Exception as e:
                self.log_message(f'Error calculating doppler shift: {str(e)}')
                print(traceback.format_exc())

            # ------------------------------------ ground track ------------------------------------
            if self.should_ground_track_get_calculated(now_datetime):
                try:
                    if self.config.ground_track_steps > 0:
                        future_times = [now_datetime + timedelta(minutes=i) for i in range(self.config.ground_track_steps)]
                        future_times = self.skyfield_ts.from_datetimes(future_times)
                        satellites = self.OMM_satellite.at(future_times)
                        subpoints = wgs84.subpoint_of(satellites)
                        ground_track = np.column_stack((
                            subpoints.latitude.degrees,
                            subpoints.longitude.degrees
                        ))
                    else:
                        ground_track = np.zeros((0, 2))
                    
                    self.ground_track_changed.emit(ground_track) # -> ui
                    self.last_time_ground_track_got_calculated = now_datetime

                except Exception as e:
                    self.log_message(f'Error calculating ground track: {str(e)}')
                    print(traceback.format_exc())
            return az, az_rate, el, el_rate, slant_range, range_rate, latitude, longitude, altitude, f1
    return None, None, None, None, None, None, None, None, None, None

def tracking_mode_SPICE(self, now_datetime):
    '''
    Parameters:
        now_datetime (datetime): observation time in UTC

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
    if not self.spice_kernels_loaded:
        return None, None, None, None, None, None, None, None, None, None

    et = spiceypy.datetime2et(now_datetime)
    target_name = self.spice_target_name
    lat = np.radians(self.config.antenna_latitude)
    lon = np.radians(self.config.antenna_longitude)
    alt = self.config.antenna_altitude/1000

    try:
        # -------------------------------- convert lat, lon to xyz --------------------------------
        obspos = spiceypy.georec(lon, lat, alt, 6378.1366, 1.0/298.25642)

        # Get the xyz coordinates of the spacecraft relative to observer in MYTOPO frame (Corrected for one-way light time and stellar aberration)
        state, _ = spiceypy.spkcpo(target_name, et, 'MYTOPO', 'OBSERVER', 'LT+S', obspos, 'EARTH', 'ITRF93')
    
    except Exception as e:
        '''
        NOTE: As long as the user has not entered the correct target name, spiceypy.spkcpo will fail. So, we ignore the exception and return.
        However if we are tracking and it still fails, we need to inform the user. 
        '''
        if self.tracking:
            self.log_message(f'Spiceypy error: {e}')
            if 'PCK file does not have coverage' in e:
                self.log_message(f'                                                                   ')
                self.log_message(f' Check that the Kernels are up to date.                            ')
                self.log_message(f' Especially pck/earth_latest_high_prec.bpc needs frequent updates. ')
                self.log_message(f' https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/           ')
                self.log_message(f'                                                                   ')
            print(traceback.format_exc())
        return None, None, None, None, None, None, None, None, None, None
        
    try:
        # --------------------------------------- Range rate --------------------------------------
        position = np.array(state[:3])  # X, Y, Z
        velocity = np.array(state[3:])  # Vx, Vy, Vz

        # Compute unit line-of-sight vector
        los_unit = position / np.linalg.norm(position)

        # Compute range rate (scalar projection of velocity onto line of sight)
        range_rate = np.dot(velocity, los_unit) # km/s

        # ------------------------------- Range, Azimuth, Elevation -------------------------------
        slant_range, az, el = spiceypy.recazl(position, azccw=False, elplsz=True)
        az = np.degrees(az)
        el = np.degrees(el)

        # ------------------------------ Azimuth and Elevation rates ------------------------------
        
        delta_t = 1 # s
        et_future = spiceypy.datetime2et(now_datetime + timedelta(seconds=delta_t))

        # Get state at future time
        state_future, _ = spiceypy.spkcpo(target_name, et_future, 'MYTOPO', 'OBSERVER', 'LT+S', obspos, 'EARTH', 'ITRF93')
        position_future = np.array(state_future[:3])

        # Compute future az, el
        _, az_future, el_future = spiceypy.recazl(position_future, azccw=False, elplsz=True)
        az_future = np.degrees(az_future)
        el_future = np.degrees(el_future)

        # Compute rates
        az_rate = (az_future - az) / delta_t  # deg/s
        el_rate = (el_future - el) / delta_t  # deg/s

        # ----------------------------------- Subpoint, Altitude ----------------------------------
        rot_matrix = spiceypy.pxform('MYTOPO', 'ITRF93', et)

        # Transform the target position from MYTOPO to ITRF93
        target_pos_itrf = rot_matrix @ position

        # Now we use the target position in ITRF93 to compute the subpoint
        # Convert rectangular coordinates to geodetic (latitude, longitude, altitude)
        longitude, latitude, altitude = spiceypy.recgeo(target_pos_itrf, 6378.1366, 1.0/298.25642)
        latitude = np.degrees(latitude)
        longitude = np.degrees(longitude)

    except Exception as e:
        if self.tracking:
            self.log_message(f'Error calculating position with spiceypy: {e}')
            print(traceback.format_exc())
    
    # --------------------------------------- Doppler Shift ---------------------------------------
    f0 = self.doppler_emited_freq
    try:
        f1 = doppler_shift(f0, range_rate)
    except Exception as e:
        self.log_message(f'Error calculating doppler shift: {str(e)}')
        print(traceback.format_exc())

    # --------------------------------------- ground track ----------------------------------------
    if self.should_ground_track_get_calculated(now_datetime):
        try:
            ground_track = np.zeros((self.config.ground_track_steps,2))
            for i in range(self.config.ground_track_steps):
                et = spiceypy.datetime2et(now_datetime + timedelta(minutes=i))
                state, _ = spiceypy.spkcpo(target_name, et, 'MYTOPO', 'OBSERVER', 'LT+S', obspos, 'EARTH', 'ITRF93')
                position = np.array(state[:3])  # X, Y, Z
                rot_matrix = spiceypy.pxform('MYTOPO', 'ITRF93', et)
                target_pos_itrf = rot_matrix @ position
                long, lat, altitude = spiceypy.recgeo(target_pos_itrf, 6378.1366, 1.0/298.25642)

                ground_track[i][0] = np.degrees(lat)
                ground_track[i][1] = np.degrees(long)
            
            self.ground_track_changed.emit(ground_track) # -> ui
            self.last_time_ground_track_got_calculated = now_datetime

        except Exception as e:
            if self.tracking:
                self.log_message(f'Error calculating ground track: {str(e)}')
                print(traceback.format_exc())

    return az, az_rate, el, el_rate, slant_range, range_rate, latitude, longitude, altitude, f1

def tracking_mode_AZ_EL(self):
    '''            
    Returns:
        az (float): Azimuth in degrees 
        el (float): Elevation in degrees
    '''
    # ---------------------------------------- ground track ----------------------------------------
    self.ground_track_changed.emit(np.zeros((0, 2))) # -> ui

    return self.az_deg, self.el_deg

def tracking_mode_Schedule(self, now_datetime):
    return None, None, None, None, None, None, None, None, None, None

# TODO LIST:
# find passes
# tracking mode schedule
#  schedule input
#  add to schedule btn
# next to tracking 
#  Status: Antenna connected (green) / not connected (red)
#  next scheduled target: NAME from DATE to DATE
#  if target scheduled and not in schedul mode -> info text  
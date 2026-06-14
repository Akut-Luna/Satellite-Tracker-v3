from astropy.coordinates import ICRS, AltAz, SkyCoord, ITRS, EarthLocation
from skyfield.api import wgs84, Star, EarthSatellite
import astropy.units as u
import traceback
from datetime import timedelta
import numpy as np
import time
import os

from utils.time_convertions import datetime_to_astropy_time, datetime_to_skyfield_time
from utils.calculations import doppler_shift

def tracking_mode_List(self, t):
    '''
    Parameters:
        t (datetime): time of observation
    
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
    
    NOTE: IF TRACKING IS TURNED OFF, ALL ERROR MESSAGES ARE GETTING IGNORED! 
    The reason for that is that, if the user has not yet finished typing in all necessary information the program would 
    raise lots of errors. So, the idea is that we just display the data that we can calculate with the information
    that we curretly have. However as soon as tracking is turned on we have to assume that the user has entered all 
    necessary information. Now we no longer ignore error messages in order to warn the user, if the given information is
    not valid.
    '''
    current_target = self.target_list[self.target_list_idx]
    self.update_data_if_needed(current_target)                 

    # get skyfield satellite object and topocentric position object
    if current_target['type'] == 'LEO':
        now_datetime = t
        t = datetime_to_skyfield_time(self.skyfield_ts, t)
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
            if self.tracking:
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
        # print(f0)
        try:
            f1 = doppler_shift(f0, range_rate)
        except Exception as e:
            if self.tracking:
                self.log_message(f'Error calculating doppler shift: {str(e)}')
                print(traceback.format_exc())

        # -------------------------------------- flight path --------------------------------------
        if self.last_time_flight_path_got_calculated is not None:
            delta_t_min = (now_datetime - self.last_time_flight_path_got_calculated).total_seconds() // 60
        else:
            delta_t_min = self.config.min_before_recalculate_flight_path
            self.last_time_flight_path_got_calculated = now_datetime

        if delta_t_min >= self.config.min_before_recalculate_flight_path:
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
                if self.tracking:
                    self.log_message(f'Error calculating flight path: {str(e)}')
                    print(traceback.format_exc())
        return az, az_rate, el, el_rate, slant_range, range_rate, latitude, longitude, altitude, f1
    
    elif current_target['type'] == 'DS':
        pass # TODO

    elif current_target['type'] == 'ASTRO':
        ra = current_target['RA']
        dec = current_target['DEC']
        az, el, latitude, longitude, altitude = self.tracking_mode_RA_DEC(t, ra, dec)
        return az, None, el, None, None, None, latitude, longitude, altitude, None

    else: 
        self.log_message(f'Unknowen target type: {current_target['type']}')
    return None, None, None, None, None, None, None, None, None, None



        # # Horizons directly -----------------------------------------------------------------------
        # # During the Artemis II mission a mismatch between the calculations for AZ/EL of this program based on Horizons 
        # # data, and the AZ/EL data from Horizons itself was noticed. So an option the use the AZ/EL data from Horizons
        # # direcly was added.
        # if self.display_horizons_directly_option and self.horizons_directly_btn.isChecked():            
        #     df_direct = current_satellite['df_direct']
        #     datetime_t = self.skyfield_time_to_datetime(t)

        #     # Convert time data in df to timezone-aware datetime object if needed
        #     if isinstance(df_direct['Calendar Date (UTC)'].iloc[0], str):
        #         df_direct['Calendar Date (UTC)'] = pd.to_datetime(df_direct['Calendar Date (UTC)']).dt.tz_localize('UTC')

        #     # find two data points closest in time
        #     closest_rows = df_direct.iloc[(df_direct['Calendar Date (UTC)'] - datetime_t).abs().argsort()[:2]]
            
        #     # linear interpolation between the two data points ------------------------------------
        #     t1, t2 = closest_rows['Calendar Date (UTC)']
            
        #     az_1, az_2 = closest_rows['Az']
        #     el_1, el_2 = closest_rows['El']

        #     delta_1,  delta_2  = closest_rows['Delta']
        #     deldot_1, deldot_2 = closest_rows['Deldot']

        #     t1 = pd.to_datetime(t1)
        #     t2 = pd.to_datetime(t2)

        #     factor = (datetime_t - t1) / (t2 - t1)

        #     az_now = az_1 + factor * (az_2 - az_1) # deg
        #     el_now = el_1 + factor * (el_2 - el_1) # deg

        #     delta_now = delta_1 + factor * (delta_2 - delta_1) # AU
        #     deldot_now = deldot_1 + factor * (deldot_2 - deldot_1) # km/s
        #     # -------------------------------------------------------------------------------------
        
        #     # over wite with direct values
        #     az = az_now 
        #     el = el_now 
        #     slant_range = delta_now * 149597870.7 # km
        #     range_rate = deldot_now
        # # -----------------------------------------------------------------------------------------

        # # light travel time -----------------------------------------------------------------------
        # # Since the Horizon data is already ligth corrected, my light correction is not needed.
        # # I'm still leaving this feature in because it might be usefull in the future with data
        # # from a different source. In the config file you can set DISPLAY_LIGHT_TIME_CORRECTION_OPTION 
        # # to True in order to display a button, that allows the activation of this feature. 
        # if self.display_light_time_correction_option and self.light_time_correction_btn.isChecked():
        #     c = 299792458 # m/s                       # if the travel time of the signal gets large
        #     light_travel_time = slant_range.m/c # s   # we need to take that into account                   
        #     t -= timedelta(seconds=light_travel_time) # and redo the calculations with an earlier time
        #     satellite, topocentric = self.calculate_satellite_and_topocentric(current_satellite, t)
        #     el, az, slant_range, el_rate, az_rate, range_rate = topocentric.frame_latlon_and_rates(self.skyfield_antenna_pos)
        # # -----------------------------------------------------------------------------------------

        # subpoint = wgs84.subpoint_of(satellite)
        # altitude = wgs84.height_of(satellite)
        
        # # units -----------------------------------------------------------------------------------
        # if not (self.display_horizons_directly_option and self.horizons_directly_btn.isChecked()):
        #     # if Horizons directly is used they are already floats
        #     az = az.degrees
        #     el = el.degrees
        #     slant_range = slant_range.km
        #     range_rate = range_rate.km_per_s

        # az_rate = az_rate.degrees.per_second
        # el_rate = el_rate.degrees.per_second
        
        # latitude = subpoint.latitude.degrees
        # longitude = subpoint.longitude.degrees
        # altitude = altitude.km

        # # doppler shift ---------------------------------------------------------------------------
        # # get frequency from config file
        # f0 = current_satellite['frequency']
        
        # # show initial frequency on UI
        # self.doppler_initial_freq.setText(f'{f0:.6f}')

        # try:
        #     f1 = self.doppler_shift(f0, range_rate)
        # except Exception as e:
        #     if self.tracking:
        #         self.log_message(f'Error calculating doppler shift: {str(e)}')
        #         print(traceback.format_exc())

        # # flight path -----------------------------------------------------------------------------
        # now_datetime = self.skyfield_time_to_datetime(t)
        # if self.last_time_flight_path_got_calculated is not None:
        #     delta_t_min = (now_datetime - self.last_time_flight_path_got_calculated).total_seconds() // 60
        # else:
        #     delta_t_min = self.min_before_recalculate_flight_path
        #     self.last_time_flight_path_got_calculated = now_datetime

        # if delta_t_min >= self.min_before_recalculate_flight_path:
        #     try:
        #         flight_path = np.zeros((self.flight_path_steps,2))
        #         for i in range(self.flight_path_steps):
        #             t = self.datetime_to_skyfield_time(now_datetime + timedelta(minutes=i))
        #             satellite, _ = self.calculate_satellite_and_topocentric(current_satellite, t)
        #             subpoint = wgs84.subpoint_of(satellite)
        #             flight_path[i][0] = subpoint.latitude.degrees
        #             flight_path[i][1] = subpoint.longitude.degrees
                
        #         self.flight_path = flight_path
        #         self.last_time_flight_path_got_calculated = now_datetime

        #     except Exception as e:
        #         if self.tracking:
        #             self.log_message(f'Error calculating flight path: {str(e)}')
        #             print(traceback.format_exc())

        # return az, az_rate, el, el_rate, slant_range, range_rate, latitude, longitude, altitude, f1

def tracking_mode_RA_DEC(self, t, ra_hours=None, dec_degrees=None):
    '''
    Parameters:
        t (datetime): time of observation
        ra_hours (float): RA if called by tracking_mode_list()
        dec_degrees (float): DEC if called by tracking_mode_list()

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
    if self.last_time_flight_path_got_calculated is not None:
        delta_t_min = (t - self.last_time_flight_path_got_calculated).total_seconds() // 60
    else:
        delta_t_min = self.config.min_before_recalculate_flight_path
        self.last_time_flight_path_got_calculated = t

    if delta_t_min >= self.config.min_before_recalculate_flight_path:
        try:
            # Vectorized calculation
            target_dir = Star(ra_hours=ra_hours, dec_degrees=dec_degrees)
            if self.config.flight_path_steps > 0:
                future_times = [t + timedelta(minutes=i) for i in range(self.config.flight_path_steps)]
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
            self.last_time_flight_path_got_calculated = t

        except Exception as e:
            if self.tracking:
                self.log_message(f'Error calculating flight path: {str(e)}')
                print(traceback.format_exc())
    return az, el, latitude, longitude, altitude

def tracking_mode_OMM(self, t):
    '''
    Parameters:
        t (datetime): time of observation

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

    satellite = None
    sat_id = self.OMM_satellite_id
    sat_name = self.OMM_satellite_name

    if self.OMM_df is not None and (sat_name != '' or sat_id != -1):
        # find satellite in data
        if sat_name != '':
            row = self.OMM_df[self.OMM_df['OBJECT_NAME'] == sat_name]
            if row.empty and self.tracking:
                self.log_message(f'Could not find {sat_name} in file data.')

        elif sat_id != -1:
            row = self.OMM_df[self.OMM_df['NORAD_CAT_ID'] == sat_id]
            if row.empty and self.tracking:
                self.log_message(f'Could not find {sat_id} in data.')

        if not row.empty: # create EarthSatellite
            fields = row.to_dict(orient='records')[0]
            satellite = EarthSatellite.from_omm(self.skyfield_ts, fields)
        else:
            self.log_message('Invalide file')

        if satellite is not None:
            '''
            Skyfield is optimized for this case, so we are using Skyfield instead of astropy here.
            '''
            now_datetime = t
            t = datetime_to_skyfield_time(self.skyfield_ts, t)
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
                if self.tracking:
                    self.log_message(f'Error calculating doppler shift: {str(e)}')
                    print(traceback.format_exc())
    
            # ------------------------------------ flight path ------------------------------------
            if self.last_time_flight_path_got_calculated is not None:
                delta_t_min = (now_datetime - self.last_time_flight_path_got_calculated).total_seconds() // 60
            else:
                delta_t_min = self.config.min_before_recalculate_flight_path
                self.last_time_flight_path_got_calculated = now_datetime

            if delta_t_min >= self.config.min_before_recalculate_flight_path:
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
                    if self.tracking:
                        self.log_message(f'Error calculating flight path: {str(e)}')
                        print(traceback.format_exc())
            return az, az_rate, el, el_rate, slant_range, range_rate, latitude, longitude, altitude, f1
    return None, None, None, None, None, None, None, None, None, None

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
    self.flight_path_changed.emit(np.zeros((0, 2))) # -> ui

    return az, el
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
        distance=1e9 * u.km,
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
    pass

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
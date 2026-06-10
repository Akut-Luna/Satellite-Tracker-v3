from astropy.coordinates import ICRS, AltAz, SkyCoord, ITRS, EarthLocation
import astropy.units as u
import traceback

from utils.time_convertions import datetime_to_astropy_time

def tracking_mode_List(self, t):
    pass

def tracking_mode_RA_DEC(self, t):
    '''
    Parameters:
        t (datetime): datetime

    Returns:
        az (float): Azimuth in degrees 
        el (float): Elevation in degrees
        latitude (float): Subpoint latitude in degrees
        longitude (float): Subpoint longitude in degrees

    NOTE: IF TRACKING IS TURNED OFF, ALL ERROR MESSAGES ARE GETTING IGNORED! 
    The reason for that is that, if the user has not yet finished typing in all necessary information the program would 
    raise lots of errors. So, the idea is that we just display the data that we can calculate with the information
    that we curretly have. However as soon as tracking is turned on we have to assume that the user has entered all 
    necessary information. No we no longer ignore error messages in order to warn the user, if the given information is
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
    
    az = aa.az.value      # aa.az.to(u.deg).value
    el = aa.alt.value

    # subpoint on WGS84 ellipsoid 
    subpoint = itrs_pos.earth_location

    latitude = subpoint.lat.value
    longitude = subpoint.lon.value
    
    # flight path -----------------------------------------------------------------------------
    self.flight_path = None # TODO clear flight path

    return az, el, latitude, longitude

def tracking_mode_OMM(self, t):
    pass

def tracking_mode_SPICE(self, t):
    pass

def tracking_mode_AZ_EL(self):
    pass

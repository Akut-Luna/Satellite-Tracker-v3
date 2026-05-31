import os
from zoneinfo import ZoneInfo
from datetime import datetime, timezone

LOCAL_TZ = os.getenv('LOCAL_TZ') # local time zone

def local_time_to_UTC(datetime):
    '''
    Parameters:
        datetime (datetime): local time

    Returns:
        datetime (datetime): UTC
    '''
    return datetime.replace(tzinfo=ZoneInfo(LOCAL_TZ)).astimezone(ZoneInfo('UTC'))

def UTC_to_local_time(datetime):
    '''
    Parameters:
        datetime (datetime): UTC

    Returns:
        datetime (datetime): local time
    '''

    return datetime.replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo(LOCAL_TZ))

def skyfield_time_to_datetime(skyfield_time):
    '''
    Prameters:
        skyfield_time (skyfield timescale): skyfield time
    
    Returns:
        datetime (datetime): datetime
    '''
    return datetime.fromisoformat(skyfield_time.utc_iso())

def datetime_to_skyfield_time(skyfield_ts, datetime):
    '''
    Parameters:
        skyfield_ts (skyfield timescale): skyfield timescale
        datetime (datetime): datetime
    
    Returns:
        skyfield_ts (skyfield timescale): skyfield time
    '''
    return skyfield_ts.from_datetime(datetime)

def convert_tdb_to_utc(jd_tdb, delta_t):
    '''
    Converts TBD Julian Date to UTC

    Parameters:
        jd_tdb (float): Julian Date in Barycentric Dynamical Time (the JPL's T_eph)
        delta_t (float): difference between TBD and UT
    
    Returns:
        jd_utc (float): Julian Date in UTC
    
    NOTE: getting correct DUT1 is not implemented yet, but since DUT1 < 0.9s per definition it can be neglected.
    '''
    jd_ut = jd_tdb - (delta_t / 86400)  # Convert delta-T from seconds to Julian days
    # getting correct DUT1 not implemented yet ------------------------------------------------
    # mjd_ut = int(jd_ut - 2400000.5)     # Convert to Modified Julian Date (MJD)
    # dut1 = self.get_dut1(mjd_ut)        # Get DUT1 from EOP data
    dut1 = 0
    # -----------------------------------------------------------------------------------------
    jd_utc = jd_ut - (dut1 / 86400)     # Apply DUT1 correction
    return jd_utc

def utc_now():
    '''
    Returns:
        datetime (datetime): Current date and time in UTC
    '''
    return datetime.now(timezone.utc)
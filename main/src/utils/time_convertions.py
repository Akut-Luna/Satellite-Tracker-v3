import os
from zoneinfo import ZoneInfo
from astropy.time import Time
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv(os.path.join('main', 'config', 'config_antenna.env'))
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

def utc_now():
    '''
    Returns:
        datetime (datetime): Current date and time in UTC
    '''
    return datetime.now(timezone.utc)

def datetime_to_astropy_time(datetime):
    '''
    Parameters:
        datetime (datetime): must be in UTC
    Returns:
        astropy time (Time): time in astropy format (UTC)
    '''
    return Time(datetime, format='datetime', scale='utc')

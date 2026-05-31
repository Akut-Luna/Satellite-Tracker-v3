import os
import numpy as np
from dotenv import load_dotenv

load_dotenv(os.path.join('main', 'config', 'config_app.env'))
MIN_ANGLE_CHANGE_BEFORE_UPDATE = float(os.getenv('MIN_ANGLE_CHANGE_BEFORE_UPDATE'))

def should_update_motors(current_az, current_el, new_az, new_el):
    '''
    Determines if the newly calculated target azimuth and elevation differ sufficiently from the current position
    such that we need to send the motors new instructions
    Parameters:
        current_az: current azimuth of the antenna. 
        current_el: current elevation of the antenna. 
        new_az: latest value that was calculated for azimuth
        new_el: latest value that was calculated for elevation
    
    Returns:
        (bool): Bool that says if antenna should be moved
    '''
    def az_el_to_vector(azimuth, elevation):
        '''
        NOTE: I'm 99.9% sure that this function can be replaced by az_el_to_cartesian()
        They use different orientations of the coordiant systems but since we are only interested
        in the angle between 2 vectors that shouldn't matter. But I don't have acesses to the motorcontroller
        at the moment and I don't want to change a tested system with out the ability to test again.

        Convert azimuth and elevation angles (in degrees) to a 3D unit vector.
        Azimuth: angle in the x-y plane from x-axis (0° is +x, 90° is +y)
        Elevation: angle from x-y plane (90° is +z)
        '''
        # Convert degrees to radians
        az_rad = np.radians(azimuth)
        el_rad = np.radians(elevation)
        
        # Calculate the 3D vector components
        x = np.cos(el_rad) * np.cos(az_rad)
        y = np.cos(el_rad) * np.sin(az_rad)
        z = np.sin(el_rad)

        return np.array([x, y, z])
    
    current_vec = az_el_to_vector(current_az, current_el)
    new_vec = az_el_to_vector(new_az, new_el)

    # Calculate angle in radians using arccos of the normalized dot product
    dot_product = np.dot(current_vec, new_vec)
    angle_rad = np.arccos(np.clip(dot_product / (np.linalg.norm(current_vec) * np.linalg.norm(new_vec)), -1.0, 1.0))
    
    # Convert to degrees
    angle_deg = np.degrees(angle_rad)
    return angle_deg >= MIN_ANGLE_CHANGE_BEFORE_UPDATE

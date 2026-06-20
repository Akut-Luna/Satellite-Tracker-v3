import numpy as np

def doppler_shift(f0, range_rate):
    '''
    calculating doppler shifted frequency. 

    Parameters:
        f0 (float): emitted frequency in MHz
        range_rate (float): relative speed in m/s

    Returns:
        f1 (float): observed frequency in MHz
    
    SIGN CONVENTION: 
        if satellite comes closer, frequency need to get up. 
            => 1/(1 - range_rate/c) > 1 
            => 1 > (1 - range_rate/c) 
            => 1 + range_rate/c > 1
            => range_rate > 0
        
        but if the satellite comes closer the range gets smaller => range_rate is neg
            => range_rate needs to change sign
        
        analoge argument when satellite leaves
    '''
    c = 299792458    # m/s
    range_rate *= -1 # m/s

    f1 = f0 / (1 - range_rate/c) # MHz
    return f1

def rotate_by_euler(vector, euler_angles):
    '''
    Rotate a vector using Euler angles (ZYX convention).
    
    Parameters:
        vector (numpy.ndarray): 3D Cartesian coordinates [x, y, z]
        euler_angles (tuple): (roll, pitch, yaw) in degrees
    
    Returns:
        rotated_vector (numpy.ndarray): Rotated 3D Cartesian coordinates
    '''
    roll, pitch, yaw = np.radians(euler_angles)
    
    # Rotation matrices
    R_x = np.array([
        [1,      0      ,       0      ],
        [0, np.cos(roll), -np.sin(roll)],
        [0, np.sin(roll),  np.cos(roll)]
    ])
    
    R_y = np.array([
        [ np.cos(pitch), 0, np.sin(pitch)],
        [     0        , 1,      0       ],
        [-np.sin(pitch), 0, np.cos(pitch)]
    ])
    
    R_z = np.array([
        [np.cos(yaw), -np.sin(yaw), 0],
        [np.sin(yaw),  np.cos(yaw), 0],
        [     0     ,       0     , 1]
    ])
    
    # Combined rotation matrix (ZYX order)
    R = R_x @ R_y @ R_z
    
    # Apply rotation
    rotated_vector = R @ vector
    
    return rotated_vector

def az_el_to_cartesian(az, el): # TODO: DO we still need this?
    '''
    Convert azimuth and elevation angles to Cartesian coordinates.
    
    Parameters:
        az (float): Azimuth angle in degrees (0° is north, 90° is east)
        el (float): Elevation angle in degrees (0° is horizon, 90° is zenith)
    
    Returns:
        vector (numpy.ndarray): 3D Cartesian coordinates [x, y, z] on a unit sphere
    '''
    # Convert angles from degrees to radians
    az_rad = np.radians(az)
    el_rad = np.radians(el)
    
    # Convert to Cartesian coordinates
    x = np.cos(el_rad) * np.sin(az_rad)
    y = np.cos(el_rad) * np.cos(az_rad)
    z = np.sin(el_rad)
    
    return np.array([x, y, z])

def cartesian_to_az_el(vector):# TODO: DO we still need this?
    '''
    Convert Cartesian coordinates to azimuth and elevation angles.
    
    Parameters:
        vector (numpy.ndarray): 3D Cartesian coordinates [x, y, z]
    
    Returns:
        az (float): Azimuth in deg
        el (float): Elevation in deg
    '''
    # Normalize the vector
    vector = vector / np.linalg.norm(vector)
    x, y, z = vector
    
    # Calculate azimuth and elevation
    el = np.degrees(np.arcsin(z))
    az = np.degrees(np.arctan2(x, y))
    
    # Ensure azimuth is in [0, 360) range
    if az < 0:
        az += 360
    
    return az, el

def correction_matrix(az, el, roll, pitch, yaw):
    '''
    Parameters:
        az (float): Azimuth in degree
        el (float): Elevation in degree
        roll (float): roll in degree
        pitch (float): pitch in degree
        yaw (float): yaw in degree
    
    Returns:
        az (float): Azimuth in degree
        el (float): Elevation in degree
    '''
    vector = az_el_to_cartesian(az, el)
    vector = rotate_by_euler(vector, (roll, pitch, yaw))
    az, el = cartesian_to_az_el(vector)
    return az, el

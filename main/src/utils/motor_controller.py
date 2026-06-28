import socket
import numpy as np
from astropy import units as u
from astropy.coordinates import angular_separation
from PySide6.QtCore import QObject, Signal, Slot

class MotorWorker(QObject):
    # ------------------------------------ Signals (send data) ------------------------------------
    log = Signal(str)
    antenna_status_changed = Signal(float, float)
    antenna_connection_status_changed = Signal(bool)
    # ---------------------------------------------------------------------------------------------

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.socket = None
        self.last_time_motor_got_updated = None
        self.tracking = False

        # Antenna Status
        self.antenna_az = 0.0
        self.antenna_el = 0.0

    def log_message(self, message):
        self.log.emit(message) # -> ui

    # ------------------------------------ Slots (receive data) -----------------------------------
    def update_tracking(self, tracking):
        self.tracking = tracking
        if not tracking:
            if self.socket is not None: # send stop command to motors
                self.talk_to_motor_controller('stop')

    def move_motors(self, data):
        '''
        Parameters:
            data (dict): data from main_loop
        '''
        if not self.tracking:
            return

        target_az = data.get('az')
        target_el = data.get('el')

        target_az_rate = data.get('az_rate')
        target_el_rate = data.get('el_rate')

        now = data.get('t')

        if target_az is None or target_el is None:
            return
                       
        if self.socket is not None:
            # get current position from antenna
            antenna_az, antenna_el = self.talk_to_motor_controller('status')
            self.antenna_status_changed.emit(antenna_az, antenna_el) # -> ui
                    
            if self.should_update_motors(antenna_az, antenna_el, target_az, target_el):
                # calculate target position based on angular rate
                if target_az_rate is not None and target_el_rate is not None:
                    if self.last_time_motor_got_updated is not None:
                        delta_t = (now - self.last_time_motor_got_updated).total_seconds()
                        target_az += target_az_rate*delta_t
                        target_el += target_el_rate*delta_t
                self.last_time_motor_got_updated = now

                target_az = np.clip(target_az, 0, 360)
                target_el = np.clip(target_el, 0, 90)
                self.talk_to_motor_controller('set', target_az, target_el)

    def update_antenna_status(self):
        res = self.talk_to_motor_controller('status')

        # treat None or partial None results as no connection
        if (
            res is not None
            and isinstance(res, (tuple, list))
            and len(res) == 2
            and res[0] is not None
            and res[1] is not None
        ):
            antenna_az, antenna_el = res
        else: # no connection or invalid response
            antenna_az, antenna_el = 9999, 9999

        # only emit when the values actually changed
        if (self.antenna_az != antenna_az) or (self.antenna_el != antenna_el):
            self.antenna_az = antenna_az
            self.antenna_el = antenna_el
            self.antenna_status_changed.emit(antenna_az, antenna_el) # -> ui
    
    def go_close_connection(self):
        self.close_connection()
    # ---------------------------------------------------------------------------------------------

    def establish_connection(self):
        '''
        Establish a persistent connection to the motor controller, if available.
        '''

        host = self.config.motor_IP
        port = self.config.motor_port

        self.log_message(f'Trying to connect to {host}:{port}...')
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)  # Set a 5-second timeout for operations
            s.connect((host, port))

            self.socket = s  # Store socket
            self.log_message(f'Successfully connected to {host}:{port}')
            self.antenna_connection_status_changed.emit(True)
        except:
            self.socket = None
            self.log_message(f'Could not connect to {host}:{port}')
            self.antenna_connection_status_changed.emit(False)

    def close_connection(self):
        '''
        Close the socket connection properly.
        '''

        if self.socket:
            self.socket.close()
            self.socket = None
            self.log_message('Connection closed.')
            self.antenna_connection_status_changed.emit(False)

    def talk_to_motor_controller(self, command, az=0, el=0):
        '''
        Get the current position from the SPID motor controller using TCP socket.
        
        Parameters:
            comand (str): stop, status or set
            az (float): azimuth in degrees
            el (float): elevation in degrees
            
        Returns:
            azimuth (float): azimuth in degrees (only when command is 'status' else None)
            elevation (float): elevation in degrees (only when command is 'status' else None)

        Send to motor controller:
        ---------------------- packet (13 bytes) ----------------------
        Format: [START, H1, H2, H3, H4, PH, V1, V2, V3, V4, PV, K, END]
        
        S     : Start byte. This is always 0x57 ('W')
        H1-H4 : Azimuth as ASCII characters 0-9
        PH    : Azimuth resolution in steps per degree (ignored!)
        V1-V4 : Elevation as ASCII characters 0-9
        PV    : Elevation resolution in steps per degree (ignored!)
        K     : Command (0x0F=stop, 0x1F=status, 0x2F=set)
        END   : End byte. This is always 0x20 (space)
        ---------------------------------------------------------------

        Recive from motor controller:
        ---------------------- packet (12 bytes) ----------------------
        Format: [START, H1, H2, H3, H4, PH, V1, V2, V3, V4, PV, END]
        
        S     : Start byte. This is always 0x57 ('W')
        H1-H4 : Azimuth as ASCII characters 0-9
        PH    : Azimuth resolution in steps per degree (ignored!)
        V1-V4 : Elevation as ASCII characters 0-9
        PV    : Elevation resolution in steps per degree (ignored!)
        END   : End byte. This is always 0x20 (space)
        ---------------------------------------------------------------
        '''
        try:
            # if socket is None, then previous connection / reconnection attempts have failed
            # and we assume that we are working in offline mode.
            if self.socket is not None:
                if command == 'stop':
                    packet = bytearray(13)
                    packet[0] = 0x57    # START 'W'
                    packet[11] = 0x0F   # STOP
                    packet[12] = 0x20   # END (space)
                    self.socket.sendall(packet)
                    return None, None

                elif command == 'set':
                    packet = self.create_set_position_packet(az, el)
                    self.socket.sendall(packet)
                    return None, None

                elif command == 'status':
                    packet = bytearray(13)
                    packet[0] = 0x57    # START 'W'
                    packet[11] = 0x1F   # STATUS
                    packet[12] = 0x20   # END (space)
                    self.socket.sendall(packet)

                    # Wait until I get a response or socket times out
                    response = self.socket.recv(12)

                    # If we got less than 12 bytes, maybe it's a Rot1Prog (5 bytes)
                    if 5 <= len(response) and len(response) < 12:
                        # Rot1Prog response format:
                        # [0x57, H1, H2, H3, 0x20]
                        azimuth = response[1] * 100 + response[2] * 10 + response[3] - 360
                        return azimuth, 0
                        
                    elif len(response) >= 12:
                        # Rot2Prog response format:
                        # [0x57, H1, H2, H3, H4, PH, V1, V2, V3, V4, PV, 0x20]
                        azimuth = response[1] * 100 + response[2] * 10 + response[3] + response[4] / 10 - 360
                        elevation = response[6] * 100 + response[7] * 10 + response[8] + response[9] / 10 - 360
                        return azimuth, elevation
                    
                    else:
                        raise TimeoutError(f'Received only {len(response)} bytes, expected 5 or 12')

                else:
                    self.log_message(f'Invalid command: {command}')
                    return None, None
        except Exception as e:
            '''
            Attempt to reconnect after disconnection. 
            If the motor controller responds within 5 seconds, 
            a new connection will be established. Otherwise, 
            it will be considered that the controller has completely disconnected 
            and no further communication attempt will be made.
            '''            
            self.log_message(f'Disconnected from motor controller:\n{e}.\nTrying to reconnect...')
            self.close_connection()
            self.establish_connection()
            return None, None       

    def create_set_position_packet(self, azimuth, elevation, az_resolution=10, el_resolution=10):
        '''
        Create a command packet to set the position for a Rot2Prog controller.
        
        Parameters:
            azimuth (float): Azimuth in degrees (0-360)
            elevation (float): Elevation in degrees
            az_resolution (int): Azimuth resolution in steps per degree
            el_resolution (int): Elevation resolution in steps per degree
            
        Returns:
            bytearray: 13-byte command packet
        '''
        # Create command packet (13 bytes)
        packet = bytearray(13)
        
        # Start byte
        packet[0] = 0x57  # 'W'
        
        # Azimuth encoding
        az_steps = int((360 + azimuth) * az_resolution)
        az_str = f'{az_steps:04d}' # formats the steps count as a 4-digit string with leading zeros

        # encode each digit as its ASCII value
        packet[1] = ord(az_str[0])  # Thousands H1
        packet[2] = ord(az_str[1])  # Hundreds  H2
        packet[3] = ord(az_str[2])  # Tens      H3
        packet[4] = ord(az_str[3])  # Ones      H4
        
        # Azimuth resolution
        packet[5] = az_resolution
        
        # Elevation encoding
        el_steps = int((360 + elevation) * el_resolution)
        el_str = f'{el_steps:04d}'
        packet[6] = ord(el_str[0])  # Thousands V1
        packet[7] = ord(el_str[1])  # Hundreds  V2
        packet[8] = ord(el_str[2])  # Tens      V3
        packet[9] = ord(el_str[3])  # Ones      V4
        
        # Elevation resolution
        packet[10] = el_resolution
        
        # Command byte (0x2F for SET)
        packet[11] = 0x2F
        
        # End byte
        packet[12] = 0x20  # space
        
        return packet

    def should_update_motors(self, antenna_az, antenna_el, target_az, target_el):
        '''
        Determines if the newly calculated target azimuth and elevation differ sufficiently from the current position
        such that we need to send the motors new instructions
        Parameters:
            antenna_az: current azimuth of the antenna. 
            antenna_el: current elevation of the antenna. 
            target_az: latest value that was calculated for azimuth
            target_el: latest value that was calculated for elevation
        
        Returns:
            (bool): Bool that says if antenna should be moved
        '''

        antenna_az *= u.deg
        antenna_el *= u.deg
        target_az *= u.deg
        target_el *= u.deg
        angle_change = angular_separation(antenna_az, antenna_el, target_az, target_el)
        return angle_change.to(u.deg).value >= self.config.min_angle_change_before_update


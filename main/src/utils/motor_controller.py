import socket
import time
from PySide6.QtCore import QObject, Signal

class MotorWorker(QObject):
    # Signals to talk back to the UI
    status_received = Signal(float, float) # az, el
    log_signal = Signal(str)

    def __init__(self, ip, port):
        super().__init__()
        self.ip = ip
        self.port = port
        self.socket = None
        self.last_time_motor_got_updated = None

    def connect_controller(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(2.0)
            self.socket.connect((self.ip, self.port))
            self.log_signal.emit(f'Connected to {self.ip}')
        except Exception as e:
            self.log_signal.emit(f'Connection failed: {e}')

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
        def recv_exact(N):
            '''Helper to ensure we get exactly N bytes from a slow controller.'''
            data = bytearray()
            self.socket.settimeout(2.0) # 2 second timeout for slow baud rates
            while len(data) < N:
                chunk = self.socket.recv(N - len(data))
                if not chunk:
                    return None # Connection closed
                data.extend(chunk)
            return data

        try:
            if not self.socket:
                # Try to connect if socket is missing
                self.connect_controller()
                if not self.socket: return None, None

            packet = bytearray(13)
            packet[0] = 0x57    # START 'W'
            packet[12] = 0x20   # END (space)

            if command == 'stop':
                packet[11] = 0x0F
                self.socket.sendall(packet)
                return None, None

            elif command == 'set':
                packet = self.create_set_position_packet(az, el)
                self.socket.sendall(packet)
                return None, None

            elif command == 'status':
                packet[11] = 0x1F
                self.socket.sendall(packet)

                # Wait until I get a response or socket times out
                # Read the START byte first to align the stream
                start_byte = recv_exact(1)
                if not start_byte or start_byte[0] != 0x57:
                    raise ConnectionError('Invalid Start Byte received')

                # Read the rest (11 more bytes for Rot2Prog)
                remaining = recv_exact(11)
                if not remaining:
                    raise ConnectionError('Incomplete packet received')
                
                # Combine [0x57] + [11 bytes] = 12 bytes
                response = start_byte + remaining

                # Decode Rot2Prog (12 bytes)
                azimuth = (response[1] * 100 + response[2] * 10 + response[3] + response[4] / 10 - 360)
                elevation = (response[6] * 100 + response[7] * 10 + response[8] + response[9] / 10 - 360)
                
                return azimuth, elevation

            else:
                self.log_message(f'Invalid command: {command}')
                return None, None

        except (socket.error, ConnectionError, TimeoutError) as e:
            self.log_message(f'Communication error: {e}. Reconnecting...')
            
            # Prevent infinite recursion/SegFault by closing before re-opening
            try:
                self.motor_controller_close_connection()
                time.sleep(1) # Give the OS time to release the port # TODO: make asynchon <----------------------------------
                self.motor_controller_establish_connection()
            except:
                pass # Avoid crashing during the recovery attempt
                
            return None, None

        except Exception as e:
            # Catch unexpected logic errors that cause SegFaults
            self.log_message(f'Critical Logic Error: {e}')
            return None, None
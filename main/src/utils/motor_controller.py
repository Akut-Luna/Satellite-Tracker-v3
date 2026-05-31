import socket
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

    def connect_controller(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(2.0)
            self.socket.connect((self.ip, self.port))
            self.log_signal.emit(f"Connected to {self.ip}")
        except Exception as e:
            self.log_signal.emit(f"Connection failed: {e}")

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

    def send_command(self, az, el):
        if not self.socket: return
        try:
            # Your packet logic here...
            self.log_signal.emit(f"Sending: {az}, {el}")
            packet = self.create_set_position_packet(az, el)
            self.socket.sendall(packet)
        except Exception as e:
            self.log_signal.emit(f"Send error: {e}")

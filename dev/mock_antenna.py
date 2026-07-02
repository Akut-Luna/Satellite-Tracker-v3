import socket
class Controller():
    def __init__(self):
        self.state = {
            'az': 45,
            'el': 30,
            'ph': 10,
            'pv': 10
        }

    def start_mock_server(self, host='127.0.0.1', port=65432):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((host, port))
        server.listen(1)
        print(f'Mock antenna listening on {host}:{port}...')

        while True:
            conn, addr = server.accept()
            print(f'Connected by {addr}')
            try:
                while True:
                    data = conn.recv(13)
                    if not data:
                        break

                    # Parse command byte (index 11)
                    cmd = data[11]
                    
                    if cmd == 0x2F: # SET
                        try:
                            h_val = int(data[1:5].decode('ascii'))
                            v_val = int(data[6:10].decode('ascii'))
                            self.state['az'] = (h_val / self.state['ph']) - 360
                            self.state['el'] = (v_val / self.state['pv']) - 360
                            print(f'[CMD] SET -> Az: {self.state['az']}°, El: {self.state['el']}°')
                        except Exception as e:
                            print(f'[ERR] Failed to decode SET: {e}')
                    
                    elif cmd in [0x0F, 0x1F]: # STOP or STATUS
                        if cmd == 0x0F:
                            label = 'STOP' 
                        else:
                            label = 'STATUS'

                        h = int((self.state['az'] + 360) * self.state['ph'])
                        v = int((self.state['el'] + 360) * self.state['pv'])
                        
                        resp = bytearray([0x57])
                        resp.extend([h // 1000, (h // 100) % 10, (h // 10) % 10, h % 10])
                        resp.append(self.state['ph'])
                        resp.extend([v // 1000, (v // 100) % 10, (v // 10) % 10, v % 10])
                        resp.append(self.state['pv'])
                        resp.append(0x20)
                        
                        conn.sendall(resp)
                        print(f'[CMD] {label} -> Sent Response: {self.state}')
                        # print(f'[CMD] {label} -> Sent Response: {resp.hex(' ')}')

            except Exception as e:
                print(f'Error: {e}')
            finally:
                conn.close()
                print('Client disconnected')

if __name__ == '__main__':
    try:
        con = Controller()
        con.start_mock_server()
    except KeyboardInterrupt:
        print('\nShutting down...')
        exit(0)
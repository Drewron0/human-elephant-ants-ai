import socket
import threading
import json

class NetworkManager:
    def __init__(self, is_host, ip='127.0.0.1', port=5555, move_callback=None):
        self.is_host = is_host
        self.ip = ip
        self.port = port
        self.conn = None
        self.move_callback = move_callback
        self.running = True

    def start(self):
        threading.Thread(target=self._run_network, daemon=True).start()

    def _run_network(self):
        try:
            if self.is_host:
                server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server.bind((self.ip, self.port))
                server.listen(1)
                self.conn, _ = server.accept()
            else:
                self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.conn.connect((self.ip, self.port))
            
            while self.running and self.conn:
                data = self.conn.recv(1024)
                if not data: break
                if self.move_callback:
                    move = json.loads(data.decode())
                    self.move_callback(move['start'], move['end'])
        except Exception:
            pass

    def send_move(self, start_pos, end_pos):
        if self.conn:
            data = json.dumps({'start': start_pos, 'end': end_pos})
            self.conn.sendall(data.encode())

    def close(self):
        self.running = False
        if self.conn:
            self.conn.close()
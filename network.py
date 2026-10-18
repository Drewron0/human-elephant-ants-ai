import socket
import threading
import json
from typing import Callable, Optional, Dict, Any


class NetworkManager:
    def __init__(self, is_host: bool, ip: str = '127.0.0.1', port: int = 5555,
                 on_connect: Optional[Callable[[], None]] = None,
                 on_move: Optional[Callable[[list, list], None]] = None,
                 on_restart: Optional[Callable[[], None]] = None,
                 on_surrender: Optional[Callable[[], None]] = None,
                 on_disconnect: Optional[Callable[[str], None]] = None):
        self.is_host = is_host
        self.ip = ip
        self.port = port
        self.conn: Optional[socket.socket] = None
        self.server_sock: Optional[socket.socket] = None
        self.running = False
        
        # Callbacks
        self.on_connect = on_connect
        self.on_move = on_move
        self.on_restart = on_restart
        self.on_surrender = on_surrender
        self.on_disconnect = on_disconnect

    def start(self):
        self.running = True
        threading.Thread(target=self._run_network, daemon=True).start()

    def _run_network(self):
        try:
            if self.is_host:
                self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_sock.bind((self.ip, self.port))
                self.server_sock.listen(1)
                self.conn, _ = self.server_sock.accept()
            else:
                self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.conn.connect((self.ip, self.port))

            if self.on_connect:
                self.on_connect()

            buffer = ""
            while self.running and self.conn:
                data = self.conn.recv(2048)
                if not data:
                    break
                buffer += data.decode('utf-8', errors='ignore')
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                        self._handle_message(msg)
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            if self.running and self.on_disconnect:
                self.on_disconnect(str(e))
        finally:
            self.close()

    def _handle_message(self, msg: Dict[str, Any]):
        msg_type = msg.get('type')
        if msg_type == 'MOVE' and self.on_move:
            self.on_move(msg.get('start'), msg.get('end'))
        elif msg_type == 'RESTART' and self.on_restart:
            self.on_restart()
        elif msg_type == 'SURRENDER' and self.on_surrender:
            self.on_surrender()

    def send_move(self, start_pos, end_pos):
        self._send({'type': 'MOVE', 'start': list(start_pos), 'end': list(end_pos)})

    def send_restart(self):
        self._send({'type': 'RESTART'})

    def send_surrender(self):
        self._send({'type': 'SURRENDER'})

    def _send(self, payload: Dict[str, Any]):
        if self.conn:
            try:
                data_bytes = (json.dumps(payload) + '\n').encode('utf-8')
                self.conn.sendall(data_bytes)
            except Exception:
                pass

    def close(self):
        self.running = False
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None
        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass
            self.server_sock = None
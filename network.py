"""
網路連線：以換行分隔的 JSON 訊息，背景執行緒收資料。
"""
import json
import socket
import threading
from collections import deque


class Net:
    """以換行分隔的 JSON；所有訊息都排進佇列，不會漏掉一次性的事件。"""

    def __init__(self, sock):
        self.sock = sock
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.settimeout(8)
        self.q = deque()
        self.alive = True
        threading.Thread(target=self._recv, daemon=True).start()

    def _recv(self):
        buf = b""
        while self.alive:
            try:
                data = self.sock.recv(1 << 16)
            except socket.timeout:
                continue
            except OSError:
                break
            if not data:
                break
            buf += data
            *lines, buf = buf.split(b"\n")
            for ln in lines:
                if ln:
                    try:
                        self.q.append(json.loads(ln))
                    except ValueError:
                        pass
        self.alive = False

    def drain(self):
        out = []
        while self.q:
            out.append(self.q.popleft())
        return out

    def send(self, obj):
        if not self.alive:
            return
        try:
            self.sock.sendall((json.dumps(obj, separators=(",", ":"), ensure_ascii=False) + "\n").encode())
        except OSError:
            self.alive = False

    def close(self):
        self.alive = False
        try:
            self.sock.close()
        except OSError:
            pass

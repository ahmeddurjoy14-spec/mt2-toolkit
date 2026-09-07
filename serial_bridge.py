"""
serial_bridge.py — Serial OR TCP bridge to MT2 firmware.
- find_port(): auto-detect /dev/ttyUSB* / ttyACM*
- find_tcp():  try 192.168.4.1:23 (MT2-LINK AP)
- MT2Bridge:   line-based command/response over chosen transport
"""
import os, glob, time, socket
try:
    import serial
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

SERIAL_BAUD = 115200
SERIAL_TIMEOUT = 2.0
PROBE_SERIAL = ("/dev/ttyUSB*", "/dev/ttyACM*", "/dev/tty.usbserial*")
TCP_HOSTS = ("192.168.4.1", "mt2.local")
TCP_PORT = 23
TCP_TIMEOUT = 3.0

def find_port(all_=False):
    if not HAS_SERIAL:
        return []
    found = []
    for pattern in PROBE_SERIAL:
        for p in glob.glob(pattern):
            if os.path.exists(p):
                found.append(p)
    if all_:
        return found
    for pref in ("/dev/ttyUSB0", "/dev/ttyACM0", "/dev/ttyUSB1", "/dev/ttyACM1"):
        if pref in found:
            return pref
    return found[0] if found else None

def find_tcp():
    """Probe TCP hosts; return (host, port) of first responsive, or None."""
    for host in TCP_HOSTS:
        try:
            addr = socket.getaddrinfo(host, TCP_PORT, socket.AF_INET, socket.SOCK_STREAM)[0][4]
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(TCP_TIMEOUT)
            s.connect(addr)
            s.close()
            return (host, TCP_PORT)
        except (socket.gaierror, socket.timeout, ConnectionRefusedError, OSError):
            continue
    return None

class SerialTransport:
    name = "serial"
    def __init__(self, port):
        self.ser = serial.Serial(port, SERIAL_BAUD, timeout=SERIAL_TIMEOUT)
        time.sleep(1.5)
        self.ser.reset_input_buffer()
    def close(self): self.ser.close()
    def write(self, data): self.ser.write(data); self.ser.flush()
    def readline(self):
        return self.ser.readline().decode("utf-8", errors="replace")
    def available(self): return self.ser.in_waiting

class TcpTransport:
    name = "tcp"
    def __init__(self, host, port=TCP_PORT):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(TCP_TIMEOUT)
        self.sock.connect((host, port))
        self.sock.settimeout(SERIAL_TIMEOUT)
        self.buf = b""
    def close(self): self.sock.close()
    def write(self, data): self.sock.sendall(data)
    def readline(self):
        while b"\n" not in self.buf:
            chunk = self.sock.recv(256)
            if not chunk:
                return ""
            self.buf += chunk
        line, _, self.buf = self.buf.partition(b"\n")
        return line.decode("utf-8", errors="replace") + "\n"
    def available(self): return len(self.buf) > 0

def MT2Serial(port, **kw):
    return MT2Bridge(SerialTransport(port), **kw)

def MT2Tcp(host=None, port=TCP_PORT, **kw):
    if host is None:
        found = find_tcp()
        if not found:
            raise ConnectionError("no MT2-LINK TCP server found")
        host, port = found
    return MT2Bridge(TcpTransport(host, port), **kw)

class MT2Bridge:
    def __init__(self, transport):
        self.t = transport
        print(f"[bridge] transport: {transport.name}")

    def close(self): self.t.close()

    def _read_lines(self, wait):
        out = []
        deadline = time.time() + wait
        self.t.sock.settimeout(0.1) if hasattr(self.t, 'sock') else None
        old_to = None
        while time.time() < deadline:
            try:
                line = self.t.readline()
                if line:
                    out.append(line.rstrip())
            except (socket.timeout, TimeoutError):
                pass
            except Exception as e:
                print(f"[bridge] read err: {e}")
                break
        return out

    def send(self, cmd, wait=0.5, lines=200):
        self.t.write((cmd + "\n").encode("utf-8"))
        out = self._read_lines(wait)
        return out[:lines]

    def stream(self):
        while True:
            try:
                line = self.t.readline()
                if line:
                    yield line.rstrip()
            except Exception:
                break

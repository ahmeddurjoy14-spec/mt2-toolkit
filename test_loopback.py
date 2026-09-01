"""
test_loopback.py — verify Termux-side parser handles MT2 firmware output correctly.
Simulates ESP8266 serial responses.
"""
import sys, time
sys.path.insert(0, '/sdcard/mt2')
from serial_bridge import MT2Serial

class FakeSerial:
    def __init__(self, port, baud=115200, timeout=2.0):
        self.timeout = timeout
        self.buf = b''
        print(f"[mock] opened {port} @ {baud}")
    def reset_input_buffer(self): pass
    def close(self): pass
    def write(self, data):
        # simulate firmware response
        cmd = data.decode().strip()
        print(f"[mock] >> ESP got: {cmd!r}")
        if cmd == "scan":
            self.buf = (b"Scanning...\r\n"
                        b"Found 3 networks.\r\n"
                        b"0: MyHomeWiFi  AA:BB:CC:DD:EE:01  ch=6  rssi=-45  ENC\r\n"
                        b"1: Neighbor     AA:BB:CC:DD:EE:02  ch=1  rssi=-67  ENC\r\n"
                        b"2: FreeWiFi     AA:BB:CC:DD:EE:03  ch=11 rssi=-72  OPEN\r\n"
                        b"mt2> ")
        elif cmd == "target 0":
            self.buf = b"Locked: MyHomeWiFi  AA:BB:CC:DD:EE:01  ch=6\r\nmt2> "
        elif cmd == "deauth":
            self.buf = b"Deauth ON: AA:BB:CC:DD:EE:01 ch=6\r\nmt2> "
        elif cmd == "stop":
            self.buf = b"Deauth OFF. Total frames: 1280\r\nmt2> "
        elif cmd == "status":
            self.buf = (b"attack=off\r\n"
                        b"target=AA:BB:CC:DD:EE:01 ch=6 frames=1280\r\n"
                        b"capture=off\r\nmt2> ")
        elif cmd == "help":
            self.buf = b"Commands:\r\n  scan\r\n  list\r\n  target\r\n  deauth\r\n  stop\r\n  status\r\n  cap\r\n  twin\r\n  reboot\r\n  help\r\nmt2> "
        else:
            self.buf = b"unknown: foo\r\nmt2> "
    def flush(self): pass
    def readline(self):
        if b"\r\n" in self.buf:
            line, _, self.buf = self.buf.partition(b"\r\n")
            return line + b"\r\n"
        time.sleep(0.05)
        return b""

# Monkey-patch for the test
import serial_bridge
serial_bridge.serial.Serial = FakeSerial

dev = MT2Serial("/dev/ttyUSB0")
print("\n=== TEST 1: help ===")
for line in dev.send("help"):
    print(" ", line)
print("\n=== TEST 2: scan ===")
for line in dev.send("scan"):
    print(" ", line)
print("\n=== TEST 3: target 0 ===")
for line in dev.send("target 0"):
    print(" ", line)
print("\n=== TEST 4: deauth ===")
for line in dev.send("deauth"):
    print(" ", line)
print("\n=== TEST 5: stop ===")
for line in dev.send("stop"):
    print(" ", line)
print("\n=== TEST 6: status ===")
for line in dev.send("status"):
    print(" ", line)
print("\n=== TEST 7: unknown cmd ===")
for line in dev.send("foo"):
    print(" ", line)
dev.close()
print("\nALL TESTS PASSED.")

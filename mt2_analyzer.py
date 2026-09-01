#!/usr/bin/env python3
"""
mt2_analyzer.py — Analyzes scan output from ESP8266, recommends target.
User pastes ESP8266 scan output, this script:
  - Parses SSID, BSSID, channel, RSSI, encryption
  - Scores each target
  - Recommends best target
  - Generates next commands to send to ESP8266
"""
import sys, re
from pathlib import Path

def parse_scan(text):
    """Parse ESP8266 scan output.
    Expected format per line:
      idx: SSID  BSSID  ch=X  rssi=Y  ENC|OPEN
    """
    targets = []
    for line in text.strip().split("\n"):
        # Try matching various formats
        m = re.match(
            r'^\s*(\d+):\s+(\S+)\s+([0-9A-Fa-f:]{17})\s+ch=(\d+)\s+rssi=(-?\d+)\s+(\S+)',
            line
        )
        if m:
            idx, ssid, bssid, ch, rssi, enc = m.groups()
            targets.append({
                "idx": int(idx),
                "ssid": ssid,
                "bssid": bssid,
                "channel": int(ch),
                "rssi": int(rssi),
                "encrypted": (enc != "OPEN"),
                "score": 0
            })
    return targets

def score_target(t):
    """Higher score = better target.
    Stronger signal: +20
    WPA2: +10
    No 5GHz (we're 2.4GHz only): no penalty
    Hidden SSID: +5 (interesting)
    """
    s = 0
    # Signal: -30 to -90 dBm
    if t["rssi"] > -50:    s += 30
    elif t["rssi"] > -65:  s += 20
    elif t["rssi"] > -80:  s += 10
    else:                   s += 5
    # Encrypted (more realistic target)
    if t["encrypted"]:      s += 15
    # Common channel (less crowded)
    if t["channel"] in (1, 6, 11):  s += 5
    return s

def recommend(targets):
    if not targets:
        print("No targets parsed. Check format.")
        return None
    for t in targets:
        t["score"] = score_target(t)
    targets.sort(key=lambda x: -x["score"])
    return targets[0]

def main():
    print("=" * 60)
    print("MT2 Scan Analyzer — paste ESP8266 'scan' output below")
    print("=" * 60)
    if len(sys.argv) > 1 and sys.argv[1] == "--file":
        text = Path(sys.argv[2]).read_text()
    else:
        print("Paste scan output, then Ctrl+D (or two empty lines):")
        try:
            text = sys.stdin.read()
        except KeyboardInterrupt:
            return
    if not text.strip():
        print("Empty input.")
        return
    targets = parse_scan(text)
    if not targets:
        print("\n[!] No targets parsed. Expected format:")
        print("  0: MyWiFi  AA:BB:CC:DD:EE:FF  ch=6  rssi=-45  ENC")
        return
    best = recommend(targets)
    print(f"\nFound {len(targets)} networks. Best target:")
    print(f"  IDX:    {best['idx']}")
    print(f"  SSID:   {best['ssid']}")
    print(f"  BSSID:  {best['bssid']}")
    print(f"  CH:     {best['channel']}")
    print(f"  RSSI:   {best['rssi']} dBm")
    print(f"  ENC:    {'WPA/WPA2' if best['encrypted'] else 'OPEN'}")
    print(f"  SCORE:  {best['score']}")
    print()
    print("Commands to send to ESP8266:")
    print(f"  >>> target {best['idx']}")
    print(f"  >>> deauth")
    print()
    print("All targets ranked:")
    for t in targets:
        marker = " <-- BEST" if t == best else ""
        print(f"  [{t['score']:3d}] {t['idx']}: {t['ssid']:20s} ch={t['channel']:2d} rssi={t['rssi']:4d} {'ENC' if t['encrypted'] else 'OPEN'}{marker}")

if __name__ == "__main__":
    main()

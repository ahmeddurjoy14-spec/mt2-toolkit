# MT2 WiFi Pentest Toolkit

ESP8266-based WiFi penetration testing platform with deauth, KARMA, and evil twin attacks.

## Features

- **Deauth Attack** - Disconnect clients from target AP
- **KARMA Attack** - Passive/Active probe response attacks
- **Evil Twin** - Fake AP with captive portal
- **Handshake Capture** - Capture WPA handshakes
- **Beacon Flood** - Mass fake AP broadcast

## Hardware

- NodeMCU ESP8266 (or compatible)
- USB OTG for Android

## Build Status

| Component | Status |
|-----------|--------|
| Firmware | ![Build](https://github.com/YOUR_USERNAME/mt2-toolkit/workflows/Build%20MT2%20Firmware/badge.svg) |

## Quick Start

### 1. Flash Firmware
```bash
esptool.py --port /dev/ttyUSB0 write_flash 0x00000 MT2_firmware.bin
```

### 2. Connect ESP8266
```bash
python3 mt2_attack.py scan
```

### 3. Run Attack
```bash
# Deauth
python3 evil_twin_advanced.py --ssid TargetWiFi --channel 6

# KARMA
python3 karma_advanced.py --ssid FreeWiFi --channel 6 --mode active

# Full Attack
python3 evil_twin_advanced.py --ssid TargetWiFi --channel 6
```

## Cloud Build

Firmware compiles automatically via GitHub Actions. Download from Actions tab.

## License

Educational use only. Only test networks you own or have permission to test.

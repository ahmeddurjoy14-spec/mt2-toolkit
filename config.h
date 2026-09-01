#ifndef CONFIG_H
#define CONFIG_H
#include <Arduino.h>

// ============================================================
//  MT2 — Headless Evil Twin / Deauth Firmware
//  No display. No buttons. Controlled via Serial (115200).
// ============================================================

// --- SD Card (SPI) — moved off D0 (was conflicting w/ BTN_UP) ---
#define SD_CS      D4   // was D0
// SPI bus: D5=CLK, D6=MISO, D7=MOSI (ESP8266 hardware SPI)

// --- Debug / Status ---
#define SERIAL_BAUD   115200

// --- Attack Settings ---
#define DEFAULT_PKT_RATE  20    // legacy (now uses burst mode)
#define BURST_SIZE        32    // frames per type (deauth/disassoc)
#define BURST_PAUSE_MS    20    // yield + watchdog feed (aggressive)
#define MAX_TARGETS       20    // up from 10

// --- Evil Twin AP ---
#define AP_MAX_CLIENTS    8
#define DNS_PORT          53

// --- Network struct (shared with .ino + .h) ---
struct Network {
  char    ssid[33];
  uint8_t bssid[6];
  int     channel;
  int     rssi;
  bool    encrypted;
};

// --- CLI command struct ---
#define CLI_MAX_ARGS  6
struct CliCommand {
  char verb[16];
  int  argc;
  char argv[CLI_MAX_ARGS][32];
};

// --- Evil twin globals (defined in evil_twin.h) ---
extern bool     twinRunning;
extern uint8_t  twinChan;
extern char     twinSsid[33];

#endif

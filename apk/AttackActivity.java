package com.mt2.attack;

import android.app.Activity;
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

            logView            = findViewById(R.id.logView);
            logView.setMovementMethod(new ScrollingMovementMethod());
            logScrollView      = findViewById(R.id.logScrollView);
            attackTargetSSID   = findViewById(R.id.attackTargetSSID);
            attackTargetInfo   = findViewById(R.id.attackTargetInfo);
            cliInput           = findViewById(R.id.cliInput);
            btnDeauth          = findViewById(R.id.btnDeauth);
            btnEvilTwin        = findViewById(R.id.btnEvilTwin);
            btnHandshake       = findViewById(R.id.btnHandshake);
            btnKarma           = findViewById(R.id.btnKarma);
            btnFull            = findViewById(R.id.btnFull);
            btnTDeauth         = findViewById(R.id.btnTDeauth);
            btnStop            = findViewById(R.id.btnStop);
            btnBack            = findViewById(R.id.btnBack);
            btnSend            = findViewById(R.id.btnSend);
            btnDebug           = findViewById(R.id.btnDebug);
            btnAutoScroll      = findViewById(R.id.btnAutoScroll);

            serial = SerialManager.getInstance(this);

            // Set initial target from intent
            targetSSID = getIntent().getStringExtra("target_ssid");
            if (targetSSID != null) {
                attackTargetSSID.setText("Target: " + targetSSID);
                attackTargetInfo.setText("WiFi Pentest Mode");
            } else {
                attackTargetSSID.setText("Target: —");
                attackTargetInfo.setText("Select target from Scan");
            }

            btnDeauth.setOnClickListener(v -> attackDeauth());
            btnEvilTwin.setOnClickListener(v -> attackEvilTwin());
            btnHandshake.setOnClickListener(v -> attackHandshake());
            btnKarma.setOnClickListener(v -> attackKarma());
            btnFull.setOnClickListener(v -> attackFull());
            btnTDeauth.setOnClickListener(v -> attackTargetedDeauth());
            btnStop.setOnClickListener(v -> stopAttack());
            btnBack.setOnClickListener(v -> finish());
            btnSend.setOnClickListener(v -> sendCommand());
            btnDebug.setOnClickListener(v -> toggleDebug());
            btnAutoScroll.setOnClickListener(v -> toggleAutoScroll());

            logView.append("\n[ATTACK] Ready. Select target and begin.");
        } catch (Exception e) {
            Toast.makeText(this, "Error: " + e.getMessage(), Toast.LENGTH_SHORT).show();
        }
    }

    private void attackDeauth() {
        if (!serial.isConnected()) { Toast.makeText(this, "Not connected", Toast.LENGTH_SHORT).show(); return; }
        logView.append("\n[DEAUTH] Starting full deauth...");
        serial.sendCommand("deauth");
    }

    private void attackFull() {
        if (!serial.isConnected()) { Toast.makeText(this, "Not connected", Toast.LENGTH_SHORT).show(); return; }
        logView.append("\n[DEAUTH] Full deauth active");
        serial.sendCommand("full_deauth");
    }

    private void attackTargetedDeauth() {
        if (!serial.isConnected()) { Toast.makeText(this, "Not connected", Toast.LENGTH_SHORT).show(); return; }
        logView.append("\n[DEAUTH] Targeted deauth active");
        serial.sendCommand("targeted_deauth");
    }

    private void attackEvilTwin() {
        if (!serial.isConnected()) { Toast.makeText(this, "Not connected", Toast.LENGTH_SHORT).show(); return; }
        logView.append("\n[EVIL TWIN] Portal started");
        serial.sendCommand("evil_twin");
    }

    private void attackHandshake() {
        if (!serial.isConnected()) { Toast.makeText(this, "Not connected", Toast.LENGTH_SHORT).show(); return; }
        logView.append("\n[HANDSHAKE] Capturing handshake...");
        serial.sendCommand("handshake");
    }

    private void attackKarma() {
        if (!serial.isConnected()) { Toast.makeText(this, "Not connected", Toast.LENGTH_SHORT).show(); return; }
        logView.append("\n[KARMA] Portal started");
        serial.sendCommand("karma");
    }

    private void stopAttack() {
        logView.append("\n[STOP] All attacks stopped");
        serial.sendCommand("stop");
    }

    private void sendCommand() {
        String cmd = cliInput.getText().toString();
        if (cmd.isEmpty()) return;
        if (!serial.isConnected()) { Toast.makeText(this, "Not connected", Toast.LENGTH_SHORT).show(); return; }
        logView.append("\n[CMD] " + cmd);
        serial.sendCommand(cmd);
        cliInput.setText("");
    }

    private void toggleDebug() {
        debugMode = !debugMode;
        btnDebug.setText(debugMode ? "DEBUG: ON" : "DEBUG: OFF");
    }

    private void toggleAutoScroll() {
        autoScroll = !autoScroll;
    }

    @Override
    public void onData(String line) {
        runOnUiThread(() -> logView.append("\n" + line));
    }

    @Override
    public void onConnected(boolean isConnected, String info) {
        runOnUiThread(() -> {
            if (isConnected) {
                logView.append("\n[CONNECTED] ESP32 ready for attacks");
            }
        });
    }
}

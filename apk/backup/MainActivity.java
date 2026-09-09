package com.mt2.attack;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {

    private TextView statusView, deviceInfo;
    private Button btnConnect, btnScan, btnAttack, btnBT, btnExit;
    private SerialManager serial;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_connect);

        statusView = findViewById(R.id.statusText);
        deviceInfo = findViewById(R.id.deviceInfo);
        btnConnect = findViewById(R.id.btnConnect);
        btnScan = findViewById(R.id.btnScan);
        btnAttack = findViewById(R.id.btnAttack);
        btnBT = findViewById(R.id.btnBT);
        btnExit = findViewById(R.id.btnExit);

        serial = SerialManager.getInstance(this);
        serial.setListener(new SerialManager.DataListener() {
            @Override
            public void onData(String line) {
                runOnUiThread(() -> deviceInfo.setText(line));
            }
            @Override
            public void onConnected(boolean isConnected, String info) {
                runOnUiThread(() -> statusView.setText(isConnected ? "✓ CONNECTED @ 115200" : "⚠ DISCONNECTED"));
            }
        });

        btnConnect.setOnClickListener(v -> connectDevice());
        btnScan.setOnClickListener(v -> startScan());
        btnAttack.setOnClickListener(v -> startAttack());
        btnBT.setOnClickListener(v -> startBluetooth());
        btnExit.setOnClickListener(v -> finish());

        updateStatus();
    }

    private void connectDevice() {
        if (serial.connect()) {
            statusView.setText("✓ CONNECTED @ 115200");
            statusView.setTextColor(getResources().getColor(R.color.accent_green));
            Toast.makeText(this, "ESP32 Connected", Toast.LENGTH_SHORT).show();
        } else {
            statusView.setText("⚠ DISCONNECTED");
            statusView.setTextColor(getResources().getColor(R.color.accent_red));
            Toast.makeText(this, "No ESP32 found", Toast.LENGTH_SHORT).show();
        }
    }

    private void startScan() {
        if (!serial.isConnected()) {
            Toast.makeText(this, "Connect ESP32 first", Toast.LENGTH_SHORT).show();
            return;
        }
        Intent intent = new Intent(this, ScanActivity.class);
        startActivity(intent);
    }

    private void startAttack() {
        if (!serial.isConnected()) {
            Toast.makeText(this, "Connect ESP32 first", Toast.LENGTH_SHORT).show();
            return;
        }
        Intent intent = new Intent(this, AttackActivity.class);
        startActivity(intent);
    }

    private void startBluetooth() {
        if (!serial.isConnected()) {
            Toast.makeText(this, "Connect ESP32 first", Toast.LENGTH_SHORT).show();
            return;
        }
        Intent intent = new Intent(this, BluetoothActivity.class);
        startActivity(intent);
    }

    private void updateStatus() {
        new Thread(() -> {
            while (!isFinishing()) {
                runOnUiThread(() -> {
                    if (serial.isConnected()) {
                        statusView.setText("✓ CONNECTED @ 115200");
                        statusView.setTextColor(getResources().getColor(R.color.accent_green));
                    } else {
                        statusView.setText("⚠ DISCONNECTED");
                        statusView.setTextColor(getResources().getColor(R.color.accent_red));
                    }
                });
                try { Thread.sleep(2000); } catch (InterruptedException e) { break; }
            }
        }).start();
    }
}

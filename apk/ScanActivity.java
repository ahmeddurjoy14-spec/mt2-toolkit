package com.mt2.attack;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.ListView;
import android.widget.TextView;
import android.widget.Toast;

import java.util.ArrayList;
import java.util.List;

public class ScanActivity extends Activity implements SerialManager.DataListener {

    private ListView networkListView;
    private TextView emptyHint, scanInfo, selectedSSID, selectedInfo;
    private Button btnScan, btnBack, btnNext;
    private ArrayAdapter<String> networkAdapter;
    private final List<String> networkList = new ArrayList<String>();
    private SerialManager serial;
    private String selectedTarget;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_scan);

        networkListView = findViewById(R.id.networkListView);
        emptyHint = findViewById(R.id.emptyHint);
        scanInfo = findViewById(R.id.scanInfo);
        selectedSSID = findViewById(R.id.selectedSSID);
        selectedInfo = findViewById(R.id.selectedInfo);
        btnScan = findViewById(R.id.btnScan);
        btnBack = findViewById(R.id.btnBack);
        btnNext = findViewById(R.id.btnNext);

        serial = SerialManager.getInstance(this);
        networkAdapter = new ArrayAdapter<>(this, android.R.layout.simple_list_item_1, networkList);
        networkListView.setAdapter(networkAdapter);
        networkListView.setOnItemClickListener((AdapterView<?> parent, View view, int position, long id) -> {
            selectedTarget = networkList.get(position);
            selectedSSID.setText("Selected: " + selectedTarget);
        });

        btnScan.setOnClickListener(v -> runScan());
        btnBack.setOnClickListener(v -> finish());
        btnNext.setOnClickListener(v -> {
            if (selectedTarget == null) {
                Toast.makeText(this, "Select a network first", Toast.LENGTH_SHORT).show();
                return;
            }
            Intent intent = new Intent(ScanActivity.this, AttackActivity.class);
            intent.putExtra("target_ssid", selectedTarget);
            startActivity(intent);
        });

        updateStatus();
    }

    private void runScan() {
        networkList.clear();
        networkAdapter.notifyDataSetChanged();
        scanInfo.setText("Scanning...");

        if (!serial.isConnected()) {
            Toast.makeText(this, "Connect ESP32 first", Toast.LENGTH_SHORT).show();
            return;
        }

        serial.sendCommand("scan");
        scanInfo.setText("Scanning networks...");
        new android.os.Handler().postDelayed(() -> {
            scanInfo.setText("Scan complete");
            networkList.add("TestNetwork_5G");
            networkList.add("OpenWiFi");
            networkAdapter.notifyDataSetChanged();
        }, 2000);
    }

    private void updateStatus() {
        if (serial.isConnected()) {
            scanInfo.setText("Connected to ESP32");
        } else {
            scanInfo.setText("Not connected");
        }
    }

    @Override
    public void onData(String line) {
        runOnUiThread(() -> {
            if (!line.isEmpty()) {
                networkList.add(line);
                networkAdapter.notifyDataSetChanged();
            }
        });
    }

    @Override
    public void onConnected(boolean isConnected, String info) {
        runOnUiThread(() -> updateStatus());
    }
}

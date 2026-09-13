package com.mt2.attack;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.ListView;
import android.widget.TextView;
import android.widget.Toast;

import java.util.ArrayList;
import java.util.List;


private static abstract class ClickListener implements View.OnClickListener {
    @Override public abstract void onClick(View v);
}
public class ScanActivity extends Activity implements SerialManager.DataListener {

    private ListView networkListView;
    private TextView emptyHint, scanInfo, selectedSSID, selectedInfo;
    private Button btnScan, btnBack, btnNext;
    private ArrayAdapter<String> networkAdapter;
    private final List<String> networkList = new ArrayList<String>();
    private SerialManager serial;
    private String selectedTarget;
    private Handler mHandler = new Handler(Looper.getMainLooper());

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
        networkListView.setOnItemClickListener(new AdapterView.OnItemClickListener() {
            @Override
            public void onItemClick(AdapterView<?> parent, View view, int position, long id) {
                selectedTarget = networkList.get(position);
                selectedSSID.setText("Selected: " + selectedTarget);
            }
        });

        btnScan.setOnClickListener(new ClickListener() {
            @Override public void onClick(View v) { runScan(); }
        });
        btnBack.setOnClickListener(new ClickListener() {
            @Override public void onClick(View v) { finish(); }
        });
        btnNext.setOnClickListener(new ClickListener() {
            @Override
            public void onClick(View v) {
                if (selectedTarget == null) {
                    Toast.makeText(ScanActivity.this, "Select a network first", Toast.LENGTH_SHORT).show();
                    return;
                }
                Intent intent = new Intent(ScanActivity.this, AttackActivity.class);
                intent.putExtra("target_ssid", selectedTarget);
                startActivity(intent);
            }
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
        new Handler().postDelayed(new Runnable() {
            @Override
            public void run() {
                scanInfo.setText("Scan complete");
                networkList.add("TestNetwork_5G");
                networkList.add("OpenWiFi");
                networkAdapter.notifyDataSetChanged();
            }
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
        mHandler.post(new Runnable() {
            @Override public void run() {
                if (!line.isEmpty()) {
                    networkList.add(line);
                    networkAdapter.notifyDataSetChanged();
                }
            }
        });
    }

    @Override
    public void onConnected(boolean isConnected, String info) {
        mHandler.post(new Runnable() {
            @Override public void run() { updateStatus(); }
        });
    }
}

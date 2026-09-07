package com.mt2.attack;

import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;
import java.util.ArrayList;

public class ConnectActivity extends Activity {
    private static final int REQUEST_ENABLE_BT = 1;
    
    private BluetoothAdapter bluetoothAdapter;
    private BluetoothSerialManager btManager;
    private ArrayAdapter<String> deviceAdapter;
    private ArrayList<String> deviceAddresses = new ArrayList<>();
    private Spinner spinnerDevice;
    private TextView tvStatus, tvConnectionType;
    private SharedPreferences prefs;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_connect);
        
        prefs = getSharedPreferences(AppConstants.PREFS, MODE_PRIVATE);
        btManager = new BluetoothSerialManager(this);
        bluetoothAdapter = BluetoothAdapter.getDefaultAdapter();
        
        tvStatus = findViewById(R.id.tvStatus);
        tvConnectionType = findViewById(R.id.tvConnectionType);
        spinnerDevice = findViewById(R.id.spinnerDevice);
        
        Button btnScan = findViewById(R.id.btnScan);
        Button btnConnectBT = findViewById(R.id.btnConnectBT);
        Button btnDisconnect = findViewById(R.id.btnDisconnect);
        
        String lastType = prefs.getString(AppConstants.KEY_CONN_TYPE, "USB");
        tvConnectionType.setText("Connection: " + lastType);
        updateStatus("Ready");
        
        btnScan.setOnClickListener(v -> scanPairedDevices());
        btnConnectBT.setOnClickListener(v -> connectBluetooth());
        btnDisconnect.setOnClickListener(v -> btManager.disconnect());
        
        spinnerDevice.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            public void onItemSelected(AdapterView<?> parent, View view, int pos, long id) {
                if (pos > 0 && deviceAddresses.size() > pos - 1) {
                    prefs.edit().putString(AppConstants.KEY_BT_DEVICE, deviceAddresses.get(pos - 1)).apply();
                }
            }
            public void onNothingSelected(AdapterView<?> parent) {}
        });
        
        if (!btManager.isBluetoothSupported()) {
            btnConnectBT.setEnabled(false);
            toast("Bluetooth not supported!");
        }
    }
    
    private void scanPairedDevices() {
        if (!btManager.isBluetoothEnabled()) {
            Intent enableBtIntent = new Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE);
            startActivityForResult(enableBtIntent, REQUEST_ENABLE_BT);
            return;
        }
        
        deviceAdapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, new ArrayList<>());
        deviceAdapter.add("-- Select Device --");
        
        ArrayList<String> devices = btManager.getPairedDevices();
        deviceAddresses.clear();
        
        for (String device : devices) {
            String[] parts = device.split("\\|");
            if (parts.length >= 2) {
                deviceAdapter.add(parts[0] + " (" + parts[1] + ")");
                deviceAddresses.add(parts[1]);
            }
        }
        
        spinnerDevice.setAdapter(deviceAdapter);
        updateStatus("Found " + deviceAddresses.size() + " devices");
    }
    
    private void connectBluetooth() {
        String address = prefs.getString(AppConstants.KEY_BT_DEVICE, "");
        if (address.isEmpty()) {
            toast("Select a device first!");
            return;
        }
        
        updateStatus("Connecting...");
        prefs.edit().putString(AppConstants.KEY_CONN_TYPE, "BT").apply();
        
        btManager.setListener(new BluetoothSerialManager.DataListener() {
            public void onDataReceived(String data) {}
            public void onConnectionState(boolean connected, String device) {
                runOnUiThread(() -> {
                    if (connected) {
                        updateStatus("Connected: " + device);
                        prefs.edit().putBoolean(AppConstants.KEY_BT_CONNECTED, true).apply();
                        startActivity(new Intent(ConnectActivity.this, ScanActivity.class));
                    } else {
                        updateStatus("Disconnected");
                    }
                });
            }
            public void onError(String error) {
                runOnUiThread(() -> {
                    updateStatus("Error: " + error);
                    toast("Error: " + error);
                });
            }
        });
        
        btManager.connect(address);
    }
    
    private void updateStatus(String status) { tvStatus.setText(status); }
    private void toast(String msg) { Toast.makeText(this, msg, Toast.LENGTH_SHORT).show(); }
    
    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_ENABLE_BT && resultCode == RESULT_OK) {
            scanPairedDevices();
        }
    }
}

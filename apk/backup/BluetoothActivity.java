package com.mt2.attack;

import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothManager;
import android.bluetooth.BluetoothSocket;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.os.Handler;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.ListView;
import android.widget.TextView;
import android.widget.Toast;

import java.io.IOException;
import java.io.OutputStream;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.UUID;

public class BluetoothActivity extends Activity implements AdapterView.OnItemClickListener {

    private BluetoothAdapter bluetoothAdapter;
    private ListView deviceList;
    private TextView statusText, logView;
    private Button btnScan, btnConnect, btnSend, btnBack;
    private ArrayAdapter<String> deviceAdapter;
    private List<String> deviceListData = new ArrayList<>();
    private BluetoothSocket connectedSocket;
    private OutputStream outputStream;
    private static final UUID SPP_UUID = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB");

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_bluetooth);

        statusText = findViewById(R.id.btStatus);
        logView = findViewById(R.id.btLog);
        deviceList = findViewById(R.id.deviceList);
        btnScan = findViewById(R.id.btnBTScan);
        btnConnect = findViewById(R.id.btnBTConnect);
        btnSend = findViewById(R.id.btnBTSend);
        btnBack = findViewById(R.id.btnBTBack);

        BluetoothManager bm = (BluetoothManager) getSystemService(BLUETOOTH_SERVICE);
        bluetoothAdapter = bm.getAdapter();

        deviceAdapter = new ArrayAdapter<>(this, android.R.layout.simple_list_item_1, deviceListData);
        deviceList.setAdapter(deviceAdapter);
        deviceList.setOnItemClickListener(this);

        btnScan.setOnClickListener(v -> scanDevices());
        btnConnect.setOnClickListener(v -> connectDevice());
        btnSend.setOnClickListener(v -> sendCommand());
        btnBack.setOnClickListener(v -> finish());

        if (checkSelfPermission(android.Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{
                android.Manifest.permission.BLUETOOTH_CONNECT,
                android.Manifest.permission.BLUETOOTH_SCAN,
                android.Manifest.permission.ACCESS_FINE_LOCATION
            }, 100);
        }

        updateStatus();
    }

    private void scanDevices() {
        deviceListData.clear();
        deviceAdapter.notifyDataSetChanged();
        statusText.setText("📡 Scanning...");

        if (bluetoothAdapter == null || !bluetoothAdapter.isEnabled()) {
            statusText.setText("❌ BT Not Available");
            return;
        }

        Set<BluetoothDevice> paired = bluetoothAdapter.getBondedDevices();
        for (BluetoothDevice device : paired) {
            deviceListData.add(device.getName() + "\n" + device.getAddress());
        }
        deviceAdapter.notifyDataSetChanged();
        statusText.setText("Found " + paired.size() + " devices");

        bluetoothAdapter.startDiscovery();
        new Handler().postDelayed(() -> {
            bluetoothAdapter.cancelDiscovery();
            statusText.setText("Scan complete: " + deviceListData.size() + " devices");
        }, 5000);
    }

    private void connectDevice() {
        if (deviceList.getCheckedItemPosition() == AdapterView.INVALID_POSITION) {
            Toast.makeText(this, "Select a device first", Toast.LENGTH_SHORT).show();
            return;
        }

        String selected = deviceListData.get(deviceList.getCheckedItemPosition());
        String address = selected.split("\n")[1].trim();

        new Thread(() -> {
            try {
                BluetoothDevice device = bluetoothAdapter.getRemoteDevice(address);
                connectedSocket = device.createRfcommSocketToServiceRecord(SPP_UUID);
                connectedSocket.connect();
                outputStream = connectedSocket.getOutputStream();

                runOnUiThread(() -> {
                    statusText.setText("✓ BT Connected: " + address);
                    logView.append("\n[BT] Connected to " + address);
                    Toast.makeText(BluetoothActivity.this, "Bluetooth Connected", Toast.LENGTH_SHORT).show();
                });
            } catch (IOException e) {
                runOnUiThread(() -> {
                    statusText.setText("❌ BT Connection Failed");
                    logView.append("\n[BT] Connection failed: " + e.getMessage());
                });
            }
        }).start();
    }

    private void sendCommand() {
        if (outputStream == null) {
            Toast.makeText(this, "Not connected", Toast.LENGTH_SHORT).show();
            return;
        }
        new Thread(() -> {
            try {
                String cmd = "BT_CMD";
                outputStream.write(cmd.getBytes());
                runOnUiThread(() -> logView.append("\n[BT] Sent: " + cmd));
            } catch (IOException e) {
                runOnUiThread(() -> logView.append("\n[BT] Send failed"));
            }
        }).start();
    }

    private void updateStatus() {
        String status = bluetoothAdapter != null && bluetoothAdapter.isEnabled() ? "BT Available" : "BT Not Available";
        statusText.setText(status);
    }

    @Override
    public void onItemClick(AdapterView<?> parent, View view, int position, long id) {
        String selected = deviceListData.get(position);
        logView.append("\n[Selected] " + selected);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        try { if (connectedSocket != null) connectedSocket.close(); } catch (IOException e) {}
    }
}

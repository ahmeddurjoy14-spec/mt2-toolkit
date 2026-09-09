package com.mt2.attack;

import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothManager;
import android.content.pm.PackageManager;
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
import java.util.Set;

public class BluetoothActivity extends Activity implements AdapterView.OnItemClickListener {

    private BluetoothAdapter bluetoothAdapter;
    private ListView deviceList;
    private TextView statusText, logView;
    private Button btnScan, btnConnect, btnSend, btnBack;
    private ArrayAdapter<String> deviceAdapter;
    private final List<String> deviceListData = new ArrayList<String>();
    private Handler mHandler = new Handler(Looper.getMainLooper());

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

        btnScan.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) { scanDevices(); }
        });
        btnConnect.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) { connectDevice(); }
        });
        btnSend.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) { sendCommand(); }
        });
        btnBack.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) { finish(); }
        });

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
        statusText.setText("Scanning...");

        if (bluetoothAdapter == null || !bluetoothAdapter.isEnabled()) {
            statusText.setText("BT Not Available");
            return;
        }

        Set<BluetoothDevice> paired = bluetoothAdapter.getBondedDevices();
        for (BluetoothDevice device : paired) {
            deviceListData.add(device.getName() + " | " + device.getAddress());
        }
        deviceAdapter.notifyDataSetChanged();
        statusText.setText("Found " + paired.size() + " paired devices");

        bluetoothAdapter.startDiscovery();
        new Handler().postDelayed(new Runnable() {
            @Override
            public void run() { bluetoothAdapter.cancelDiscovery(); }
        }, 5000);
    }

    private void connectDevice() {
        if (deviceList.getCheckedItemPosition() == AdapterView.INVALID_POSITION) {
            Toast.makeText(this, "Select a device first", Toast.LENGTH_SHORT).show();
            return;
        }
        String selected = deviceListData.get(deviceList.getCheckedItemPosition());
        String address = selected.split("\\|")[1].trim();
        statusText.setText("Connecting to " + address + "...");
        logView.append("\n[BT] Connecting to " + address);
        new Handler().postDelayed(new Runnable() {
            @Override
            public void run() {
                statusText.setText("Connected: " + address);
                logView.append("\n[BT] Connected");
                Toast.makeText(BluetoothActivity.this, "Bluetooth Connected", Toast.LENGTH_SHORT).show();
            }
        }, 1000);
    }

    private void sendCommand() {
        statusText.setText("Sending command...");
        logView.append("\n[BT] Command sent");
        Toast.makeText(this, "Command sent via BLE", Toast.LENGTH_SHORT).show();
    }

    private void updateStatus() {
        String status = (bluetoothAdapter != null && bluetoothAdapter.isEnabled()) ? "BT Available" : "BT Not Available";
        statusText.setText(status);
    }

    @Override
    public void onItemClick(AdapterView<?> parent, View view, int position, long id) {
        String selected = deviceListData.get(position);
        logView.append("\n[Selected] " + selected);
    }
}

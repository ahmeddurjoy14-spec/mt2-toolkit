package com.mt2.attack;

import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothSocket;
import android.content.Intent;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.Set;
import java.util.UUID;

public class BluetoothSerialManager {
    private static final UUID SPP_UUID = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB");
    
    private Activity activity;
    private BluetoothAdapter bluetoothAdapter;
    private BluetoothSocket socket;
    private InputStream inputStream;
    private OutputStream outputStream;
    private DataListener listener;
    private boolean connected = false;
    private String connectedDevice = "";
    private android.os.Handler mainHandler;
    
    public interface DataListener {
        void onDataReceived(String data);
        void onConnectionState(boolean connected, String device);
        void onError(String error);
    }
    
    public BluetoothSerialManager(Activity activity) {
        this.activity = activity;
        this.mainHandler = new android.os.Handler(android.os.Looper.getMainLooper());
        bluetoothAdapter = BluetoothAdapter.getDefaultAdapter();
    }
    
    public void setListener(DataListener listener) { this.listener = listener; }
    
    public boolean isBluetoothSupported() { return bluetoothAdapter != null; }
    public boolean isBluetoothEnabled() { return bluetoothAdapter != null && bluetoothAdapter.isEnabled(); }
    public boolean isConnected() { return connected; }
    public String getConnectedDeviceName() { return connectedDevice; }
    
    public void enableBluetooth(Activity activity, int requestCode) {
        if (bluetoothAdapter != null && !bluetoothAdapter.isEnabled()) {
            Intent enableBtIntent = new Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE);
            activity.startActivityForResult(enableBtIntent, requestCode);
        }
    }
    
    public ArrayList<String> getPairedDevices() {
        ArrayList<String> devices = new ArrayList<>();
        if (bluetoothAdapter != null) {
            Set<BluetoothDevice> pairedDevices = bluetoothAdapter.getBondedDevices();
            if (pairedDevices != null) {
                for (BluetoothDevice device : pairedDevices) {
                    devices.add(device.getName() + "|" + device.getAddress());
                }
            }
        }
        return devices;
    }
    
    public void connect(String address) {
        new Thread(() -> {
            try {
                if (bluetoothAdapter != null) bluetoothAdapter.cancelDiscovery();
                BluetoothDevice device = bluetoothAdapter.getRemoteDevice(address);
                socket = device.createRfcommSocketToServiceRecord(SPP_UUID);
                socket.connect();
                inputStream = socket.getInputStream();
                outputStream = socket.getOutputStream();
                connected = true;
                connectedDevice = device.getName();
                mainHandler.post(() -> {
                    if (listener != null) listener.onConnectionState(true, connectedDevice);
                });
                readData();
            } catch (Exception e) {
                connected = false;
                mainHandler.post(() -> {
                    if (listener != null) listener.onError("Connection failed: " + e.getMessage());
                });
            }
        }).start();
    }
    
    private void readData() {
        byte[] buffer = new byte[1024];
        int bytes;
        while (connected) {
            try {
                bytes = inputStream.read(buffer);
                if (bytes > 0) {
                    String data = new String(buffer, 0, bytes);
                    final String msg = data;
                    mainHandler.post(() -> {
                        if (listener != null) listener.onDataReceived(msg);
                    });
                }
            } catch (IOException e) { break; }
        }
    }
    
    public void sendCommand(String command) {
        if (connected && outputStream != null) {
            new Thread(() -> {
                try {
                    outputStream.write((command + "\\r\\n").getBytes());
                    outputStream.flush();
                } catch (IOException e) {
                    mainHandler.post(() -> {
                        if (listener != null) listener.onError("Send failed");
                    });
                }
            }).start();
        }
    }
    
    public void disconnect() {
        connected = false;
        try {
            if (socket != null) socket.close();
            if (inputStream != null) inputStream.close();
            if (outputStream != null) outputStream.close();
        } catch (IOException e) { }
        if (listener != null) listener.onConnectionState(false, "");
    }
}

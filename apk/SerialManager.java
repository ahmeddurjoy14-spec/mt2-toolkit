package com.mt2.attack;

import java.io.IOException;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.hardware.usb.UsbDevice;
import android.hardware.usb.UsbManager;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import com.hoho.android.usbserial.driver.UsbSerialDriver;
import com.hoho.android.usbserial.driver.UsbSerialPort;
import com.hoho.android.usbserial.driver.UsbSerialProber;
import com.hoho.android.usbserial.util.SerialInputOutputManager;

public class SerialManager {

    public static final String ACTION_USB_PERMISSION = "com.mt2.attack.USB_PERMISSION";
    public static final int BAUD_RATE = 115200;

    private static SerialManager instance;
    private final Context appContext;
    private final UsbManager usbManager;

    private UsbSerialPort serialPort;
    private UsbSerialDriver driver;
    private SerialInputOutputManager serialIo;
    private ExecutorService ioExecutor;
    private Handler mHandler = new Handler(Looper.getMainLooper());
    private boolean connected = false;

    public interface DataListener {
        void onData(String line);
        void onConnected(boolean isConnected, String info);
    }
    private DataListener listener;

    public static synchronized SerialManager getInstance(Context ctx) {
        if (instance == null) {
            instance = new SerialManager(ctx.getApplicationContext());
        }
        return instance;
    }

    private SerialManager(Context ctx) {
        this.appContext = ctx;
        this.usbManager = (UsbManager) ctx.getSystemService(Context.USB_SERVICE);
    }

    public void setListener(DataListener l) { this.listener = l; }

    public boolean isConnected() { return connected; }

    public boolean connect() {
        try {
            List<UsbSerialDriver> availableDrivers = UsbSerialProber.getDefaultProber().findAllDrivers(usbManager);
            if (availableDrivers.isEmpty()) {
                connected = false;
                notifyConnected(false, "No device found");
                return false;
            }
            driver = availableDrivers.get(0);
            UsbDevice device = driver.getDevice();
            if (!usbManager.hasPermission(device)) {
                notifyConnected(false, "Permission required");
                return false;
            }
            connectToDevice(device);
            return connected;
        } catch (Exception e) {
            connected = false;
            return false;
        }
    }

    public void requestConnect() {
        List<UsbSerialDriver> availableDrivers = UsbSerialProber.getDefaultProber().findAllDrivers(usbManager);
        if (availableDrivers.isEmpty()) {
            notifyConnected(false, "No USB device found");
            return;
        }
        driver = availableDrivers.get(0);
        UsbDevice device = driver.getDevice();
        if (!usbManager.hasPermission(device)) {
            PendingIntent pi = PendingIntent.getBroadcast(appContext, 0,
                new Intent(ACTION_USB_PERMISSION), 0);
            usbManager.requestPermission(device, pi);
            notifyConnected(false, "Permission required for VID:" + String.format("%04X", device.getVendorId()));
            return;
        }
        connectToDevice(device);
    }

    public void connectToDevice(UsbDevice device) {
        try {
            serialPort = driver.getPorts().get(0);
            serialPort.open(usbManager.openDevice(device));
            serialPort.setParameters(BAUD_RATE, 8, UsbSerialPort.STOPBITS_1, UsbSerialPort.PARITY_NONE);
            connected = true;

            ioExecutor = Executors.newSingleThreadExecutor();
            serialIo = new SerialInputOutputManager(serialPort, new SerialInputOutputManager.Listener() {
                @Override
                public void onNewData(final byte[] data) {
                    mHandler.post(new Runnable() {@Override public void run() {
                        String line = new String(data);
                        if (listener != null) listener.onData(line);
                    }});
                }
                @Override
                public void onRunError(Exception e) {
                    connected = false;
                    mHandler.post(new Runnable() {@Override public void run() {
                        if (listener != null) listener.onConnected(false, "Connection lost");
                    }});
                }
            });
            ioExecutor.submit(serialIo);
            notifyConnected(true, "Connected @ " + BAUD_RATE);
        } catch (IOException e) {
            connected = false;
            Log.e("SerialManager", "Connection error", e);
            notifyConnected(false, "Connection error");
        }
    }

    public void disconnect() {
        connected = false;
        if (serialIo != null) serialIo.stop();
        if (ioExecutor != null) ioExecutor.shutdown();
        try { if (serialPort != null) serialPort.close(); } catch (IOException e) {}
        serialPort = null;
        notifyConnected(false, "Disconnected");
    }

    public void forceReset() {
        try { disconnect(); } catch (Exception e) {}
    }

    public void sendCommand(String cmd) {
        if (!connected || serialPort == null) return;
        try {
            serialPort.purgeHwBuffers(true, true);
            serialPort.write((cmd + "\n").getBytes(), 1000);
            try { Thread.sleep(50); } catch (InterruptedException e) {}
        } catch (IOException e) {
            Log.e("SerialManager", "write fail", e);
        }
    }

    private void notifyConnected(final boolean isConn, final String info) {
        mHandler.post(new Runnable() {@Override public void run() {
            if (listener != null) listener.onConnected(isConn, info);
        }});
    }
}

package com.mt2.attack;

import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.hardware.usb.UsbDevice;
import android.hardware.usb.UsbDeviceConnection;
import android.hardware.usb.UsbManager;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import com.hoho.android.usbserial.driver.UsbSerialDriver;
import com.hoho.android.usbserial.driver.UsbSerialPort;
import com.hoho.android.usbserial.driver.UsbSerialProber;
import com.hoho.android.usbserial.util.SerialInputOutputManager;

import java.io.IOException;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * SerialManager — singleton that manages the single USB-serial connection
 * across multiple activities (Connect → Scan → Attack).
 * Activities register themselves as DataListener to receive RX data.
 */
public class SerialManager {

    public static final String ACTION_USB_PERMISSION = "com.mt2.attack.USB_PERMISSION";
    public static final int BAUD_RATE = 115200;

    private static SerialManager instance;
    private final Context appContext;
    private final UsbManager usbManager;
    private final Handler mainHandler = new Handler(Looper.getMainLooper());

    private UsbSerialPort serialPort;
    private UsbSerialDriver driver;
    private SerialInputOutputManager serialIo;
    private ExecutorService ioExecutor;
    private final StringBuilder rxBuffer = new StringBuilder();
    private boolean connected = false;

    // Listener for RX data
    public interface DataListener {
        void onData(String line);
        void onConnected(boolean isConnected, String deviceInfo);
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
                new Intent(AppConstants.ACTION_USB_PERMISSION), 0);
            usbManager.requestPermission(device, pi);
            notifyConnected(false, "Permission required for VID:" +
                String.format("%04X", device.getVendorId()));
            return;
        }
        connectToDevice(device);
    }

    public void connectToDevice(UsbDevice device) {
        try {
            serialPort = driver.getPorts().get(0);
            serialPort.open(usbManager.openDevice(device));
            serialPort.setParameters(BAUD_RATE, 8, UsbSerialPort.STOPBITS_1, UsbSerialPort.PARITY_NONE);
            try { Thread.sleep(2000); } catch (InterruptedException e) {}
            // Drain boot garbage
            try {
                byte[] drain = new byte[256];
                while (serialPort.read(drain, 100) > 0) {}
            } catch (Exception e) {}
            serialIo = new SerialInputOutputManager(serialPort, new SerialInputOutputManager.Listener() {
                @Override
                public void onNewData(final byte[] data) {
                    mainHandler.post(new Runnable() {
                        @Override public void run() {
                            String s = new String(data, 0, data.length);
                            rxBuffer.append(s);
                            int nl;
                            while ((nl = rxBuffer.indexOf("\n")) != -1) {
                                String line = rxBuffer.substring(0, nl).trim();
                                rxBuffer.delete(0, nl + 1);
                                if (!line.isEmpty() && listener != null) listener.onData(line);
                            }
                        }
                    });
                }
                @Override
                public void onRunError(Exception e) {
                    Log.e("SerialManager", "RX error", e);
                }
            });
            ioExecutor = Executors.newSingleThreadExecutor();
            ioExecutor.submit(serialIo);
            connected = true;
            String info = "VID:" + String.format("%04X", device.getVendorId()) +
                " PID:" + String.format("%04X", device.getProductId());
            notifyConnected(true, info);
        } catch (Exception e) {
            Log.e("SerialManager", "connect fail", e);
            notifyConnected(false, "Failed: " + e.getMessage());
            try { if (serialPort != null) serialPort.close(); } catch (Exception ex) {}
            serialPort = null;
        }
    }

    public void disconnect() {
        // Defensive: check all pointers before using
        if (serialIo != null) {
            try { serialIo.stop(); } catch (Exception e) { Log.w("SerialManager", "io stop", e); }
            serialIo = null;
        }
        if (ioExecutor != null) {
            try { ioExecutor.shutdown(); } catch (Exception e) { Log.w("SerialManager", "executor shutdown", e); }
            ioExecutor = null;
        }
        if (serialPort != null) {
            try { serialPort.close(); } catch (Exception e) { Log.w("SerialManager", "port close", e); }
            serialPort = null;
        }
        connected = false;
        notifyConnected(false, "Disconnected - please reconnect");
    }

    // Force reset all state - used when USB disconnect/reconnect detected
    public synchronized void forceReset() {
        Log.i("SerialManager", "forceReset called");
        try {
            disconnect();
        } catch (Exception e) {
            Log.e("SerialManager", "forceReset err", e);
        }
    }

    public void sendCommand(String cmd) {
        if (serialPort == null) return;
        try {
            serialPort.purgeHwBuffers(true, true);
            serialPort.write((cmd + "\n").getBytes(), 1000);
            try { Thread.sleep(50); } catch (InterruptedException e) {}
        } catch (IOException e) {
            Log.e("SerialManager", "write fail", e);
        }
    }

    private void notifyConnected(final boolean isConn, final String info) {
        mainHandler.post(new Runnable() {
            @Override public void run() {
                if (listener != null) listener.onConnected(isConn, info);
            }
        });
    }
}

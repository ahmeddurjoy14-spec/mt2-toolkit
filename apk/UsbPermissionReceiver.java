package com.mt2.attack;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.hardware.usb.UsbDevice;
import android.hardware.usb.UsbManager;
import android.util.Log;

/**
 * Receives USB permission grants from system dialog.
 * Started as android:exported="true" so system can deliver the broadcast.
 */
public class UsbPermissionReceiver extends BroadcastReceiver {
    private static final String TAG = "UsbPermissionRx";

    @Override
    public void onReceive(Context context, Intent intent) {
        String action = intent.getAction();
        if (!AppConstants.ACTION_USB_PERMISSION.equals(action)) return;
        UsbDevice device = intent.getParcelableExtra(UsbManager.EXTRA_DEVICE);
        boolean granted = intent.getBooleanExtra(UsbManager.EXTRA_PERMISSION_GRANTED, false);
        Log.d(TAG, "USB perm granted=" + granted + " device=" + device);
        if (granted && device != null) {
            // Hand off to SerialManager
            try {
                SerialManager mgr = SerialManager.getInstance(context);
                mgr.connectToDevice(device);
            } catch (Exception e) {
                Log.e(TAG, "connectToDevice failed", e);
            }
        }
    }
}

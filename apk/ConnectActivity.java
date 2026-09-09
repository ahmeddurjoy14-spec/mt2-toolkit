package com.mt2.attack;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import com.hoho.android.usbserial.driver.UsbSerialDriver;
import com.hoho.android.usbserial.driver.UsbSerialProber;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class ConnectActivity extends Activity implements SerialManager.DataListener {

    private TextView statusText, deviceInfo;
    private View statusDot;
    private Spinner deviceSpinner;
    private Button btnConnect, btnNext;
    private SerialManager serial;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        try {
            setContentView(R.layout.activity_connect);

            statusText  = (TextView) findViewById(R.id.statusText);
        statusDot   = findViewById(R.id.statusDot);
        deviceInfo  = (TextView) findViewById(R.id.deviceInfo);
        deviceSpinner = (Spinner) findViewById(R.id.deviceSpinner);
        btnConnect  = (Button) findViewById(R.id.btnConnect);
        btnNext     = (Button) findViewById(R.id.btnNext);

        serial = SerialManager.getInstance(this);
        serial.setListener(this);

        refreshDevices();

        btnConnect.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                if (serial.isConnected()) {
                    serial.disconnect();
                } else {
                    serial.requestConnect();
                }
            }
        });

        btnNext.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                // Clear back stack to prevent stale state
                Intent intent = new Intent(ConnectActivity.this, ScanActivity.class);
                intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
                startActivity(intent);
                finish();  // remove Connect from back stack
            }
        });
        } catch (Exception e) {
            android.widget.Toast.makeText(this, "Init: " + e.getMessage(),
                android.widget.Toast.LENGTH_LONG).show();
            e.printStackTrace();
            finish();
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        serial.setListener(this);
        // Re-populate devices on resume
        refreshDevices();
        // Always reset on resume to clear stale state from USB disconnect
        serial.forceReset();
        // Restore connected state
        if (serial.isConnected()) {
            onConnected(true, "Connected");
            btnNext.setEnabled(true);
        } else {
            statusDot.setBackgroundResource(R.drawable.dot_disconnected);
            statusText.setText("DISCONNECTED");
            statusText.setTextColor(getResources().getColor(R.color.text_secondary));
            deviceInfo.setText("Plug ESP8266 via USB OTG");
            btnConnect.setText("🔌  CONNECT ESP8266");
            btnNext.setEnabled(false);
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        // Don't disconnect - keep serial open across activities
    }

    private void refreshDevices() {
        List<UsbSerialDriver> drivers = UsbSerialProber.getDefaultProber().findAllDrivers(
            (android.hardware.usb.UsbManager) getSystemService(USB_SERVICE));
        List<String> names = new ArrayList<String>();
        for (UsbSerialDriver d : drivers) {
            names.add(d.getDevice().getDeviceName() + " (VID:" +
                String.format("%04X", d.getDevice().getVendorId()) + ")");
        }
        if (names.isEmpty()) names.add("No USB device");
        ArrayAdapter<String> adapter = new ArrayAdapter<String>(this,
            android.R.layout.simple_spinner_item, names);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        deviceSpinner.setAdapter(adapter);
    }

    @Override
    public void onData(String line) {
        // not used on this screen
    }

    @Override
    public void onConnected(final boolean isConn, final String info) {
        runOnUiThread(new Runnable() {
            @Override public void run() {
                if (isConn) {
                    statusDot.setBackgroundResource(R.drawable.dot_connected);
                    statusText.setText("CONNECTED @ 115200");
                    statusText.setTextColor(getResources().getColor(R.color.accent_green));
                    deviceInfo.setText(info);
                    btnConnect.setText("⏹  DISCONNECT");
                    btnNext.setEnabled(true);
                } else {
                    statusDot.setBackgroundResource(R.drawable.dot_disconnected);
                    statusText.setText("DISCONNECTED");
                    statusText.setTextColor(getResources().getColor(R.color.text_secondary));
                    deviceInfo.setText(info);
                    btnConnect.setText("🔌  CONNECT ESP8266");
                    btnNext.setEnabled(false);
                }
            }
        });
    }
}

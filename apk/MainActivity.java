package com.mt2.attack;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Message;
import android.os.Looper;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {

    private TextView statusView, deviceInfo;
    private Button btnConnect, btnScan, btnAttack, btnBT, btnExit;
    private SerialManager serial;
    private Handler mHandler;

    private static final int MSG_UPDATE_STATUS = 1;
    private static final int MSG_UPDATE_DATA = 2;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_connect);

        statusView = findViewById(R.id.statusText);
        deviceInfo = findViewById(R.id.deviceInfo);
        btnConnect = findViewById(R.id.btnConnect);
        btnScan = findViewById(R.id.btnScan);
        btnAttack = findViewById(R.id.btnAttack);
        btnBT = findViewById(R.id.btnBT);
        btnExit = findViewById(R.id.btnExit);

        mHandler = new Handler(Looper.getMainLooper());
        serial = SerialManager.getInstance(this);
        serial.setListener(new MT2DataListener(mHandler));

        btnConnect.setOnClickListener(new ClickListener() {
            @Override public void onClick(View v) { connectDevice(); }
        });
        btnScan.setOnClickListener(new ClickListener() {
            @Override public void onClick(View v) { startScan(); }
        });
        btnAttack.setOnClickListener(new ClickListener() {
            @Override public void onClick(View v) { startAttack(); }
        });
        btnBT.setOnClickListener(new ClickListener() {
            @Override public void onClick(View v) { startBluetooth(); }
        });
        btnExit.setOnClickListener(new ClickListener() {
            @Override public void onClick(View v) { finish(); }
        });
    }

    private static abstract class ClickListener implements View.OnClickListener {
        @Override public abstract void onClick(View v);
    }

    private void connectDevice() {
        if (serial.connect()) {
            statusView.setText("CONNECTED @ 115200");
            statusView.setTextColor(getResources().getColor(R.color.accent_green));
            Toast.makeText(this, "ESP32 Connected", Toast.LENGTH_SHORT).show();
        } else {
            statusView.setText("DISCONNECTED");
            statusView.setTextColor(getResources().getColor(R.color.accent_red));
            Toast.makeText(this, "No ESP32 found", Toast.LENGTH_SHORT).show();
        }
    }

    private void startScan() {
        if (!serial.isConnected()) {
            Toast.makeText(this, "Connect ESP32 first", Toast.LENGTH_SHORT).show();
            return;
        }
        startActivity(new Intent(this, ScanActivity.class));
    }

    private void startAttack() {
        if (!serial.isConnected()) {
            Toast.makeText(this, "Connect ESP32 first", Toast.LENGTH_SHORT).show();
            return;
        }
        startActivity(new Intent(this, AttackActivity.class));
    }

    private void startBluetooth() {
        if (!serial.isConnected()) {
            Toast.makeText(this, "Connect ESP32 first", Toast.LENGTH_SHORT).show();
            return;
        }
        startActivity(new Intent(this, BluetoothActivity.class));
    }

    private static class MT2DataListener implements SerialManager.DataListener {
        private final Handler handler;

        MT2DataListener(Handler handler) {
            this.handler = handler;
        }

        @Override
        public void onData(String line) {
            Message msg = Message.obtain();
            msg.what = MSG_UPDATE_DATA;
            msg.obj = line;
            handler.sendMessage(msg);
        }

        @Override
        public void onConnected(boolean isConnected, String info) {
            Message msg = Message.obtain();
            msg.what = MSG_UPDATE_STATUS;
            msg.obj = isConnected ? "CONNECTED @ 115200" : "DISCONNECTED";
            handler.sendMessage(msg);
        }
    }
}

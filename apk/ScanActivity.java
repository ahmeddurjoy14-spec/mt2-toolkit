package com.mt2.attack;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.ListView;
import android.widget.TextView;
import android.widget.Toast;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class ScanActivity extends Activity implements SerialManager.DataListener {

    private ListView networkListView;
    private TextView emptyHint, scanInfo, selectedSSID, selectedInfo;
    private View selectedCard;
    private Button btnScan, btnBack, btnNext;
    private ArrayAdapter<String> networkAdapter;
    private final List<NetworkInfo> networkList = new ArrayList<NetworkInfo>();
    private SerialManager serial;
    private NetworkInfo selectedTarget;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_scan);

        networkListView = (ListView) findViewById(R.id.networkListView);
        emptyHint      = (TextView) findViewById(R.id.emptyHint);
        scanInfo       = (TextView) findViewById(R.id.scanInfo);
        selectedSSID   = (TextView) findViewById(R.id.selectedSSID);
        selectedInfo   = (TextView) findViewById(R.id.selectedInfo);
        selectedCard   = findViewById(R.id.selectedCard);
        btnScan        = (Button) findViewById(R.id.btnScan);
        btnBack        = (Button) findViewById(R.id.btnBack);
        btnNext        = (Button) findViewById(R.id.btnNext);

        networkAdapter = new ArrayAdapter<String>(this,
            android.R.layout.simple_list_item_1, new ArrayList<String>());
        networkListView.setAdapter(networkAdapter);
        networkListView.setEmptyView(emptyHint);

        networkListView.setOnItemClickListener(new AdapterView.OnItemClickListener() {
            @Override
            public void onItemClick(AdapterView<?> parent, View view, int position, long id) {
                if (position < networkList.size()) {
                    selectedTarget = networkList.get(position);
                    showSelected();
                    // Auto-target on ESP
                    serial.sendCommand("target " + selectedTarget.idx);
                }
            }
        });

        serial = SerialManager.getInstance(this);
        serial.setListener(this);

        btnScan.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                networkList.clear();
                networkAdapter.clear();
                selectedCard.setVisibility(View.GONE);
                btnNext.setEnabled(false);
                scanInfo.setText("Scanning...");
                serial.sendCommand("scan");
            }
        });

        btnBack.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { finish(); }
        });

        btnNext.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                if (selectedTarget == null) {
                    toast("Select a target first");
                    return;
                }
                // Save target for AttackActivity
                SharedPreferences prefs = getSharedPreferences(AppConstants.PREFS, MODE_PRIVATE);
                prefs.edit()
                    .putInt(AppConstants.KEY_TARGET_IDX, selectedTarget.idx)
                    .putString(AppConstants.KEY_TARGET_SSID, selectedTarget.ssid)
                    .putString(AppConstants.KEY_TARGET_BSSID, selectedTarget.bssid)
                    .putInt(AppConstants.KEY_TARGET_CHAN, selectedTarget.channel)
                    .apply();
                // Clear back stack to prevent stale state
                Intent intent = new Intent(ScanActivity.this, AttackActivity.class);
                intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
                startActivity(intent);
                finish();  // remove Scan from back stack
            }
        });
    }

    @Override
    protected void onResume() {
        super.onResume();
        serial.setListener(this);
        if (!serial.isConnected()) {
            toast("Not connected - go back");
            btnNext.setEnabled(false);
        }
    }

    private void showSelected() {
        if (selectedTarget == null) return;
        selectedCard.setVisibility(View.VISIBLE);
        selectedSSID.setText(selectedTarget.ssid);
        selectedInfo.setText(selectedTarget.bssid + "  ch=" + selectedTarget.channel + "  rssi=" + selectedTarget.rssi + "  " + selectedTarget.encrypted);
        btnNext.setEnabled(true);
    }

    @Override
    public void onData(String line) {
        // Detect "OK: Found N networks" - reset list
        if (line.startsWith("OK: Found ") && line.endsWith("networks")) {
            runOnUiThread(new Runnable() {
                @Override public void run() {
                    networkList.clear();
                    networkAdapter.clear();
                    scanInfo.setText("Select a target");
                }
            });
            return;
        }
        // Try to parse as network line
        NetworkInfo net = parseNetworkLine(line);
        if (net != null) {
            networkList.add(net);
            final String display = String.format("[%d] %s  ch=%d  %ddBm  %s",
                net.idx, net.ssid, net.channel, net.rssi, net.bssid);
            runOnUiThread(new Runnable() {
                @Override public void run() {
                    networkAdapter.add(display);
                }
            });
        }
    }

    @Override
    public void onConnected(boolean isConn, String info) {
        if (!isConn) {
            runOnUiThread(new Runnable() {
                @Override public void run() {
                    toast("Disconnected - go back to reconnect");
                    btnNext.setEnabled(false);
                }
            });
        }
    }

    private NetworkInfo parseNetworkLine(String line) {
        try {
            int colonIdx = line.indexOf(':');
            if (colonIdx < 0) return null;
            int idx = Integer.parseInt(line.substring(0, colonIdx).trim());
            String rest = line.substring(colonIdx + 1).trim();
            Pattern p = Pattern.compile("([0-9A-Fa-f:]{17})\\s+ch=(\\d+)\\s+rssi=(-?\\d+)\\s+(\\S+)");
            Matcher m = p.matcher(rest);
            if (!m.find()) return null;
            String bssid = m.group(1);
            int channel = Integer.parseInt(m.group(2));
            int rssi = Integer.parseInt(m.group(3));
            String enc = m.group(4);
            String ssid = rest.substring(0, m.start()).trim();
            return new NetworkInfo(idx, ssid, bssid, channel, rssi, enc);
        } catch (Exception e) { return null; }
    }

    private void toast(String s) {
        Toast.makeText(this, s, Toast.LENGTH_SHORT).show();
    }
}

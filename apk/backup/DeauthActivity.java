package com.mt2.attack;

import android.app.Activity;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

public class DeauthActivity extends Activity {

    private TextView logView, statusText;
    private Button btnFull, btnFull, btnTDeauth, btnStop, btnBack;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_attack);

        statusText = findViewById(R.id.statusText);
        logView = findViewById(R.id.logView);
        btnFull = findViewById(R.id.btnFull);
        btnTDeauth = findViewById(R.id.btnTDeauth);
        btnStop = findViewById(R.id.btnStop);
        btnBack = findViewById(R.id.btnBack);

        btnFull.setOnClickListener(v -> startBeaconFlood());
        btnFull.setOnClickListener(v -> startFullDeauth());
        btnTDeauth.setOnClickListener(v -> startTargetedDeauth());
        btnStop.setOnClickListener(v -> stopDeauth());
        btnBack.setOnClickListener(v -> finish());
    }

    private void startBeaconFlood() {
        statusText.setText("⚡ Full Deauth Active");
        statusText.setTextColor(getResources().getColor(R.color.accent_red));
        logView.append("\n[DEAUTH] Beacon flood started");
    }

    private void startFullDeauth() {
        statusText.setText("⚡ Full Deauth Active");
        statusText.setTextColor(getResources().getColor(R.color.accent_red));
        logView.append("\n[DEAUTH] Full deauth started");
    }

    private void startTargetedDeauth() {
        statusText.setText("⚡ Targeted Deauth Active");
        statusText.setTextColor(getResources().getColor(R.color.accent_orange));
        logView.append("\n[DEAUTH] Targeted deauth started");
    }

    private void stopDeauth() {
        statusText.setText("✓ Stopped");
        statusText.setTextColor(getResources().getColor(R.color.accent_green));
        logView.append("\n[DEAUTH] Stopped");
    }
}

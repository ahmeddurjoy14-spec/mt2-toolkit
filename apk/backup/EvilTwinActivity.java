package com.mt2.attack;

import android.app.Activity;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

public class EvilTwinActivity extends Activity {

    private TextView logView, statusText;
    private EditText ssidField;
    private Button btnClone, btnStart, btnStop, btnBack;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        // Use attack layout but add our own views programmatically for simplicity
        setContentView(R.layout.activity_attack);

        statusText = findViewById(R.id.statusText);
        logView = findViewById(R.id.logView);
        // Add ssidField programmatically
        ssidField = new EditText(this);
        ssidField.setHint("Enter target SSID");
        ssidField.setTextColor(0xFFFFFFFF);

        btnClone = findViewById(R.id.btnFull);      // Use Full for Clone
        btnStart = findViewById(R.id.btnEvilTwin);   // Use EvilTwin for Start
        btnStop = findViewById(R.id.btnStop);
        btnBack = findViewById(R.id.btnBack);

        btnClone.setOnClickListener(v -> cloneNetwork());
        btnStart.setOnClickListener(v -> startEvilTwin());
        btnStop.setOnClickListener(v -> stopEvilTwin());
        btnBack.setOnClickListener(v -> finish());
    }

    private void cloneNetwork() {
        String ssid = ssidField.getText().toString();
        statusText.setText("📡 Cloning: " + ssid);
        logView.append("\n[EVIL TWIN] Cloning network: " + ssid);
    }

    private void startEvilTwin() {
        statusText.setText("⚡ Evil Twin Active");
        statusText.setTextColor(getResources().getColor(R.color.accent_purple));
        logView.append("\n[EVIL TWIN] Portal started");
    }

    private void stopEvilTwin() {
        statusText.setText("✓ Stopped");
        statusText.setTextColor(getResources().getColor(R.color.accent_green));
        logView.append("\n[EVIL TWIN] Stopped");
    }
}

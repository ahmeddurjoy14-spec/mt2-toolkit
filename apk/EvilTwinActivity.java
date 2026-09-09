package com.mt2.attack;

import android.app.Activity;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

public class EvilTwinActivity extends Activity {

    private TextView logView, statusText;
    private Button btnClone, btnStart, btnStop, btnBack;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_attack);

        statusText = findViewById(R.id.statusText);
        logView = findViewById(R.id.logView);
        btnClone = findViewById(R.id.btnFull);
        btnStart = findViewById(R.id.btnEvilTwin);
        btnStop = findViewById(R.id.btnStop);
        btnBack = findViewById(R.id.btnBack);

        btnClone.setText("CLONE NETWORK");

        btnClone.setOnClickListener(v -> cloneNetwork());
        btnStart.setOnClickListener(v -> startEvilTwin());
        btnStop.setOnClickListener(v -> stopEvilTwin());
        btnBack.setOnClickListener(v -> finish());
    }

    private void cloneNetwork() {
        statusText.setText("CLONING NETWORK...");
        logView.append("\n[EVIL TWIN] Cloning network");
        Toast.makeText(this, "Network Clone Started", Toast.LENGTH_SHORT).show();
    }

    private void startEvilTwin() {
        statusText.setText("EVIL TWIN ACTIVE");
        statusText.setTextColor(getResources().getColor(R.color.accent_purple));
        logView.append("\n[EVIL TWIN] Portal started");
        Toast.makeText(this, "Evil Twin Active", Toast.LENGTH_SHORT).show();
    }

    private void stopEvilTwin() {
        statusText.setText("STOPPED");
        statusText.setTextColor(getResources().getColor(R.color.accent_green));
        logView.append("\n[EVIL TWIN] Stopped");
        Toast.makeText(this, "Evil Twin Stopped", Toast.LENGTH_SHORT).show();
    }
}

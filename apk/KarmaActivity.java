package com.mt2.attack;

import android.app.Activity;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

public class KarmaActivity extends Activity {

    private TextView logView, statusText;
    private Button btnKarma, btnStop, btnBack;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_attack);

        statusText = findViewById(R.id.statusText);
        logView = findViewById(R.id.logView);
        btnKarma = findViewById(R.id.btnKarma);
        btnStop = findViewById(R.id.btnStop);
        btnBack = findViewById(R.id.btnBack);

        btnKarma.setOnClickListener(v -> startKarma());
        btnStop.setOnClickListener(v -> stopKarma());
        btnBack.setOnClickListener(v -> finish());
    }

    private void startKarma() {
        statusText.setText("KARMA PORTAL ACTIVE");
        statusText.setTextColor(getResources().getColor(R.color.accent_orange));
        logView.append("\n[KARMA] Portal started");
        Toast.makeText(this, "Karma Portal Active", Toast.LENGTH_SHORT).show();
    }

    private void stopKarma() {
        statusText.setText("STOPPED");
        statusText.setTextColor(getResources().getColor(R.color.accent_green));
        logView.append("\n[KARMA] Stopped");
        Toast.makeText(this, "Karma Stopped", Toast.LENGTH_SHORT).show();
    }
}

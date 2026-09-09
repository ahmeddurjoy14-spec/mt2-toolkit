package com.mt2.attack;

import android.app.Activity;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;
import android.os.Handler;
import android.os.Looper;

public class DeauthActivity extends Activity {

    private TextView logView, statusText;
    private Button btnFull, btnTDeauth, btnStop, btnBack;

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

        btnFull.setOnClickListener(new View.OnClickListener() {@Override public void onClick(View v) { fullDeauth(); }});
        btnTDeauth.setOnClickListener(new View.OnClickListener() {@Override public void onClick(View v) { targetedDeauth(); }});
        btnStop.setOnClickListener(new View.OnClickListener() {@Override public void onClick(View v) { stopAttack(); }});
        btnBack.setOnClickListener(new View.OnClickListener() {@Override public void onClick(View v) { finish(); }});
    }

    private void fullDeauth() {
        statusText.setText("FULL DEAUTH ACTIVE");
        statusText.setTextColor(getResources().getColor(R.color.accent_red));
        logView.append("\n[DEAUTH] Full deauth started");
        Toast.makeText(this, "Full Deauth Active", Toast.LENGTH_SHORT).show();
    }

    private void targetedDeauth() {
        statusText.setText("TARGETED DEAUTH ACTIVE");
        statusText.setTextColor(getResources().getColor(R.color.accent_orange));
        logView.append("\n[DEAUTH] Targeted deauth started");
        Toast.makeText(this, "Targeted Deauth Active", Toast.LENGTH_SHORT).show();
    }

    private void stopAttack() {
        statusText.setText("STOPPED");
        statusText.setTextColor(getResources().getColor(R.color.accent_green));
        logView.append("\n[DEAUTH] Stopped");
        Toast.makeText(this, "Stopped", Toast.LENGTH_SHORT).show();
    }
}

package com.mt2.attack;

public class NetworkInfo {
    public int idx;
    public String ssid;
    public String bssid;
    public int channel;
    public int rssi;
    public String encrypted;

    public NetworkInfo(int idx, String ssid, String bssid, int channel, int rssi, String enc) {
        this.idx = idx;
        this.ssid = ssid;
        this.bssid = bssid;
        this.channel = channel;
        this.rssi = rssi;
        this.encrypted = enc;
    }
}

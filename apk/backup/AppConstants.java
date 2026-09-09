package com.mt2.attack;

/**
 * Shared constants used across multiple activities.
 * Defined in a separate class to avoid circular dependencies.
 */
public final class AppConstants {
    private AppConstants() {} // no instances

    public static final String PREFS = "mt2_prefs";
    public static final String KEY_TARGET_IDX = "target_idx";
    public static final String KEY_TARGET_SSID = "target_ssid";
    public static final String KEY_TARGET_BSSID = "target_bssid";
    public static final String KEY_TARGET_CHAN = "target_chan";
    public static final String ACTION_USB_PERMISSION = "com.mt2.attack.USB_PERMISSION";
}

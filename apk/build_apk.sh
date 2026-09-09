#!/bin/bash
# build_apk.sh - Build MT2 ESP32 WiFi Pentest + Bluetooth APK
set -e

APK_DIR="/sdcard/MT2/apk"
ANDROID_HOME="/root/android-sdk"
BUILD_TOOLS="$ANDROID_HOME/android-14"
AAPT2="/usr/bin/aapt2"
AAPT="/usr/bin/aapt"
ZIPALIGN="/usr/bin/zipalign"
ANDROID_JAR="$ANDROID_HOME/platforms/android.jar"
APKSIGNER="/usr/bin/apksigner"
D8_JAR="$BUILD_TOOLS/lib/d8.jar"
OUT="$APK_DIR/dist"

mkdir -p "$OUT" "$APK_DIR/build/classes" "$APK_DIR/build/gen"

# Extract AAR
SERIAL_LIB="$APK_DIR/libs/usb-serial-for-android.aar"
AAR_EXTRACT="/tmp/aar_extract"
rm -rf "$AAR_EXTRACT" && mkdir -p "$AAR_EXTRACT"
if [ -f "$SERIAL_LIB" ]; then
    cd "$AAR_EXTRACT" && unzip -q "$SERIAL_LIB" 2>/dev/null
fi
SERIAL_CLASSES="$AAR_EXTRACT/classes.jar"

# Step 1: Compile resources
echo "[1/7] Compile resources..."
"$AAPT2" compile --dir "$APK_DIR/res" -o "$APK_DIR/build/resources.zip" 2>&1 | tail -3

# Step 2: Link resources + manifest, generate R.java
echo "[2/7] Link resources + generate R.java..."
"$AAPT2" link \
    -I "$ANDROID_JAR" \
    --manifest "$APK_DIR/AndroidManifest.xml" \
    --java "$APK_DIR/build/gen" \
    -o "$APK_DIR/build/unaligned.apk" \
    "$APK_DIR/build/resources.zip" 2>&1 | tail -3

# Step 3: Compile Java
echo "[3/7] Compile Java..."
JARS="$ANDROID_JAR"
[ -f "$SERIAL_CLASSES" ] && JARS="$JARS:$SERIAL_CLASSES"

javac \
    --release 14 \
    -classpath "$JARS" \
    -d "$APK_DIR/build/classes" \
    $(find "$APK_DIR/build/gen" -name "*.java" 2>/dev/null) \
    "$APK_DIR/MainActivity.java" \
    "$APK_DIR/ScanActivity.java" \
    "$APK_DIR/AttackActivity.java" \
    "$APK_DIR/BluetoothActivity.java" \
    "$APK_DIR/DeauthActivity.java" \
    "$APK_DIR/KarmaActivity.java" \
    "$APK_DIR/EvilTwinActivity.java" \
    "$APK_DIR/SerialManager.java" \
    "$APK_DIR/NetworkInfo.java" \
    "$APK_DIR/AppConstants.java" \
    "$APK_DIR/UsbPermissionReceiver.java" 2>&1 | tail -15

# Step 4: Convert .class to .dex
echo "[4/7] Dex..."
CLASS_FILES=$(find "$APK_DIR/build/classes" -name "*.class" 2>/dev/null | tr '\n' ' ')
[ -f "$SERIAL_CLASSES" ] && CLASS_FILES="$CLASS_FILES $SERIAL_CLASSES"
mkdir -p "$APK_DIR/build"
cd "$APK_DIR/build/classes"
java -cp "$D8_JAR" com.android.tools.r8.D8 \
    --lib "$ANDROID_JAR" \
    --output "$APK_DIR/build" \
    $CLASS_FILES 2>\&1 | grep -v "^Warning" | tail -3
# Step 5: Add classes.dex to APK
echo "[5/7] Add dex to APK..."
cd "$APK_DIR/build"
"$AAPT" add unaligned.apk classes.dex 2>&1 | tail -2

# Step 6: Align
echo "[6/7] Align..."
"$ZIPALIGN" -f 4 "unaligned.apk" "$OUT/MT2ESP32-unsigned.apk" 2>&1 | tail -3

# Step 7: Sign
KEYSTORE="$APK_DIR/debug.keystore"
if [ ! -f "$KEYSTORE" ]; then
    keytool -genkey -v -keystore "$KEYSTORE" \
        -storepass android -alias androiddebugkey -keypass android \
        -keyalg RSA -keysize 2048 -validity 10000 \
        -dname "CN=Android Debug,O=Android,C=US" 2>&1 | tail -2
fi

"$APKSIGNER" sign \
    --ks "$KEYSTORE" \
    --ks-pass pass:android \
    --key-pass pass:android \
    --ks-key-alias androiddebugkey \
    --out "$OUT/MT2ESP32.apk" \
    "$OUT/MT2ESP32-unsigned.apk" 2>&1 | tail -3

echo ""
echo "=== DONE ==="
ls -la "$OUT/MT2ESP32.apk" 2>&1
echo ""
echo "Install: adb install $OUT/MT2ESP32.apk"

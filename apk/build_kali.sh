#!/bin/bash
set -e

APK_DIR="/home/kali/Desktop/MT2/apk"
AAPT2="/usr/bin/aapt2"
ZIPALIGN="/usr/bin/zipalign"
APKSIGNER="/usr/bin/apksigner"
ANDROID_JAR="/opt/android-sdk/platforms/android-29/android.jar"
DX_JAR="/tmp/dx.jar"
OUT="$APK_DIR/dist"

mkdir -p "$OUT" "$APK_DIR/build/classes"

echo "[1/6] Compile resources..."
"$AAPT2" compile --dir "$APK_DIR/res" -o "$APK_DIR/build/resources.zip" 2>&1 | tail -3

echo "[2/6] Link resources + manifest..."
"$AAPT2" link \
    -I "$ANDROID_JAR" \
    --manifest "$APK_DIR/AndroidManifest.xml" \
    -o "$APK_DIR/build/unaligned.apk" \
    "$APK_DIR/build/resources.zip" 2>&1 | tail -3

echo "[3/6] Compile Java..."
javac \
    -source 1.8 -target 1.8 \
    -bootclasspath "$ANDROID_JAR" \
    -d "$APK_DIR/build/classes" \
    "$APK_DIR/ConnectActivity.java" \
    "$APK_DIR/ScanActivity.java" \
    "$APK_DIR/AttackActivity.java" \
    "$APK_DIR/SerialManager.java" \
    "$APK_DIR/NetworkInfo.java" \
    "$APK_DIR/AppConstants.java" \
    "$APK_DIR/UsbPermissionReceiver.java" 2>&1

echo "[4/6] Convert to dex..."
cd "$APK_DIR/build/classes"
java -jar "$DX_JAR" --dex --output="$APK_DIR/build/classes.dex" . 2>&1

echo "[5/6] Package APK..."
cd "$APK_DIR/build"
cp unaligned.apk unaligned_with_dex.apk
"$AAPT2" add unaligned_with_dex.apk classes.dex 2>&1

echo "[6/6] Sign APK..."
"$ZIPALIGN" -f 4 unaligned_with_dex.apk "$OUT/MT2Attack-unsigned.apk" 2>&1 | tail -2
"$APKSIGNER" sign \
    --ks "$APK_DIR/debug.keystore" \
    --ks-pass pass:android \
    --key-pass pass:android \
    --ks-key-alias androiddebugkey \
    --out "$OUT/MT2Attack.apk" \
    "$OUT/MT2Attack-unsigned.apk" 2>&1 | tail -3

echo ""
echo "=== DONE ==="
ls -la "$OUT/MT2Attack.apk"

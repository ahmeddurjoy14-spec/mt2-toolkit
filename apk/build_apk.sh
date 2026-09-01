#!/bin/bash
# build_apk.sh - Build MT2 Attack Console APK (Termux aarch64)
set -e

APK_DIR="/sdcard/MT2/apk"
ANDROID_HOME="${ANDROID_HOME:-/opt/android-sdk}"
BUILD_TOOLS="$ANDROID_HOME/build-tools/34.0.0"
AAPT2="/usr/bin/aapt2"
ZIPALIGN="/usr/bin/zipalign"
PLATFORM="$ANDROID_HOME/platforms/android-29"
ANDROID_JAR="$PLATFORM/android.jar"
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
    -source 1.8 -target 1.8 \
    -bootclasspath "$ANDROID_JAR" \
    -classpath "$JARS" \
    -d "$APK_DIR/build/classes" \
    $(find "$APK_DIR/build/gen" -name "*.java") \
    "$APK_DIR/ConnectActivity.java" \
    "$APK_DIR/ScanActivity.java" \
    "$APK_DIR/AttackActivity.java" \
    "$APK_DIR/SerialManager.java" \
    "$APK_DIR/NetworkInfo.java" \
    "$APK_DIR/AppConstants.java" \
    "$APK_DIR/UsbPermissionReceiver.java" 2>&1 | tail -10

# Step 4: Convert .class to .dex (including serial lib classes)
echo "[4/7] Dex..."
CLASS_FILES=$(find "$APK_DIR/build/classes" -name "*.class" | tr '\n' ' ')
[ -f "$SERIAL_CLASSES" ] && CLASS_FILES="$CLASS_FILES $SERIAL_CLASSES"
mkdir -p "$APK_DIR/build"
cd "$APK_DIR/build/classes"
java -cp "$ANDROID_HOME/cmdline-tools/lib/r8.jar" com.android.tools.r8.D8 \
    --min-api 21 \
    --output "$APK_DIR/build" \
    $CLASS_FILES 2>&1 | grep -v "^Warning" | tail -3

# Step 5: Add classes.dex to APK
echo "[5/7] Add dex to APK..."
cd "$APK_DIR/build"
/usr/bin/aapt add unaligned.apk classes.dex 2>&1 | tail -2

# Step 6: Align
echo "[6/7] Align..."
"$ZIPALIGN" -f 4 "unaligned.apk" "$OUT/MT2Attack-unsigned.apk" 2>&1 | tail -3

# Step 7: Sign
echo "[7/7] Sign..."
KEYSTORE="$APK_DIR/debug.keystore"
if [ ! -f "$KEYSTORE" ]; then
    keytool -genkey -v -keystore "$KEYSTORE" \
        -storepass android -alias androiddebugkey -keypass android \
        -keyalg RSA -keysize 2048 -validity 10000 \
        -dname "CN=Android Debug,O=Android,C=US" 2>&1 | tail -2
fi

"$BUILD_TOOLS/apksigner" sign \
    --ks "$KEYSTORE" \
    --ks-pass pass:android \
    --key-pass pass:android \
    --ks-key-alias androiddebugkey \
    --out "$OUT/MT2Attack.apk" \
    "$OUT/MT2Attack-unsigned.apk" 2>&1 | tail -3

echo ""
echo "=== DONE ==="
ls -la "$OUT/MT2Attack.apk"
echo ""
echo "Install: adb install $OUT/MT2Attack.apk"

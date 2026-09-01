#!/bin/bash
# build_firmware.sh - Push to GitHub and download compiled firmware
# Usage: bash build_firmware.sh <github-username>

set -e

REPO="mt2-toolkit"
FOLDER="/sdcard/MT2"

if [ -z "$1" ]; then
    echo "Usage: bash build_firmware.sh <github-username>"
    echo "Example: bash build_firmware.sh myusername"
    exit 1
fi

USER="$1"
cd "$FOLDER"

echo "=== MT2 Firmware Cloud Build ==="
echo ""
echo "1. Adding GitHub remote..."
git remote add origin "https://github.com/$USER/$REPO.git" 2>/dev/null || git remote set-url origin "https://github.com/$USER/$REPO.git"

echo "2. Committing firmware..."
git add .github/ *.ino *.h platformio.ini ATTACK_WORKFLOW.md README.md .gitignore 2>/dev/null || true
git commit -m "MT2 firmware with deauth fix - $(date)" 2>/dev/null || echo "Nothing to commit"

echo "3. Pushing to GitHub..."
git branch -M main
git push -u origin main

echo ""
echo "=== Done! ==="
echo ""
echo "Now:"
echo "1. Go to: https://github.com/$USER/$REPO/actions"
echo "2. Click 'Build MT2 Firmware' → 'Run workflow'"
echo "3. Wait ~5 minutes"
echo "4. Download .bin from Artifacts"
echo "5. Flash with: esptool.py --port /dev/ttyUSB0 write_flash 0x00000 firmware.bin"

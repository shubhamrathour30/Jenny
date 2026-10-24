#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
npm init -y >/dev/null 2>&1
npm install @capacitor/core@7 @capacitor/cli@7 @capacitor/android@7 --no-audit --no-fund
npx cap add android
pip install pillow >/dev/null 2>&1 || pip3 install pillow
python3 patch_android.py
cd android
chmod +x gradlew
./gradlew assembleDebug --no-daemon
cp app/build/outputs/apk/debug/app-debug.apk ../../Jenny.apk
echo "built"

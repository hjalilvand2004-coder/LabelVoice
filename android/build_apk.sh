#!/usr/bin/env bash
# ============================================================
#  ساخت APK اندروید LabelVoice — بدون Gradle و بدون Android Studio
#
#  پیش‌نیازها (متغیرهای محیطی یا مسیرهای پیش‌فرض):
#    BUILD_TOOLS  مسیر پوشه build-tools 34 (شامل aapt2, d8, apksigner, zipalign)
#    ANDROID_JAR  مسیر android.jar پلتفرم android-34
#    JDK_BIN      (اختیاری) مسیر bin یک JDK 17+ اگر java/javac در PATH نباشد
#
#  خروجی: build/LabelVoice-Android-<VERSION>.apk (امضاشده، قابل نصب)
#  کلید امضا در keystore/labelvoice.keystore ساخته می‌شود (در git نیست).
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

BT="${BUILD_TOOLS:-$HOME/android-sdk/build-tools/34.0.0}"
AJ="${ANDROID_JAR:-$HOME/android-sdk/platforms/android-34/android.jar}"
if [ -n "${JDK_BIN:-}" ]; then export PATH="$JDK_BIN:$PATH"; fi

VERSION_NAME="${VERSION_NAME:-2.12.3}"
VERSION_CODE="${VERSION_CODE:-27}"
OUT_APK="build/LabelVoice-Android-${VERSION_NAME}.apk"

command -v javac >/dev/null || { echo "خطا: javac یافت نشد (JDK_BIN را تنظیم کنید)"; exit 1; }
[ -x "$BT/aapt2" ]   || { echo "خطا: aapt2 در $BT نیست"; exit 1; }
[ -f "$AJ" ]         || { echo "خطا: android.jar در $AJ نیست"; exit 1; }

mkdir -p build/assets build/classes build/dex build/res keystore

# ---- 1) آماده‌سازی assets از PWA (بدون لانچرهای دسکتاپ) ----
echo "[1/7] آماده‌سازی assets از ../mobile-app ..."
rm -rf build/assets && mkdir -p build/assets
(
  cd ../mobile-app
  find . -type f \
    ! -name 'شروع-در-ویندوز.bat' ! -name 'START-WINDOWS.bat' \
    ! -name 'شروع-در-لینوکس-مک.sh' ! -name 'server-windows.ps1' \
    ! -name 'README-MOBILE-fa.md' ! -name 'label-reader-singlefile.html' \
    -exec cp --parents {} ../android/build/assets/ \;
)

# ---- 2) کامپایل منابع ----
echo "[2/7] aapt2 compile/link ..."
rm -f build/res.zip build/base.apk
"$BT/aapt2" compile --dir res -o build/res.zip
"$BT/aapt2" link -o build/base.apk \
  -I "$AJ" \
  --manifest AndroidManifest.xml \
  --min-sdk-version 24 --target-sdk-version 34 \
  --version-code "$VERSION_CODE" --version-name "$VERSION_NAME" \
  -A build/assets \
  build/res.zip

# ---- 3) کامپایل جاوا + dex ----
# توجه ۱: d8 داخل build-tools 34 باگ NPE روی کلاس‌های ناشناس خروجی javacهای جدید دارد؛
#   اگر R8_JAR (jar نسخه جدید R8 از dl.google.com/android/maven2/com/android/tools/r8) ست شود،
#   به‌جای d8 از آن استفاده می‌شود.
# توجه ۲: اگر jar را با java اجرا می‌کنید و java در PATH نیست، JDK_BIN را تنظیم کنید.
echo "[3/7] javac + dex ..."
rm -rf build/classes build/dex && mkdir -p build/classes build/dex
javac --release 8 -classpath "$AJ" -d build/classes \
  java/com/labelvoice/app/MainActivity.java
CLASS_FILES=$(find build/classes -name '*.class')
if [ -n "${R8_JAR:-}" ]; then
  java -cp "$R8_JAR" com.android.tools.r8.D8 --release --min-api 24 --lib "$AJ" \
    --output build/dex $CLASS_FILES
elif [ -n "${D8_JDK_BIN:-}" ]; then
  env PATH="$D8_JDK_BIN:$PATH" "$BT/d8" --release --min-api 24 --lib "$AJ" \
    --output build/dex $CLASS_FILES
else
  "$BT/d8" --release --min-api 24 --lib "$AJ" \
    --output build/dex $CLASS_FILES
fi

# ---- 4) افزودن classes.dex ----
echo "[4/7] افزودن classes.dex ..."
(cd build/dex && zip -q ../base.apk classes.dex)

# ---- 5) zipalign ----
echo "[5/7] zipalign ..."
"$BT/zipalign" -f 4 build/base.apk build/aligned.apk

# ---- 6) کلید امضا (یک‌بار ساخته می‌شود) ----
if [ ! -f keystore/labelvoice.keystore ]; then
  echo "[6/7] ساخت کلید امضا ..."
  keytool -genkeypair -v \
    -keystore keystore/labelvoice.keystore -alias labelvoice \
    -keyalg RSA -keysize 2048 -validity 10000 \
    -storepass labelvoice-sign -keypass labelvoice-sign \
    -dname "CN=LabelVoice, OU=LabelVoice, O=LabelVoice, C=IR"
else
  echo "[6/7] کلید امضا موجود است."
fi

# ---- 7) امضا ----
echo "[7/7] امضا ..."
rm -f "$OUT_APK"
"$BT/apksigner" sign \
  --ks keystore/labelvoice.keystore \
  --ks-key-alias labelvoice \
  --ks-pass pass:labelvoice-sign --key-pass pass:labelvoice-sign \
  --out "$OUT_APK" \
  build/aligned.apk
"$BT/apksigner" verify "$OUT_APK" && echo "تأیید امضا: OK"

echo ""
echo "APK آماده شد: android/$OUT_APK"

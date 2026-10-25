#!/usr/bin/env sh
# LabelVoice — پل OCR (v2.5.0): موتورهای سنگین دسکتاپ برای وب/موبایل
# اجرا: ./START-BRIDGE.sh  →  سپس آدرس نمایش‌داده‌شده را در انتخاب‌گر موتورِ
# رابط وب/موبایل وارد کنید («پل دسکتاپ» → بررسی اتصال).
cd "$(dirname "$0")/.."
echo "============================================"
echo "  LabelVoice - OCR Bridge (v2.5.0)"
echo "  EasyOCR / Surya / Qwen3-VL on THIS computer"
echo "============================================"
if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] python3 یافت نشد — ابتدا پایتون ۳.۹+ نصب کنید."
  exit 1
fi
exec python3 -m label_reader.bridge --port 8770

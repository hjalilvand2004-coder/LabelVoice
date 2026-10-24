#!/usr/bin/env bash
# راه‌انداز لینوکس/مک — برچسب‌خوان موبایل
# اگر python3 موجود باشد سرور محلی راه می‌اندازد (کاملاً اختیاری)؛
# در غیر این صورت همان فایل index.html را مستقیم باز کنید (حالت file://).
set -e
cd "$(dirname "$0")"
PORT=8765
echo "============================================"
echo "  برچسب‌خوان هوشمند دارو و محصولات"
echo "  راه‌انداز لینوکس/مک"
echo "============================================"
if command -v python3 >/dev/null 2>&1; then
  ( sleep 1
    (xdg-open "http://127.0.0.1:$PORT/" 2>/dev/null || open "http://127.0.0.1:$PORT/" 2>/dev/null) || true
  ) &
  echo "اجرا روی http://127.0.0.1:$PORT/ — برای بستن Ctrl+C"
  # v1.8.3 fix: در بستهٔ قابل حمل، صفحهٔ اصلی داخل webapp/ است
  if [ -d webapp ]; then
    exec python3 -m http.server "$PORT" --bind 127.0.0.1 --directory webapp
  else
    exec python3 -m http.server "$PORT" --bind 127.0.0.1
  fi
else
  echo "پایتون یافت نشد؛ نگران نباشید:"
  echo "فایل index.html را در مرورگر (Chrome/Firefox/Edge) باز کنید."
  echo "بار اول به اینترنت برای بارگیری موتور OCR نیاز دارد."
  if [ -d webapp ]; then (xdg-open "$(pwd)/webapp/index.html" 2>/dev/null || open "$(pwd)/webapp/index.html" 2>/dev/null) || true
  else (xdg-open "$(pwd)/index.html" 2>/dev/null || open "$(pwd)/index.html" 2>/dev/null) || true; fi
fi

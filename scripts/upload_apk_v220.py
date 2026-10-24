#!/usr/bin/env python3
"""افزودن دارایی APK به Release v2.2.0 — توکن فقط گذرا از ورودی استاندارد."""
import json
import os
import sys
import urllib.request
from pathlib import Path

REPO = "hjalilvand2004-coder/LabelVoice"
TOKEN = os.environ.get("GH_TOKEN") or sys.stdin.readline().strip()
APK = Path("/home/z/my-project/labelvoice-clone/android/build/LabelVoice-Android-2.2.0.apk")
NAME = "LabelVoice-v2.2.0-Android.apk"
LABEL = "نسخهٔ نصب‌پذیر اندروید (versionCode 14) — کاملاً آفلاین، WebView محلی، امضاشده"
API = f"https://api.github.com/repos/{REPO}"
HDR = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}


def req(url, data=None, method="GET", raw=None, headers=None):
    body = raw if raw is not None else (json.dumps(data).encode() if data else None)
    r = urllib.request.Request(url, data=body, headers=headers or HDR, method=method)
    with urllib.request.urlopen(r) as resp:
        payload = resp.read()
    return json.loads(payload) if payload else {}


rel = req(f"{API}/releases/tags/v2.2.0")
existing = {a["name"]: a for a in rel.get("assets", [])}

# اگر نسخهٔ قبلی همان نام هست، اول حذف کن (جایگزینی)
if NAME in existing:
    req(f"{API}/releases/assets/{existing[NAME]['id']}", method="DELETE")
    print(f"old asset deleted: {NAME}")

up = urllib.request.Request(
    f"https://uploads.github.com/repos/{REPO}/releases/{rel['id']}/assets?name={NAME}",
    data=APK.read_bytes(),
    headers={"Authorization": f"Bearer {TOKEN}",
             "Content-Type": "application/vnd.android.package-archive",
             "Content-Length": str(APK.stat().st_size)},
    method="POST")
with urllib.request.urlopen(up) as resp:
    print(f"uploaded: {resp.status} {NAME}")

# به‌روزرسانی بدنهٔ Release — افزودن بخش APK
body = rel.get("body", "")
apk_section = """### 📱 نسخهٔ نصب‌پذیر اندروید (APK)
- داراییٔ **`LabelVoice-v2.2.0-Android.apk`**: WebView بومی (`MainActivity`) با موتور کامل PWA داخل APK — **کاملاً آفلاین** (OCR Tesseract.js WASM + مدل‌های `fas/eng` داخل بسته)
- `versionCode 14 / versionName 2.2.0` · `minSdk 24 (اندروید ۷+)` · `targetSdk 34`
- مجوزها: دوربین (عکس مستقیم از جعبهٔ دارو) + اینترنت (فقط fallback اختیاری CDN)
- نصب: دانلود APK → اجازهٔ «نصب از منابع ناشناس» → نصب
- کلید امضا محلی نگهداری می‌شود و در گیت کامیت نمی‌شود

"""
anchor = "### 🧠 شفافیت مدل‌ها"
if anchor in body and "LabelVoice-v2.2.0-Android.apk" not in body:
    body = body.replace(anchor, apk_section + anchor)
    req(f"{API}/releases/{rel['id']}", data={"body": body}, method="PATCH")
    print("release body updated with APK section")
print("DONE")

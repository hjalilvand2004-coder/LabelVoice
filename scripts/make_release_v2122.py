#!/usr/bin/env python3
"""انتشار Release v2.12.2 — توکن فقط گذرا (GH_TOKEN یا urlsplit از URL ریموت)؛ هرگز ذخیره نمی‌شود.

v2.12.2 = مستندات مدل‌ها (بر اساس بررسی و تحلیل صورت گرفته):
  (۱) جدول «نوع، نام و مسیر فایل هر مدل» — باندل‌شده در پروژه / نصب جداگانه
      تک‌منبع حقیقت: label_reader/models_info.py → models_paths_markdown_fa()
  (۲) بازنویسی همهٔ مستندات با لحن «بر اساس بررسی و تحلیل …» (حذف نقل‌قول‌های درخواست/گزارش)
  (۳) حذف بازمانده‌های قدیمی: Web Speech API در جدول مدل‌ها + راهنمای کهنهٔ Edge در INSTALL
۶ دارایی: Full-Project / Portable-Web / Mobile-App-PWA / تک‌فایل /
APK (versionCode 26) / PDF مستندات v2.12.2.
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO = "hjalilvand2004-coder/LabelVoice"
ROOT = Path("/home/z/my-project/labelvoice-clone")
OUT = Path("/home/z/my-project/download")
VERSION = "2.12.2"


def token_from_remote() -> str:
    tok = os.environ.get("GH_TOKEN")
    if tok:
        return tok.strip()
    url = subprocess.check_output(
        ["git", "-C", str(ROOT), "config", "--get", "remote.origin.url"],
        text=True).strip()
    from urllib.parse import urlsplit, unquote
    password = urlsplit(url).password
    if password:
        return unquote(password)
    m = re.search(r":(ghp_[^@]+)@", url)
    if not m:
        sys.exit("توکن در URL ریموت یافت نشد؛ GH_TOKEN را ست کنید")
    return m.group(1)


TOKEN = token_from_remote()


def is_ascii_name(name: str) -> bool:
    return all(ord(c) < 128 for c in name)


def gh(method: str, url: str, data=None, ctype="application/json"):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/{url}", method=method,
        data=data,
        headers={"Authorization": f"token {TOKEN}",
                 "Accept": "application/vnd.github+json",
                 "Content-Type": ctype, "User-Agent": "labelvoice-release"})
    with urllib.request.urlopen(req) as r:
        body = r.read()
        return json.loads(body) if body else {}


# ---------- ۱) پروژهٔ کامل ----------
full_zip = OUT / f"LabelVoice-v{VERSION}-Full-Project.zip"
exclude_dirs = {".git", "__pycache__", ".pytest_cache", "node_modules",
                ".venv", "venv", "build", "keystore", "deploy-tmp", "sw-heal-site", "starthere-test"}
with zipfile.ZipFile(full_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    n = 0
    for p in ROOT.rglob("*"):
        if p.is_dir():
            continue
        rel = p.relative_to(ROOT)
        if any(part in exclude_dirs for part in rel.parts):
            continue
        if rel.suffix == ".pyc":
            continue
        if is_ascii_name(rel.as_posix()):
            arc = f"LabelVoice-v{VERSION}/{rel.as_posix()}"
        else:
            safe = rel.name.encode("ascii", "ignore").decode() or "file"
            arc = f"LabelVoice-v{VERSION}/{rel.parent.as_posix()}/x-{safe}"
        zf.write(p, arc)
        n += 1
print(f"OK {full_zip} ({full_zip.stat().st_size/1e6:.1f} MB, {n} فایل)")

# ---------- ۲) اپ موبایل PWA ----------
MOBILE = ROOT / "mobile-app"
mobile_zip = OUT / f"LabelVoice-v{VERSION}-Mobile-App-PWA.zip"
with zipfile.ZipFile(mobile_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    skip = {
        "label-reader-singlefile.html", "START-WINDOWS.bat",
        "server-windows.ps1", "شروع-در-ویندوز.bat", "شروع-در-لینوکس-مک.sh",
        "START-BRIDGE.bat", "START-BRIDGE.sh",
    }
    for p in MOBILE.rglob("*"):
        if p.is_dir():
            continue
        rel = p.relative_to(MOBILE)
        if rel.as_posix() in skip:
            continue
        if any(part in {".git", "__pycache__", "node_modules"} for part in rel.parts):
            continue
        assert is_ascii_name(rel.as_posix()), f"non-ascii: {rel}"
        zf.write(p, f"LabelVoice-Mobile-PWA/{rel.as_posix()}")
    zf.write(MOBILE / "START-WINDOWS.bat", "LabelVoice-Mobile-PWA/START-WINDOWS.bat")
    zf.write(MOBILE / "server-windows.ps1", "LabelVoice-Mobile-PWA/server-windows.ps1")
    zf.write(MOBILE / "START-BRIDGE.bat", "LabelVoice-Mobile-PWA/START-BRIDGE.bat")
    zf.write(MOBILE / "START-BRIDGE.sh", "LabelVoice-Mobile-PWA/START-BRIDGE.sh")
print(f"OK {mobile_zip} ({mobile_zip.stat().st_size/1e6:.1f} MB)")

# ---------- ۳) دارایی‌ها ----------
portable_zip = OUT / f"LabelVoice-v{VERSION}-Portable-Web.zip"
singlefile = ROOT / "mobile-app" / "label-reader-singlefile.html"
apk = ROOT / "android" / "build" / "LabelVoice-Android-2.12.2.apk"
pdf = ROOT / "docs" / "LabelVoice-Documentation-v2.12.2.pdf"

ASSETS = [
    (full_zip, f"LabelVoice-v{VERSION}-Full-Project.zip",
     "کل پروژه — دسکتاپ + وب/موبایل + اندروید + مدل صوتی Piper در models/tts + رجیستری مدل‌ها با مسیر فایل‌ها"),
    (portable_zip, f"LabelVoice-v{VERSION}-Portable-Web.zip",
     "بستهٔ قابل حمل بدون پایتون — START-HERE + تک‌فایل (موتور صوتی تعبیه‌شده) + وب‌اپ (SW v27) + لانچرها + _APK"),
    (mobile_zip, f"LabelVoice-v{VERSION}-Mobile-App-PWA.zip",
     "اپ موبایل PWA — مدل صوتی Piper باندل‌شده در vendor/tts؛ کش lbr-mobile-v27؛ کاملاً آفلاین"),
    (singlefile, f"label-reader-singlefile-v{VERSION}.html",
     "تک‌فایل آفلاین قابل حمل — OCR + دادهٔ زبان + مدل صوتی Piper و موتور WASM تعبیه‌شده (~۶۰MB) + جدول مسیر مدل‌ها در راهنما"),
    (apk, f"LabelVoice-v{VERSION}-Android.apk",
     "نسخهٔ نصب‌پذیر اندروید (versionCode 26، versionName 2.12.2) — صدا کاملاً لوکال؛ ارتقای مستقیم از v2.12.0/v2.12.1 (همان کلید امضا)"),
    (pdf, f"LabelVoice-Documentation-v{VERSION}.pdf",
     "مستندات فنی v2.12.2 — کارت ۵ بخش ۴: جدول «نوع، نام و مسیر فایل هر مدل» + تاریخچهٔ کامل"),
]

BODY = """## برچسب‌خوان هوشمند دارو و محصولات — نسخه ۲.۱۲.۲

**توسعه و طراحی: حمید جلیلوند و نوید بدری**

### 🗂️ مستندات مدل‌ها (بر اساس بررسی و تحلیل صورت گرفته) ✅

**۱) هر مدل — باندل‌شده یا نصب جداگانه — اکنون با «نوع + نام + مسیر دقیق فایل» مستند شده است** (تک‌منبع حقیقت: `label_reader/models_info.py` ← تابع `models_paths_markdown_fa`؛ همین جدول در README، راهنمای درون‌اپی، documentation.html، START-HERE و PDF):

| نقش | نوع | نام مدل / داده | وضعیت | مسیر فایل |
|---|---|---|---|---|
| دادهٔ زبان Tesseract | traineddata (LSTM) | fas (tessdata_best) + eng | **باندل‌شده در پروژه** | `models/tessdata/fas.traineddata` (~۳٫۳MB) · `eng.traineddata` (~۴٫۱MB) |
| مدل صوتی (هر سه رابط) | VITS — فایل ONNX | Piper «fa_IR-amir-medium» | **باندل‌شده در پروژه** | دسکتاپ: `models/tts/piper-fa_IR-amir/` (model.onnx fp32 ~۶۳MB + model.int8.onnx ~۱۸٫۶MB + tokens.txt + espeak-ng-data ۳۵۵ فایل) · مرورگر/APK: `mobile-app/vendor/tts/fa_IR-amir-medium.int8.onnx` (~۱۸MB) |
| موتور اجرای صوت (دسکتاپ) | کتابخانه استنتاج ONNX | sherpa-onnx 1.12.40 | نصب جداگانه (pip) | کد: `label_reader/tts/local_provider.py` |
| موتور اجرای صوت (مرورگر/APK) | WebAssembly | onnxruntime-web 1.18 + piper-phonemize | **باندل‌شده در پروژه** | `mobile-app/vendor/tts/` (ort + piper_phonemize WASM/data) |
| OCR موتور مرورگر | WebAssembly | Tesseract.js 6.0.1 + core 6.1.2 | **باندل‌شده در پروژه** | `mobile-app/vendor/tesseract/` + `vendor/core/` + `lang/integer\\|best/*.traineddata.gz` |
| OCR موتور دوم (اختیاری) | CRNN + CRAFT | EasyOCR 1.7 (fa+en) | نصب جداگانه + دانلود وزن | `~/.EasyOCR/model/` یا `LBR_EASYOCR_MODEL_DIR` |
| OCR موتور سوم (اختیاری) | ترنسفورمر | Surya (surya-ocr) | نصب جداگانه + دانلود وزن | کش Hugging Face `~/.cache/huggingface/hub` یا `LBR_SURYA_MODEL_DIR` |
| OCR موتور چهارم + دستیار (اختیاری) | VLM | Qwen/Qwen3-VL-2B-Instruct | نصب جداگانه + دانلود وزن | `~/.cache/huggingface/hub/models--Qwen--Qwen3-VL-2B-Instruct/` |

**۲) «آیا مسیر فایل مدل باید داده شود؟» — بله؛ برای همهٔ مدل‌ها داده می‌شود:** باندل‌شده‌ها با مسیر داخل مخزن، و موتورهای نصب‌جداگانه با مسیر دقیق ذخیره‌سازی وزن‌ها روی دستگاه و متغیر محیطیِ مسیر جایگزین. موتورهای بدون فایل مدل (OpenCV، قواعد regex، قالب‌ساز پاسخ) هم صریحاً «بدون فایل مدل» علامت خورده‌اند.

**۳) لحن مستندات یکدست شد:** عبارت‌های نقل‌قولی از درخواست/گزارش‌ها از متن مستندات حذف و به «بر اساس بررسی و تحلیل صورت گرفته …» بازنویسی شد — در README، documentation.html، START-HERE، راهنماهای درون‌اپی و PDF.

**۴) حذف بازمانده‌های قدیمی:** اشارهٔ Web Speech API از جدول مدل‌های documentation.html و راهنمای درون‌اپی؛ راهنمای کهنهٔ «مرورگر Edge» از عیب‌یابی INSTALL؛ محدودیت TTS وب/موبایل در LIMITATIONS.md با واقعیت مدل لوکال بازنویسی شد.

### 🔊 مدل صوتی لوکال — بی‌تغییر و کامل (v2.12.0 به بعد)

**Piper VITS — `fa_IR-amir-medium`** (صدای مردانهٔ فارسی؛ منبع: [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices) v1.0.0 — لایسنس MIT) — فایل‌های مدل **داخل فایل‌های پروژه**؛ دسکتاپ با sherpa-onnx 1.12.40 و مرورگر/WebView/APK با onnxruntime-web (WASM/SIMD) — بدون اینترنت، بدون سرویس ابری، بدون TTS گوشی. سنتز زندهٔ دسکتاپ در همین نسخه مجدداً راستی‌آزمایی شد.

### 🧪 آزمون‌ها

۱۷۷ pytest + ۸۰ Node (شامل ۹ آزمون TTS لوکال) + AppTest استریم‌لیت — همه پاس.

### 📦 نسخه‌ها

کش سرویس‌ورکر → `lbr-mobile-v27` · APK versionCode 26 / versionName 2.12.2 (همان کلید امضای v2.12.0/v2.12.1 — ارتقای مستقیم) · تک‌فایل بازساخت (~۶۰MB) · هر سه ZIP از مخزن به‌روز بازتولید شدند · PDF v2.12.2 (۱۲ صفحه).

### نصب

- **بدون پایتون:** `LabelVoice-v2.12.2-Portable-Web.zip` → استخراج در **پوشهٔ جدید** → `START-WINDOWS.bat` (خط «Folder version» باید v2.12.2 را نشان دهد)
- **دسکتاپ:** `pip install -r requirements.txt` → `streamlit run app.py` (مدل صوتی داخل پروژه؛ اینترنت لازم ندارد)
- **موبایل/وب:** `LabelVoice-v2.12.2-Mobile-App-PWA.zip` → `START-WINDOWS.bat`
- **تک‌فایل:** `label-reader-singlefile-v2.12.2.html` — دابل‌کلیک؛ OCR و صدا کاملاً آفلاین
- **APK:** نصب مستقیم (ارتقا از v2.12.0+)؛ اگر نسخهٔ نصب‌شدهٔ شما **v2.11.0 یا قدیمی‌تر** است ابتدا Uninstall کنید

### یادآوری محدوده محصول
این ابزار فقط می‌گوید «روی بسته چه نوشته شده است»؛ تشخیص دارو، تجویز، تعیین مقدار مصرف یا توصیهٔ پزشکی انجام نمی‌دهد. «قدرت درج‌شده» هرگز «دوز مصرف» نیست.
"""


def main() -> None:
    for path, name, _ in ASSETS:
        assert path.exists(), f"موجود نیست: {path}"
        print(f"✓ {name} ({path.stat().st_size/1e6:.1f} MB)")

    tag = f"v{VERSION}"
    try:
        gh("GET", f"git/ref/tags/{tag}")
        print(f"تگ {tag} از قبل موجود است")
    except Exception:  # noqa: BLE001
        try:
            gh("POST", "git/refs", json.dumps({
                "ref": f"refs/tags/{tag}",
                "sha": gh("GET", "git/ref/heads/main")["object"]["sha"]}).encode())
            print(f"تگ {tag} ساخته شد")
        except Exception as e:  # noqa: BLE001
            print("تگ (احتمالاً موجود):", e)

    rel = gh("POST", "releases", json.dumps({
        "tag_name": tag,
        "name": f"LabelVoice {tag} — جدول «نوع، نام و مسیر فایل هر مدل» + مستندات با لحن بررسی و تحلیل",
        "body": BODY, "draft": False, "prerelease": False}).encode())
    rel_id = rel["id"]
    print(f"Release id={rel_id}")

    for path, name, _ in ASSETS:
        data = path.read_bytes()
        boundary = "----labelvoice2122boundary"
        pre = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
               f"filename=\"{name}\"\r\nContent-Type: application/octet-stream\r\n\r\n").encode()
        body = pre + data + f"\r\n--{boundary}--\r\n".encode()
        url = (f"https://uploads.github.com/repos/{REPO}/releases/{rel_id}/assets"
               f"?name={name}")
        req = urllib.request.Request(url, method="POST", data=body, headers={
            "Authorization": f"token {TOKEN}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "labelvoice-release"})
        with urllib.request.urlopen(req) as r:
            res = json.loads(r.read())
            print(f"⬆ آپلود شد: {res['name']} ({res['size']/1e6:.1f} MB)")

    check = gh("GET", f"releases/tags/{tag}")
    names = [a["name"] for a in check.get("assets", [])]
    print(f"دارایی‌های نهایی ({len(names)}): {', '.join(names)}")
    print("URL:", check.get("html_url"))


if __name__ == "__main__":
    main()

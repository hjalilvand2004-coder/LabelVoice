#!/usr/bin/env python3
"""انتشار Release v2.12.0 — توکن فقط گذرا (GH_TOKEN یا urlsplit از URL ریموت)؛ هرگز ذخیره نمی‌شود.

v2.12.0 = درخواست کاربر: «یک مدل دانلود کن و در فایل‌های پروژه قرار بده و به‌صورت
لوکال از مدل در برنامه استفاده کن — برای همه موارد؛ نه سرویس آنلاین»
  (۱) مدل: Piper VITS fa_IR-amir-medium (rhasspy/piper-voices v1.0.0 — MIT)
      دسکتاپ: models/tts/piper-fa_IR-amir (fp32 ۶۳MB + int8 ۱۸٫۶MB + espeak-ng-data)
      مرورگر/APK: mobile-app/vendor/tts (int8 + onnxruntime-web 1.30 + piper-phonemize تریم‌شده)
  (۲) اجرای لوکال: دسکتاپ sherpa-onnx 1.12.40 · مرورگر onnxruntime-web (WASM/SIMD)
  (۳) حذف کامل مسیرهای آنلاین: edge/gtts providers · POST /api/tts · چک‌باکس رضایت ابری ·
      کلاینت مستقیم Edge · هک UA «Edg/» در MainActivity
  (۴) راستی‌آزمایی: کوانتیزه int8 (نسبت مدت ۱٫۰۱–۱٫۰۸) + آزمون زندهٔ مرورگر (WAV ۳٫۷ث)
      + آزمون زندهٔ دسکتاپ (WAV ۸٫۳ث) + ۱۷۷ pytest + ۷۱ Node + AppTest

۶ دارایی: Full-Project / Portable-Web / Mobile-App-PWA / تک‌فایل /
APK (versionCode 24) / PDF مستندات v2.12.0.
پیش‌نیاز: build_portable_zip.py + build_apk.sh + build_singlefile.py + PDF اجرا شده باشند.
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
VERSION = "2.12.0"


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
apk = ROOT / "android" / "build" / "LabelVoice-Android-2.12.0.apk"
pdf = ROOT / "docs" / "LabelVoice-Documentation-v2.12.0.pdf"

ASSETS = [
    (full_zip, f"LabelVoice-v{VERSION}-Full-Project.zip",
     "کل پروژه — دسکتاپ + وب/موبایل + اندروید + مدل صوتی Piper در models/tts + آزمون‌های TTS لوکال"),
    (portable_zip, f"LabelVoice-v{VERSION}-Portable-Web.zip",
     "بستهٔ قابل حمل بدون پایتون — START-HERE + تک‌فایل (با موتور صوتی تعبیه‌شده) + وب‌اپ + لانچرها"),
    (mobile_zip, f"LabelVoice-v{VERSION}-Mobile-App-PWA.zip",
     "اپ موبایل PWA — مدل صوتی Piper باندل‌شده در vendor/tts؛ کش lbr-mobile-v25؛ کاملاً آفلاین"),
    (singlefile, f"label-reader-singlefile-v{VERSION}.html",
     "تک‌فایل آفلاین قابل حمل — موتور OCR + دادهٔ زبان + مدل صوتی Piper و موتور WASM تعبیه‌شده (~۶۰MB)"),
    (apk, f"LabelVoice-v{VERSION}-Android.apk",
     "نسخهٔ نصب‌پذیر اندروید (versionCode 24، versionName 2.12.0) — صدا کاملاً لوکال؛ کلید امضای جدید است (بخوانید یادداشت نصب)"),
    (pdf, "LabelVoice-Documentation-v2.12.0.pdf",
     "مستندات فنی v2.12.0 — بخش «مدل صوتی دانلودشدهٔ پروژه» + WBS به‌روز + تاریخچه"),
]

BODY = """## برچسب‌خوان هوشمند دارو و محصولات — نسخه ۲.۱۲.۰

**توسعه و طراحی: حمید جلیلوند و نوید بدری**

### 🔊 درخواست کاربر: «یک مدل دانلود کن و در فایل‌های پروژه قرار بده؛ به‌صورت لوکال از مدل در برنامه استفاده کن — برای همه موارد، نه سرویس آنلاین» ✅

بازخورد کاربر دقیقاً همین بود: صداهای «فرید» و «دلارا» در v2.11.0 صداهای **سرویس آنلاین Microsoft Edge** بودند، نه مدل باندل‌شده. این نسخه آن را ریشه‌ای حل می‌کند:

**مدل انتخابی: Piper VITS — `fa_IR-amir-medium`** (صدای مردانهٔ فارسی؛ منبع: [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices) v1.0.0 — لایسنس MIT)

| رابط | محل مدل | موتور اجرا |
|---|---|---|
| دسکتاپ (Streamlit) | `models/tts/piper-fa_IR-amir/` — model.onnx (fp32 ۶۳MB) + model.int8.onnx (۱۸٫۶MB) + tokens.txt + espeak-ng-data (۳۵۵ فایل) | sherpa-onnx 1.12.40 (`label_reader/tts/local_provider.py`) |
| وب / PWA / تک‌فایل | `mobile-app/vendor/tts/` — مدل int8 + پیکربندی Piper | onnxruntime-web 1.30 (WASM/SIMD) + piper-phonemize WASM |
| APK اندروید | همان `vendor/tts/` داخل assets | همان موتور WASM در زمینهٔ امن `appassets` |

**بهینه‌سازی اندازه:** دادهٔ فونِم‌ساز espeak از ۱۸٫۰۸MB به **۱٫۲۸MB** تریم شد (۴۹۴ → ۳۸۳ فایل؛ فقط fa+en + جداول مشترک phon*/intonations/lang/voices) — اسکریپت `scripts/trim_piper_wasm_data.py` با بازنویسی متادیتای تعبیه‌شده در گلو.

**حذف کامل مسیرهای آنلاین (خط قرمز v2.12.0):**
- `label_reader/tts/edge_provider.py` و `gtts_provider.py` حذف شدند؛ `requirements.txt` → `sherpa-onnx==1.12.40` (نسخهٔ 2.x فونِم‌ساز داخلی ندارد)
- اندپوینت `POST /api/tts` از پل محلی حذف شد (پل فقط OCR است)
- چک‌باکس «رضایت ارسال به سرویس ابری» از هر دو رابط حذف شد — دیگر چیزی برای ارسال وجود ندارد
- کلاینت WebSocket مستقیم Edge (پورت پروتکل edge-tts) حذف شد
- هک UA «Edg/» از MainActivity حذف شد — UA استاندارد WebView
- هیچ استفاده‌ای از speechSynthesis / TextToSpeech گوشی (از v2.11.0 همچنان برقرار)

**سرعت خوانش:** (−۱۵٪ تا +۲۰٪) در همهٔ رابط‌ها با قاعدهٔ پاریتی (rate → length_scale) پایتون ⇄ JS.

### 🧪 اثبات واقعی (نه ادعا)

- **راستی‌آزمایی کوانتیزهٔ int8:** نسبت مدت خوانش به fp32 برای دو جملهٔ فارسی = ۱٫۰۰۶ و ۱٫۰۷۶ (بازهٔ پذیرش ۰٫۷۵–۱٫۳) — `models/tts/piper-fa_IR-amir/quantization-report.json` + شواهد صوتی در `scripts/evidence_v2120/`
- **آزمون زندهٔ مرورگر (Chromium واقعی):** سنتز موفق WAV فارسی ۳٫۷ ثانیه‌ای با موتور WASM و دادهٔ espeak تریم‌شده — `scripts/evidence_v2120/browser_tts_fa.wav`
- **آزمون زندهٔ دسکتاپ:** WAV ۸٫۳ ثانیه‌ای از پاسخ واقعی خط لوله (`desktop_tts_fa.wav`)
- **تک‌فایل:** موتور صوتی (مدل + WASM‌ها) به‌صورت data: URL داخل همان HTML تعبیه شد (~۶۰MB) و آزمون زندهٔ سنتز آن هم پاس شد
- **آزمون‌ها:** ۱۷۷ pytest + ۷۱ Node (شامل ۹ آزمون جدید `tests-js/tts_local_v2120.js`: پاریتی نرخ، سرصفحهٔ WAV، باندل دارایی، خط قرمز «بدون سرویس آنلاین») + AppTest استریم‌لیت — همه پاس
- **مستندات هم‌راستا:** README + ARCHITECTURE + INSTALL + LIMITATIONS + help_content.py + help.js + documentation.html + START-HERE + README موبایل + PDF جدید (بخش ۴: مدل صوتی لوکال)

### ⚠️ مهم برای نصب APK

**کلید امضای این نسخه جدید است** (محیط ساخت بازسازی شده) — اگر نسخهٔ قبلی را نصب دارید، ابتدا **Uninstall** کنید و سپس v2.12.0 را نصب نمایید. (versionCode 24، versionName 2.12.0)

### نصب
- **بدون پایتون:** `Portable-Web.zip` → `START-WINDOWS.bat`
- **دسکتاپ:** `pip install -r requirements.txt` → `streamlit run app.py` (مدل صوتی داخل پروژه است؛ اینترنت لازم ندارد)
- **موبایل/وب:** `Mobile-App-PWA.zip` → `START-WINDOWS.bat` — صدا بدون پل و بدون اینترنت کار می‌کند
- **تک‌فایل:** `label-reader-singlefile-v2.12.0.html` — دابل‌کلیک؛ هم OCR هم صدا کاملاً آفلاین
- **APK:** نصب مستقیم (پس از Uninstall نسخهٔ قبلی — کلید امضای جدید)

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
        "name": f"LabelVoice {tag} — مدل صوتی دانلودشده در فایل‌های پروژه (Piper فارسی، کاملاً لوکال)",
        "body": BODY, "draft": False, "prerelease": False}).encode())
    rel_id = rel["id"]
    print(f"Release id={rel_id}")

    for path, name, _ in ASSETS:
        data = path.read_bytes()
        boundary = "----labelvoice2120boundary"
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

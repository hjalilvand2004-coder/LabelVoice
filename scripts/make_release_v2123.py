#!/usr/bin/env python3
"""انتشار Release v2.12.2 — توکن فقط گذرا (GH_TOKEN یا urlsplit از URL ریموت)؛ هرگز ذخیره نمی‌شود.

v2.12.2 = مستندات مدل‌ها (بر اساس بررسی و تحلیل صورت گرفته):
  (۱) جدول «نوع، نام و مسیر فایل هر مدل» — باندل‌شده در پروژه / نصب جداگانه
      تک‌منبع حقیقت: label_reader/models_info.py → models_paths_markdown_fa()
  (۲) بازنویسی همهٔ مستندات با لحن «بر اساس بررسی و تحلیل …» (حذف نقل‌قول‌های درخواست/گزارش)
  (۳) حذف بازمانده‌های قدیمی: Web Speech API در جدول مدل‌ها + راهنمای کهنهٔ Edge در INSTALL
۶ دارایی: Full-Project / Portable-Web / Mobile-App-PWA / تک‌فایل /
APK (versionCode 27) / PDF مستندات v2.12.2.
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
VERSION = "2.12.3"


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
apk = ROOT / "android" / "build" / "LabelVoice-Android-2.12.3.apk"
pdf = ROOT / "docs" / "LabelVoice-Documentation-v2.12.3.pdf"

ASSETS = [
    (full_zip, f"LabelVoice-v{VERSION}-Full-Project.zip",
     "کل پروژه — دسکتاپ + وب/موبایل + اندروید + مدل صوتی Piper در models/tts + رجیستری مدل‌ها با مسیر فایل‌ها"),
    (portable_zip, f"LabelVoice-v{VERSION}-Portable-Web.zip",
     "بستهٔ قابل حمل بدون پایتون — START-HERE + تک‌فایل (موتور صوتی تعبیه‌شده) + وب‌اپ (SW v28) + لانچرها + _APK"),
    (mobile_zip, f"LabelVoice-v{VERSION}-Mobile-App-PWA.zip",
     "اپ موبایل PWA — مدل صوتی Piper باندل‌شده در vendor/tts؛ کش lbr-mobile-v28؛ کاملاً آفلاین"),
    (singlefile, f"label-reader-singlefile-v{VERSION}.html",
     "تک‌فایل آفلاین قابل حمل — OCR + دادهٔ زبان + مدل صوتی Piper و موتور WASM تعبیه‌شده (~۶۰MB) + جدول مسیر مدل‌ها در راهنما"),
    (apk, f"LabelVoice-v{VERSION}-Android.apk",
     "نسخهٔ نصب‌پذیر اندروید (versionCode 27، versionName 2.12.2) — صدا کاملاً لوکال؛ ارتقای مستقیم از v2.12.0/v2.12.1 (همان کلید امضا)"),
    (pdf, f"LabelVoice-Documentation-v{VERSION}.pdf",
     "مستندات فنی v2.12.2 — کارت ۵ بخش ۴: جدول «نوع، نام و مسیر فایل هر مدل» + تاریخچهٔ کامل"),
]

BODY = """## برچسب‌خوان هوشمند دارو و محصولات — نسخه ۲.۱۲.۳

**توسعه و طراحی: حمید جلیلوند و نوید بدری**

### 🔊 رفع خطای پخش صوتی در بستهٔ پرتیبل ✅

بر اساس بررسی و تحلیل صورت گرفته روی گزارش «تولید صدا ناموفق بود. فایل‌های vendor/tts باید کنار برنامه باشند و صفحه از طریق سرور محلی باز شود»، دو علت مستقل شناسایی و رفع شد:

**۱) MIME نادرست ماژول mjs در سرور محلی ویندوز** (علتِ اجرای با START-WINDOWS.bat): جدول MIME سرور داخلی (`server-windows.ps1`) فایل‌های `.mjs` را با `application/octet-stream` می‌فرستاد؛ مرورگرها import ماژول ES با MIME غیرجاوااسکریپتی را رد می‌کنند و onnxruntime-web هنگام ساخت نشست، `ort-wasm-simd-threaded.mjs` را import می‌کند — در نتیجه راه‌اندازی موتور صوتی بی‌صدا شکست می‌خورد. اکنون هر دو نسخهٔ سرور (پرتیبل و Full-Project) `.mjs` را با `text/javascript` سرو می‌کنند (+ تعریف صریح `.onnx`/`.data`/`.txt`) و آزمون رگرسیون MIME به آزمون‌های Node اضافه شد.

**۲) بازکردن مستقیم HTML از Explorer — حالت file://** (علتِ دوبارکلیک): در این حالت مرورگر `fetch()` فایل‌های مدل کنار برنامه را مسدود می‌کند. اکنون موتور صوتی (`js/tts.js`) پروتکل file:// را تشخیص می‌دهد و راهنمای دقیق فارسی می‌دهد (اجرای START-WINDOWS.bat یا استفاده از تک‌فایل)، همهٔ خطاهای fetch/راه‌اندازی موتور با پیام فارسیِ قابل‌اقدام پوشش شده‌اند، START-HERE در حالت file:// هشدار سرخ درج می‌کند و متن گمراه‌کنندهٔ لانچر اصلاح شد — حالت بدون سرور یعنی تک‌فایل، نه webapp/index.html.

**۳) رفع باگ سازندهٔ تک‌فایل:** خطای نحوی prelude کارگر OCR (`__LBR_U[m[1]]`) اصلاح شد و تعبیهٔ دارایی‌های صوتی نسخه‌مستقل شد (قبلاً به تگ `?v=2.12.2` سخت‌کد شده بود) + بررسی نهایی سخت‌گیرانهٔ تعبیه (data: URL واقعی مدل).

### 🧪 شواهد E2E (scripts/evidence_v2123)

- سرور با MIME نادرست ← بازتولید همان شکست با پیام شفاف فارسی جدید («Failed to fetch dynamically imported module: …/ort-wasm-simd-threaded.mjs»)
- سرور با MIME اصلاح‌شده ← سنتز موفق لوکال: WAV ۹۳٫۷KB در ۷٫۰ ثانیه
- تک‌فایل با file:// (بدون سرور) ← سنتز موفق: WAV ۱۰۸٫۶KB — موتور و مدل کاملاً تعبیه‌شده

### 🔊 مدل صوتی لوکال — بی‌تغییر و کامل (v2.12.0 به بعد)

**Piper VITS — `fa_IR-amir-medium`** (منبع: rhasspy/piper-voices v1.0.0 — لایسنس MIT) — فایل‌های مدل داخل فایل‌های پروژه؛ دسکتاپ با sherpa-onnx 1.12.40 و مرورگر/WebView/APK با onnxruntime-web (WASM/SIMD) — بدون اینترنت، بدون سرویس ابری، بدون TTS گوشی.

### 📦 راهنمای رفع مشکل برای کاربران نسخهٔ قبلی

اگر در نسخهٔ پرتیبل قبلی با زدن «پخش صوتی پاسخ» پیام خطا می‌دیدید:
- **بستهٔ جدید v2.12.3 را دانلود و در پوشهٔ جدید استخراج کنید** → `START-WINDOWS.bat` (خط «Folder version» باید v2.12.3 را نشان دهد)
- یا بدون دانلود: فایل `label-reader-singlefile.html` را دوبارکلیک کنید — موتور صوتی و مدل داخل خودش تعبیه شده و با دوبارکلیک هم صدا دارد

### 🧪 آزمون‌ها

۱۷۷ pytest + ۷۲ Node (شامل ۹ آزمون TTS لوکال + ۱ آزمون رگرسیون MIME) + AppTest استریم‌لیت — همه پاس.

### 📦 نسخه‌ها

کش سرویس‌ورکر → `lbr-mobile-v28` · APK versionCode 27 / versionName 2.12.3 (همان کلید امضای v2.12.0+ — ارتقای مستقیم) · تک‌فایل بازساخت (~۶۰MB) · هر سه ZIP از مخزن به‌روز بازتولید شدند · PDF v2.12.3 (۱۳ صفحه).

### نصب

- **بدون پایتون:** `LabelVoice-v2.12.3-Portable-Web.zip` → استخراج در **پوشهٔ جدید** → `START-WINDOWS.bat` (خط «Folder version» باید v2.12.3 را نشان دهد)
- **دسکتاپ:** `pip install -r requirements.txt` → `streamlit run app.py` (مدل صوتی داخل پروژه؛ اینترنت لازم ندارد)
- **موبایل/وب:** `LabelVoice-v2.12.3-Mobile-App-PWA.zip` → `START-WINDOWS.bat`
- **تک‌فایل:** `label-reader-singlefile-v2.12.3.html` — دابل‌کلیک؛ OCR و صدا کاملاً آفلاین
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
        boundary = "----labelvoice2123boundary"
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

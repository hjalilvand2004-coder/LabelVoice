#!/usr/bin/env python3
"""انتشار Release v2.11.0 — توکن فقط گذرا (محیط GH_TOKEN یا urlsplit از URL ریموت)؛ هرگز ذخیره نمی‌شود.

v2.11.0 = درخواست کاربر: «مدل متداول TTS با صدای فارسی در برنامه؛ موبایل هم از
همان مدل بخواند — از قابلیت گفتار به صدای گوشی استفاده نکن»
  (۱) مدل مشترک همهٔ رابط‌ها: صداهای نورال فارسی Microsoft Edge (Farid/Dilara)
  (۲) پل دسکتاپ: POST /api/tts در bridge.py — همان کد label_reader/tts (رضایت صریح)
  (۳) کلاینت مستقیم: js/tts.js — پورت کامل پروتکل edge-tts 7.3.1 (توکن Sec-MS-GEC v2
      با پاریتی بیتی ۶ وکتور + آزمون زندهٔ end-to-end: ۳۳KB MP3 فارسی)
  (۴) ممیزی زندهٔ هدرها: فقط UA با «Edg/» پذیرفته می‌شود → مستقیم فقط Edge/WebView-APK
  (۵) حذف speechSynthesis از app.js و پل بومی TextToSpeech از MainActivity

۶ دارایی: Full-Project / Portable-Web / Mobile-App-PWA / تک‌فایل /
APK (versionCode 23) / PDF مستندات v2.11.0 (۱۰ صفحه — بخش TTS مشترک).
پیش‌نیاز: build_portable_zip.py + build_apk.sh + build_singlefile.py اجرا شده باشند.
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
VERSION = "2.11.0"


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
apk = ROOT / "android" / "build" / "LabelVoice-Android-2.11.0.apk"
pdf = ROOT / "docs" / "LabelVoice-Documentation-v2.11.0.pdf"

ASSETS = [
    (full_zip, f"LabelVoice-v{VERSION}-Full-Project.zip",
     "کل پروژه — دسکتاپ + وب/موبایل + اندروید + پل OCR/TTS + آزمون‌های پاریتی TTS (tests-js/tts_v2110.js)"),
    (portable_zip, f"LabelVoice-v{VERSION}-Portable-Web.zip",
     "بستهٔ قابل حمل بدون پایتون — START-HERE + تک‌فایل + وب‌اپ + لانچرهای پل"),
    (mobile_zip, f"LabelVoice-v{VERSION}-Mobile-App-PWA.zip",
     "اپ موبایل PWA — همان مدل صوتی دسکتاپ (Edge TTS فارسی)؛ کش lbr-mobile-v24؛ js/tts.js جدید"),
    (singlefile, f"label-reader-singlefile-v{VERSION}.html",
     "تک‌فایل آفلاین قابل حمل — موتور OCR و دادهٔ زبان تعبیه‌شده + کلاینت Edge TTS"),
    (apk, f"LabelVoice-v{VERSION}-Android.apk",
     "نسخهٔ نصب‌پذیر اندروید (versionCode 23، versionName 2.11.0) — همان کلید امضای v2.10.1؛ فقط نصب‌کنندگان v2.10.0 یا قدیمی‌تر باید قبلی را Uninstall کنند"),
    (pdf, "LabelVoice-Documentation-v2.11.0.pdf",
     "مستندات فنی v2.11.0 (۱۰ صفحه) — بخش جدید «مدل صوتی مشترک دسکتاپ و موبایل» + تاریخچه"),
]

BODY = """## برچسب‌خوان هوشمند دارو و محصولات — نسخه ۲.۱۱.۰

**توسعه و طراحی: حمید جلیلوند و نوید بدری**

### 🔊 درخواست کاربر: «یک مدل متداول TTS با صدای فارسی؛ موبایل هم از همان مدل بخواند — از قابلیت گفتار به صدای گوشی استفاده نکن» ✅

**مدل انتخابی: صداهای نورال فارسی Microsoft Edge** (همان موتور دسکتاپ از ابتدای پروژه):
- `fa-IR-FaridNeural` «فرید» (مرد) و `fa-IR-DilaraNeural` «دلارا» (زن) + جایگزین خودکار gTTS
- اکنون **یک مدل مشترک در هر سه رابط** — دسکتاپ، وب/موبایل (PWA/تک‌فایل) و اندروید

**مسیر ۱ — پل دسکتاپ `POST /api/tts`** (`label_reader/bridge.py`):
ساخت mp3 دقیقاً با همان کد پایتون دسکتاپ (`label_reader/tts`). رضایت صریح (`consent=true`) الزام است؛ سقف ۶۴KB بدنه و ۶۰۰۰ نویسه؛ اعتبارسنجی صدا/سرعت؛ وضعیت TTS در `GET /ping`؛ بدون لاگ محتوا. آزمون زنده پاس شد.

**مسیر ۲ — کلاینت مستقیم `mobile-app/js/tts.js`** (جدید):
پیاده‌سازی کامل پروتکل edge-tts 7.3.1 در جاوااسکریپت شامل الگوریتم توکن **Sec-MS-GEC v2** (SHA-256 اصلاح‌شدهٔ وابسته به داده + دیجست CS64). **پاریتی بیتی با پایتون با ۶ وکتور آزمون** (`tests-js/tts_v2110.js`)؛ آزمون زندهٔ end-to-end با سرویس واقعی: **۳۳٫۵KB MP3 فارسی** تولید شد.

**ممیزی زندهٔ هدرها (یافتهٔ مهم):**
سرویس مایکروسافت فقط درخواست‌های با UA حاوی «Edg/» را می‌پذیرد (کروم/فایرفاکس/بدون هدر = HTTP 403؛ Origin و Cookie بی‌اثر). نتیجه:
- مسیر مستقیم در **مرورگر Microsoft Edge** و **WebView اندروید** فعال است (نشانهٔ `Edg/143.0.3650.75` به UA اضافه شد)
- در بقیهٔ مرورگرها «پل دسکتاپ» راه مطمئن است؛ پیام راهنمای شفاف نمایش داده می‌شود

**حذف کامل TTS گوشی:** `speechSynthesis` از `js/app.js` و پل بومی `TextToSpeech` از `MainActivity.java` حذف شد. رابط موبایل: چک‌باکس رضایت + انتخاب صدا (فرید/دلارا) + سرعت خوانش (−۱۵٪ تا +۲۰٪) با ذخیرهٔ محلی.

### 🧪 اثبات واقعی (نه ادعا)

- **پاریتی توکن:** ۶ وکتور پایتون (edge-tts 7.3.1) ⇄ JS — مطابقت بیتی کامل (digest + CS64 + توکن نهایی)
- **زندهٔ end-to-end:** کلاینت واقعی js/tts.js با سرویس واقعی مایکروسافت — ۳۳,۵۰۴ بایت MP3 فارسی
- **آزمون زندهٔ هدرها:** ماتریس UA/Origin/Cookie (۶ حالت) — فقط «Edg/» پذیرفته می‌شود
- **پل:** `POST /api/tts` بدون رضایت → ۴۰۳ با پیام فارسی (آزمون زنده)؛ ۱۷۶ pytest + ۸۰ Node (شامل وکتورها) + ۲ E2E جدید — همه پاس
- مستندات: README + ARCHITECTURE + INSTALL + LIMITATIONS + help_content.py + help.js + documentation.html + START-HERE + PDF جدید ۱۰ صفحه‌ای — همه هم‌راستا

### ⚠️ مهم برای نصب APK

کلید امضای همین کلیدِ v2.10.1 است (نصب مستقیم روی v2.10.1 بدون حذف). اگر v2.10.0 یا قدیمی‌تر دارید، ابتدا **Uninstall** کنید. (versionCode 23، versionName 2.11.0)

### نصب
- **بدون پایتون:** `Portable-Web.zip` → `START-WINDOWS.bat`
- **دسکتاپ:** `pip install -r requirements.txt` → `streamlit run app.py`
- **موبایل/وب:** `Mobile-App-PWA.zip` → `START-WINDOWS.bat` + برای صدا `START-BRIDGE.bat` را هم روی رایانه اجرا کنید (یا صفحه را در مرورگر Edge باز کنید)
- **تک‌فایل:** `label-reader-singlefile-v2.11.0.html` — دابل‌کلیک
- **APK:** نصب مستقیم؛ برای صدا اینترنت گوشی روشن باشد

### یادآوری محدوده محصول
این ابزار فقط می‌گوید «روی بسته چه نوشته شده است»؛ تشخیص دارو، تجویز، تعیین مقدار مصرف یا توصیه پزشکی انجام نمی‌دهد. «قدرت درج‌شده» هرگز «دوز مصرف» نیست.
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
        "name": f"LabelVoice {tag} — مدل صوتی مشترک دسکتاپ و موبایل (Edge TTS فارسی، بدون TTS گوشی)",
        "body": BODY, "draft": False, "prerelease": False}).encode())
    rel_id = rel["id"]
    print(f"Release id={rel_id}")

    for path, name, _ in ASSETS:
        data = path.read_bytes()
        boundary = "----labelvoice2110boundary"
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

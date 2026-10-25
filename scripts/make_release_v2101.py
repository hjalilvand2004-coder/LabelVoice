#!/usr/bin/env python3
"""انتشار Release v2.10.1 — توکن فقط گذرا (محیط GH_TOKEN یا urlsplit از URL ریموت)؛ هرگز ذخیره نمی‌شود.

v2.10.1 = رفع بازخورد کاربر: «START-WINDOWS نسخهٔ قبلی را نشان می‌دهد / START-HERE با خطا اجرا می‌شود»
  (۱) فلگ پاکسازی SW در START-HEADER وابسته به نسخه شد
  (۲) رفرش خودکار یک‌باره: SW جدید هنگام activate کلاینت‌های کهنه را navigate می‌کند (اثبات E2E)
  (۳) لانچر قابل‌حمل چیدمان Full-Project را تشخیص می‌دهد و به mobile-app تحویل می‌دهد + اصلاح چیپ‌های نسخهٔ جامانده

۶ دارایی: Full-Project / Portable-Web / Mobile-App-PWA / تک‌فایل /
APK (versionCode 22) / PDF مستندات (بدون تغییر محتوایی نسبت به v2.10.0).
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
VERSION = "2.10.1"


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
apk = ROOT / "android" / "build" / "LabelVoice-Android-2.10.1.apk"
pdf = ROOT / "docs" / "LabelVoice-Documentation-v2.10.0.pdf"

ASSETS = [
    (full_zip, f"LabelVoice-v{VERSION}-Full-Project.zip",
     "کل پروژه — دسکتاپ + وب/موبایل + اندروید + اسکریپت‌ها + آزمون‌های E2E درمان SW (e2e_sw_heal_v2101)"),
    (portable_zip, f"LabelVoice-v{VERSION}-Portable-Web.zip",
     "بستهٔ قابل حمل بدون پایتون — رفع «لانچر نسخهٔ قدیم را نشان می‌دهد» + راهنمای چیدمان"),
    (mobile_zip, f"LabelVoice-v{VERSION}-Mobile-App-PWA.zip",
     "اپ موبایل PWA — رفرش خودکار یک‌باره هنگام به‌روزرسانی سرویس‌ورکر (کش lbr-mobile-v23)"),
    (singlefile, f"label-reader-singlefile-v{VERSION}.html",
     "تک‌فایل آفلاین قابل حمل — موتور OCR و دادهٔ زبان تعبیه‌شده"),
    (apk, f"LabelVoice-v{VERSION}-Android.apk",
     "نسخهٔ نصب‌پذیر اندروید (versionCode 22، versionName 2.10.1) — کلید امضای جدید؛ Uninstall نسخهٔ قبل لازم است"),
    (pdf, "LabelVoice-Documentation-v2.10.0.pdf",
     "مستندات فنی — در این پچ محتوای معماری تغییر نکرده؛ همان PDF v2.10.0 (تاریخچهٔ v2.10.1 در documentation.html)"),
]

BODY = """## برچسب‌خوان هوشمند دارو و محصولات — نسخه ۲.۱۰.۱ (پچ)

**توسعه و طراحی: حمید جلیلوند و نوید بدری**

### 🔧 بازخورد کاربر: «START-WINDOWS نسخهٔ قبلی را نشان می‌دهد / START-HERE با خطا اجرا می‌شود» ✅

ممیزی ریشه‌ای **سه علت مستقل** یافت و هر سه رفع شد:

1. **فلگ پاکسازی سرویس‌ورکر در START-HERE ثابت بود** (`lv_launcher_cleaned_for_v2`) — پاکسازیِ «یک‌بار در هر مرورگر» فقط برای اولین نسخه اجرا می‌شد؛ SW استخراج قبلی روی همان `127.0.0.1:8765` باقی می‌ماند و رابط کهنه را از کش سرو می‌کرد. فلگ اکنون وابسته به نسخه است (`lv_launcher_cleaned_v2_10_1`).
2. **صفحهٔ اولِ سرو‌شده توسط SW قدیمی خودبه‌خود تازه نمی‌شد** — اکنون خودِ سرویس‌ورکرِ جدید هنگام activate (فقط در آپدیت، نه نصب اول) کلاینت‌های بازِ با DOM کهنه را `client.navigate` می‌کند؛ صفحه بدون هیچ رفرش دستی تازه می‌شود. + درمان کلاینت‌ساید مکمل در app.js (controllerchange با گارد بازدید اول و sessionStorage).
3. **چیدمان Full-Project** — لانچر `portable\\START-WINDOWS.bat` در پوشهٔ کامل پروژه صفحه‌ای را سرو می‌کرد که لینک‌هایش وجود نداشتند (خطای Page not found) و `portable\\VERSION.txt` قدیمی مانده بود (هشدار کاذب «کپی قدیمی»). اکنون لانچر چیدمان را تشخیص می‌دهد و به `mobile-app` تحویل می‌دهد؛ نسخهٔ پوشه 2.10.1 است؛ START-HERE هم راهنمای صریح دارد.

### 🧪 اثبات واقعی (نه ادعا)

- **E2E درمان SW** (`scripts/e2e_sw_heal_v2101.js`): بازدید اول با SW کهنه → چیپ `OLD-STALE` (بازتولید دقیق باگ) → انتشار نسخهٔ جدید روی همان origin → ناوبری مجدد → چیپ **«۲.۱۰.۱» بدون هیچ رفرش دستی**، SW فعال v23، بدون خطای صفحه — **PASS**
- **E2E چیدمان‌ها** (`scripts/e2e_starthere_v2101.js`): START-HERE در هر دو چیدمان (Portable و Full-Project) با چیپ درست، راهنمای لانچر درست و بدون خطای کنسول — **PASS**
- ۱۷۰ pytest + ۷۰ Node — همه پاس

### 🧹 پاکسازی نسخه‌های جامانده در همین پچ

- چیپ هیروی START-HERE: «۲.۷.۰» ← «۲.۱۰.۱» · چیپ «درباره» راهنمای موبایل: «۱.۴.۰» ← «۲.۱۰.۱»
- `mobile-app/VERSION.txt` و `portable/VERSION.txt`: هماهنگ با 2.10.1

### ⚠️ مهم برای نصب APK

کلید امضای این نسخه جدید است (محیط ساخت ریست شده) — ابتدا نسخهٔ قبلی را **Uninstall** کنید. (versionCode 22، versionName 2.10.1)

### نصب
- **بدون پایتون:** `Portable-Web.zip` → `START-WINDOWS.bat` (اگر داخل پوشهٔ کامل پروژه اجرا شود، خودکار به لانچر درست تحویل می‌دهد)
- **دسکتاپ:** `pip install -r requirements.txt` → `streamlit run app.py`
- **تک‌فایل:** `label-reader-singlefile-v2.10.1.html` — دابل‌کلیک، بدون سرور
- **نکتهٔ به‌روزرسانی PWA:** دیگر لازم نیست بعد از آپدیت دستی رفرش کنید؛ SW جدید خودش صفحه را تازه می‌کند

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
        "name": f"LabelVoice {tag} — رفع «لانچر نسخهٔ قدیم را نشان می‌دهد» (SW خودترمیم + چیدمان Full-Project)",
        "body": BODY, "draft": False, "prerelease": False}).encode())
    rel_id = rel["id"]
    print(f"Release id={rel_id}")

    for path, name, _ in ASSETS:
        data = path.read_bytes()
        boundary = "----labelvoice2101boundary"
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

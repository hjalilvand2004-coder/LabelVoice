#!/usr/bin/env python3
"""انتشار Release v2.7.0 — توکن فقط گذرا از ورودی استاندارد؛ هرگز ذخیره نمی‌شود.

v2.7.0 = «دیدن کار OpenCV و خوانش خام OCR» اکنون در وب/موبایل هم
(بازخورد کاربر: «در نسخهٔ جدید این مهم هنوز انجام نشده» — چون v2.6.0 فقط دسکتاپ بود
و کاربر از START-WINDOWS.bat / نسخهٔ موبایل استفاده می‌کرد).

هر ۵ دارایی تازه ساخته می‌شوند:
  Full-Project / Portable-Web / Mobile-App-PWA / تک‌فایل / APK (versionCode 18)
پیش‌نیاز: python3 scripts/build_portable_zip.py --apk android/build/LabelVoice-Android-2.7.0.apk
"""
import json
import os
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

REPO = "hjalilvand2004-coder/LabelVoice"
TOKEN = os.environ.get("GH_TOKEN") or sys.stdin.readline().strip()
VERSION = "2.7.0"
ROOT = Path("/home/z/my-project/labelvoice-clone")
OUT = Path("/home/z/my-project/download")
OUT.mkdir(parents=True, exist_ok=True)


def is_ascii_name(name: str) -> bool:
    return all(ord(c) < 128 for c in name)


# ---------- ۱) پروژهٔ کامل ----------
full_zip = OUT / f"LabelVoice-v{VERSION}-Full-Project.zip"
exclude_dirs = {".git", "__pycache__", ".pytest_cache", "node_modules",
                ".venv", "venv", "build", "keystore", "deploy-tmp"}
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

# ---------- ۳) دارایی‌های تازهٔ دیگر ----------
portable_zip = OUT / f"LabelVoice-v{VERSION}-Portable-Web.zip"
singlefile = ROOT / "mobile-app" / "label-reader-singlefile.html"
apk = ROOT / "android" / "build" / "LabelVoice-Android-2.7.0.apk"

ASSETS = [
    (full_zip, f"LabelVoice-v{VERSION}-Full-Project.zip",
     "کل پروژه — دسکتاپ (Streamlit) + وب/موبایل + اندروید + اسکریپت‌ها"),
    (portable_zip, f"LabelVoice-v{VERSION}-Portable-Web.zip",
     "بستهٔ قابل حمل بدون پایتون (START-HERE + تک‌فایل + webapp) — با قابلیت جدید 🔬"),
    (mobile_zip, f"LabelVoice-v{VERSION}-Mobile-App-PWA.zip",
     "اپ موبایل PWA — با بخش جدید «دیدن کار OpenCV و خوانش خام OCR»"),
    (singlefile, f"label-reader-singlefile-v{VERSION}.html",
     "تک‌فایل آفلاین قابل حمل — موتور OCR و دادهٔ زبان تعبیه‌شده — با قابلیت جدید 🔬"),
    (apk, f"LabelVoice-v{VERSION}-Android.apk",
     "نسخهٔ نصب‌پذیر اندروید (versionCode 18، versionName 2.7.0) — با قابلیت جدید 🔬"),
]

BODY = """## برچسب‌خوان هوشمند دارو و محصولات — نسخه ۲.۷.۰

**توسعه و طراحی: حمید جلیلوند و نوید بدری**

### 🔬 بازخورد کاربر: «در نسخهٔ جدید این مهم هنوز انجام نشده» ✅

قابلیت «دیدن خروجی مرحلهٔ OpenCV» که در v2.6.0 فقط در **نسخهٔ دسکتاپ (Streamlit)** بود، اکنون **در وب تک‌فایلی، PWA و اپ اندروید** هم دقیقاً به همان شکل وجود دارد. (اگر از `START-WINDOWS.bat` یا اپ موبایل استفاده می‌کنید، این نسخه را بگیرید.)

**۱) تصویر پس از هر عملیات پیش‌پردازش — روی همان تصویر اولیهٔ کاربر:**
- تصویر ورودی (پس از اعتبارسنجی) ← صاف‌کردن چرخش کم‌زاویه (با ذکر زاویه) ← حذف پس‌زمینه (با مختصات جعبه) ← چرخش ۹۰ درجهٔ خودکار در صورت خوانش کم‌بازده (با امتیازها) ← نسخه‌های پردازشی.
- نسخه‌های پردازشی: نسخهٔ اصلی بزرگ‌نمایی‌شده · خاکستری + CLAHE (کاشی ۸×۸، clip=۲) · تیزکردن Unsharp ۳×۳ · آستانه‌گذاری تطبیقی (پنجرهٔ ۳۱، C=۱۵) · متن روشن روی زمینهٔ تیره (پنجرهٔ ۵۱، C=۱۲) · جداسازی جوهر رنگی (۲۵۵ منهای بیشینهٔ کانال‌ها).
- هر گام: **تصویر خروجی همان عملیات** + توضیح فارسیِ عین عملیات + چیپ روشنایی میانگین و کنتراست همان تصویر.

**۲) خوانش خام OCR برای هر نسخهٔ پردازشی — قبل از ادغام بهترین-اول و رأی‌گیری:**
- متن پیوستهٔ خوانده‌شده از هر نسخه (قطعه‌ها به‌ترتیب مکان y,x) + تعداد قطعه + میانگین اطمینان.
- اگر نسخه‌ای چیزی نخواند، شفاف اعلام می‌شود.

#### تغییرات فنی
- `mobile-app/js/preprocess.js`: خروجی `trace` از `buildVariants` — هر واریانت با عنوان/توضیح فارسیِ عین عملیات + معیارها
- `mobile-app/js/app.js`: جمع‌آوری مسیر گام‌به‌گام (ورودی/deskew/برش/چرخش/واریانت‌ها) + خوانش خام هر نسخه + رندر گرید تصویری + تصاویر نسخه‌ها از گذرِ برنده
- `index.html` / `css/style.css`: بخش جدید «🔬 دیدن کار OpenCV و خوانش خام OCR» + راهنمای درون‌برنامه‌ای «trace»
- نتیجهٔ نهایی و گیت‌های کیفیت **هیچ تغییری نکرده‌اند** — این بخش فقط «نمایش» است.
- آزمون‌ها: ۱۳۸ pytest + ۶۴+۵ Node (۵ آزمون جدید `tests-js/trace_v270.js`) + ۱۸+۵ e2e + ران واقعی مرورگر با شاهد تصویری
- نسخه‌ها: APK versionCode 18 (versionName 2.7.0) · کش سرویس‌ورکر → `lbr-mobile-v19`

#### یادآوری
- نسخهٔ دسکتاپ (Streamlit) این قابلیت را از v2.6.0 دارد (بخش «🔬 دیدن کار OpenCV»).
- اگر APK قبلی (تا ۲.۴.۰) نصب است، ابتدا Uninstall کنید (کلید امضا از ۲.۵.۰ به بعد یکسان است).
"""

API = f"https://api.github.com/repos/{REPO}"


def req(method: str, url: str, data=None, headers=None):
    h = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}
    if headers:
        h.update(headers)
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(r, timeout=300) as resp:
        body = resp.read()
        return json.loads(body) if body else {}


def upload(url: str, path: Path, name: str) -> None:
    for attempt in range(1, 4):
        try:
            data = path.read_bytes()
            req("POST", url + f"?name={name}", data=data,
                headers={"Content-Type": "application/octet-stream",
                         "Content-Length": str(len(data))})
            print(f"  ✓ {name} ({len(data)//1024//1024}MB)")
            return
        except Exception as exc:  # noqa: BLE001
            print(f"  ! تلاش {attempt} ناموفق: {exc}")
            time.sleep(4 * attempt)
    raise SystemExit(f"آپلود {name} ناموفق ماند")


def main() -> None:
    for local, name, _note in ASSETS:
        p = Path(local)
        assert p.exists(), f"یافت نشد: {p}"

    commits = req("GET", f"{API}/commits/main")
    sha = commits["sha"]
    try:
        req("POST", f"{API}/git/refs", data=json.dumps({
            "ref": f"refs/tags/v{VERSION}", "sha": sha}).encode())
        print(f"✓ تگ v{VERSION} روی {sha[:9]}")
    except Exception as exc:  # noqa: BLE001
        print(f"! تگ: {exc}")

    rel = req("POST", f"{API}/releases", data=json.dumps({
        "tag_name": f"v{VERSION}",
        "name": f"LabelVoice v{VERSION} — دیدن کار OpenCV و خوانش خام OCR (وب/موبایل هم)",
        "body": BODY,
        "draft": False,
        "prerelease": False,
    }).encode())
    print(f"✓ Release id={rel['id']}: {rel['html_url']}")

    up_url = rel["upload_url"].split("{")[0]
    for local, name, _note in ASSETS:
        upload(up_url, Path(local), name)

    print("تمام شد:", rel["html_url"])


if __name__ == "__main__":
    main()

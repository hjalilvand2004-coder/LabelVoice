#!/usr/bin/env python3
"""انتشار Release v2.9.0 — توکن فقط گذرا از ورودی استاندارد؛ هرگز ذخیره نمی‌شود.

v2.9.0 = توسعهٔ کیفیت پایپ‌لاین OpenCV (حذف سایه/یکنواخت‌سازی نور + Unsharp +
دودویی مقیاس‌پذیر + لانسزوس + deskew پروفایلی + گیت هوشمند) + مستندات با
«ساختار شکست کار (WBS) و نقشهٔ درختی مخزن» در HTML + PDF (۱۸ صفحه).

۶ دارایی: Full-Project / Mobile-App-PWA / Portable-Web / تک‌فایل /
APK (versionCode 20) / PDF مستندات.
پیش‌نیاز: build_portable_zip.py + build_apk.sh + رندر PDF اجرا شده باشند.
"""
import json
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO = "hjalilvand2004-coder/LabelVoice"
TOKEN = os.environ.get("GH_TOKEN") or sys.stdin.readline().strip()
VERSION = "2.9.0"
ROOT = Path("/home/z/my-project/labelvoice-clone")
OUT = Path("/home/z/my-project/download")


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

# ---------- ۳) دارایی‌ها ----------
portable_zip = OUT / f"LabelVoice-v{VERSION}-Portable-Web.zip"
singlefile = ROOT / "mobile-app" / "label-reader-singlefile.html"
apk = ROOT / "android" / "build" / "LabelVoice-Android-2.9.0.apk"
pdf = ROOT / "docs" / "LabelVoice-Documentation-v2.9.0.pdf"

ASSETS = [
    (full_zip, f"LabelVoice-v{VERSION}-Full-Project.zip",
     "کل پروژه — دسکتاپ (Streamlit) + وب/موبایل + اندروید + اسکریپت‌ها + شواهد کیفیت OpenCV"),
    (portable_zip, f"LabelVoice-v{VERSION}-Portable-Web.zip",
     "بستهٔ قابل حمل بدون پایتون — OpenCV باکیفیت‌تر (حذف سایه/تیزکردن) + مستندات WBS"),
    (mobile_zip, f"LabelVoice-v{VERSION}-Mobile-App-PWA.zip",
     "اپ موبایل PWA — پیش‌پردازش یکنواخت‌سازی‌نور + بخش گام‌به‌گام OpenCV با دکمهٔ تصویر"),
    (singlefile, f"label-reader-singlefile-v{VERSION}.html",
     "تک‌فایل آفلاین قابل حمل — موتور OCR و دادهٔ زبان تعبیه‌شده"),
    (apk, f"LabelVoice-v{VERSION}-Android.apk",
     "نسخهٔ نصب‌پذیر اندروید (versionCode 20، versionName 2.9.0)"),
    (pdf, "LabelVoice-Documentation-v2.9.0.pdf",
     "مستندات فنی ۱۸ صفحه‌ای — معماری، WBS و درخت مخزن، فناوری‌ها، ارزیابی"),
]

BODY = """## برچسب‌خوان هوشمند دارو و محصولات — نسخه ۲.۹.۰

**توسعه و طراحی: حمید جلیلوند و نوید بدری**

### 🔬 بازخورد کاربر: «خروجی مرتبط با OpenCV کیفیت لازم را ندارد» ✅

پایپ‌لاین پیش‌پردازش از پایه تقویت شد (دسکتاپ و وب/موبایل هم‌راستا):

- **حذف سایه و یکنواخت‌سازی نور:** تابع جدید `flatten_illumination` — پس‌زمینهٔ روشنایی با `morphological close` (هستهٔ بیضوی ≈ ۱/۸ ضلع) برآورد و تصویر بر آن تقسیم می‌شود؛ سایه و گرادیان نور عکس موبایل حذف و متن پرکنتراست می‌شود. این مرحله داخل `gray_clahe` و `binarized` هم تزریق شد.
- **دو واریانت جدید:** `shadow_free` (حذف سایهٔ خالص) و `sharpened` (ماسک تیزکنندهٔ Unsharp) — مجموع ۷ نسخهٔ پردازشی.
- **دودویی مقیاس‌پذیر:** بلوک آستانه‌گذاری متناسب با ابعاد (۳۱..۹۱) + حذف نمک‌وفلفل با medianBlur.
- **بزرگ‌نمایی لانسزوس** (INTER_LANCZOS4) و **صاف‌کردن چرخش دومرحله‌ای** (minAreaRect + پالایش پروفایلی ±۲°).
- **گیت هوشمند:** واریانت‌های مکمل فقط وقتی خوانش اصلی ضعیف است (اطمینان < ۰٫۸) اجرا می‌شوند — عکس خوب سریع‌تر، عکس سخت با پوشش کامل.
- **اثبات واقعی** (`scripts/ab_opencv_v290.py` + شواهد `scripts/evidence_v290/`): روی نمونهٔ سایه‌دار ۵۸٪، خوانش original آشغال بود (اطمینان ۰٫۲۳) و واریانت‌های جدید «استامینوفن… تاریخ انقضا: ۱۴۰۶/۰۵» را با اطمینان تا ۰٫۷۴ خواندند.

### 📚 مستندات فنی به‌روز شد — WBS و ساختار درختی ✅

- بخش جدید **«ساختار شکست کار (WBS) و نقشهٔ درختی مخزن»**: ۱۲ بستهٔ کاری (WBS-1..12) با جدول نگاشت «الزام ← تحویل‌شدنی ← پوشه/فایل» + درخت کامل مخزن با کد WBS هر شاخه — در **سند HTML** (documentation.html، اکنون ۱۳ بخش) و **PDF ۱۸ صفحه‌ای** (دارایی ششم).
- بخش‌های OpenCV، فایل‌ها، فناوری‌ها، ارزیابی و تاریخچه به‌روز شد؛ نسخهٔ سند ۲.۹.۰.

### تغییرات فنی
- `label_reader/preprocess.py`: flatten_illumination + shadow_free + sharpened + binarize مقیاس‌پذیر + estimate_skew_angle پروفایلی + لانسزوس
- `label_reader/pipeline.py`: گیت اطمینان واریانت‌های مکمل (≥ ۰٫۸ → ردشدن)
- `mobile-app/js/preprocess.js`: flattenGray (تصویر انتگرالی) + تزریق به CLAHE/دودویی
- `label_reader/help_content.py` + `mobile-app/js/help.js`: به‌روزرسانی راهنماهای preprocess/trace
- نسخه‌ها: APK versionCode 20 (2.9.0) · کش سرویس‌ورکر → `lbr-mobile-v21` · تک‌فایل بازساخت
- آزمون‌ها: ۱۵۲ pytest (۱۴ جدید) + ۶۸ Node (۴ جدید) + ۱۸ E2E مرورگر — همه پاس

### نصب
- **بدون پایتون:** `Portable-Web.zip` → `START-WINDOWS.bat`
- **دسکتاپ:** `pip install -r requirements.txt` → `streamlit run app.py`
- **اندروید:** `Android.apk` (versionCode 20) — از ۲.۵.۰ به بعد درجا نصب می‌شود
- **تک‌فایل:** `label-reader-singlefile-v2.9.0.html` — دابل‌کلیک، بدون سرور

### یادآوری محدوده محصول
این ابزار فقط می‌گوید «روی بسته چه نوشته شده است»؛ تشخیص دارو، تجویز، تعیین مقدار مصرف یا توصیه پزشکی انجام نمی‌دهد. «قدرت درج‌شده» هرگز «دوز مصرف» نیست.
"""


def main() -> None:
    # بررسی وجود دارایی‌ها
    for path, name, _ in ASSETS:
        assert path.exists(), f"موجود نیست: {path}"
        print(f"✓ {name} ({path.stat().st_size/1e6:.1f} MB)")

    tag = f"v{VERSION}"
    # ساخت تگ از main فعلی
    try:
        gh("POST", "git/refs", json.dumps({
            "ref": f"refs/tags/{tag}",
            "sha": gh("GET", "git/ref/heads/main")["object"]["sha"]}).encode())
        print(f"تگ {tag} ساخته شد")
    except Exception as e:  # noqa: BLE001
        print("تگ (احتمالاً موجود):", e)

    rel = gh("POST", "releases", json.dumps({
        "tag_name": tag, "name": f"LabelVoice {tag} — کیفیت OpenCV + WBS و درخت مخزن",
        "body": BODY, "draft": False, "prerelease": False}).encode())
    rel_id = rel["id"]
    print(f"Release id={rel_id}")

    for path, name, _ in ASSETS:
        data = path.read_bytes()
        boundary = "----labelvoice290boundary"
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


if __name__ == "__main__":
    main()

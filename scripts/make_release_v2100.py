#!/usr/bin/env python3
"""انتشار Release v2.10.0 — توکن فقط گذرا (محیط GH_TOKEN یا استخراج از URL ریموت)؛ هرگز ذخیره نمی‌شود.

v2.10.0 = ممیزی مهندسی طبق دستورالعمل ارشد بینایی ماشین/OCR:
  F1 ایمنی عدد در ادغام (۵۰/۵۰۰ فقط با قرینهٔ هندسی)
  F2 حذف دوقلوی سرگردان (ریشهٔ الگوی «Keeping Keeping»)
  F5 پیش‌پردازش مشروط (diagnose_image) + فلگ بازگشت LBR_CONDITIONAL_VARIANTS
  F6 رکورد کامل خوانش خام (زبان/PSM/ابعاد/زمان/دلیل رد هر قطعه)

۶ دارایی: Full-Project / Portable-Web / Mobile-App-PWA / تک‌فایل /
APK (versionCode 21) / PDF مستندات.
پیش‌نیاز: build_portable_zip.py + build_apk.sh + رندر PDF اجرا شده باشند.
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
VERSION = "2.10.0"


def token_from_remote() -> str:
    tok = os.environ.get("GH_TOKEN")
    if tok:
        return tok.strip()
    url = subprocess.check_output(
        ["git", "-C", str(ROOT), "config", "--get", "remote.origin.url"],
        text=True).strip()
    from urllib.parse import urlsplit, unquote
    password = urlsplit(url).password  # https://user:token@github.com/...
    if password:
        return unquote(password)
    m = re.search(r":(ghp_[^@]+)@", url)  # پشتیبان: فقط توکن واقعی ghp_
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
apk = ROOT / "android" / "build" / "LabelVoice-Android-2.10.0.apk"
pdf = ROOT / "docs" / "LabelVoice-Documentation-v2.10.0.pdf"

ASSETS = [
    (full_zip, f"LabelVoice-v{VERSION}-Full-Project.zip",
     "کل پروژه — دسکتاپ (Streamlit) + وب/موبایل + اندروید + اسکریپت‌ها + شواهد ممیزی و ارزیابی"),
    (portable_zip, f"LabelVoice-v{VERSION}-Portable-Web.zip",
     "بستهٔ قابل حمل بدون پایتون — ادغام ایمن عدد + حذف دوقلو + پیش‌پردازش مشروط"),
    (mobile_zip, f"LabelVoice-v{VERSION}-Mobile-App-PWA.zip",
     "اپ موبایل PWA — پاریتی کامل قواعد جدید ادغام/دوقلو + رکورد خوانش خام"),
    (singlefile, f"label-reader-singlefile-v{VERSION}.html",
     "تک‌فایل آفلاین قابل حمل — موتور OCR و دادهٔ زبان تعبیه‌شده"),
    (apk, f"LabelVoice-v{VERSION}-Android.apk",
     "نسخهٔ نصب‌پذیر اندروید (versionCode 21، versionName 2.10.0) — کلید امضای جدید؛ Uninstall نسخهٔ قبل لازم است"),
    (pdf, "LabelVoice-Documentation-v2.10.0.pdf",
     "مستندات فنی — خلاصهٔ ممیزی + WBS و درخت مخزن + ارزیابی قبل/بعد"),
]

BODY = """## برچسب‌خوان هوشمند دارو و محصولات — نسخه ۲.۱۰.۰

**توسعه و طراحی: حمید جلیلوند و نوید بدری**

### 🔍 ممیزی مهندسی واقعی — نه فقط مستندات ✅

طبق دستورالعمل «مهندس ارشد بینایی ماشین، OCR فارسی/انگلیسی و تضمین کیفیت»، مسیر واقعی پردازش (نه ادعای مستندات) ممیزی شد؛ جدول «مشاهده/فرضیه/شاهد/آزمون/اصلاح» برای ۸ یافته تنظیم و ۴ اصلاح ریشه‌ای پیاده و آزمایش شد:

- **F1 — ایمنی عدد در ادغام:** قاعدهٔ قدیمی «عدد کوتاه داخل عدد بلند ⇒ جایگزینی» بدون بررسی اطمینان و هندسه بود (نقض خط قرمز ۵۰/۵۰۰)؛ اکنون قطعهٔ تمام‌عددی فقط با قرینهٔ هندسی (IoU/احتواء) و اطمینان بالاتر ادغام می‌شود — در پایتون و JS هم‌زمان.
- **F2 — دوقلوی سرگردان (ریشهٔ الگوی «Keeping Keeping»):** دو خوانش هم‌متن با کادرهای جدا (IoU≤۰٫۴) از ادغام می‌گریختند و در ساخت سطر چسبانده می‌شدند؛ قاعدهٔ جدید «هم‌متن + هم‌سطر + شکاف کم» قوی‌ترین را نگه می‌دارد و تکرارهای واقعیِ دور از هم دست‌نخورده می‌مانند. شمار حذف در گزارش مرحله اعلام می‌شود (`ghost_duplicates_removed`).
- **F5 — پیش‌پردازش مشروط:** به‌جای ساخت/خواندن همهٔ نسخه‌ها برای همهٔ تصاویر، `diagnose_image` (سایه/زمینهٔ تیره/جوهر رنگی) تصمیم می‌گیرد و دلیل هر صرف‌نظر به فارسی گزارش می‌شود؛ فلگ بازگشت به مسیر قدیمی: `LBR_CONDITIONAL_VARIANTS=0`.
- **F6 — رکورد کامل خوانش خام:** زبان/PSM/ابعاد ورودی/زمان اجرا/شمار قطعات خام و دلیل رد هر قطعه اکنون برای هر واریانت ثبت و در رابط نمایش داده می‌شود — تفکیک شفاف «خوانش خام ← ادغام ← فیلدها ← پاسخ».

### 📊 ارزیابی واقعی قبل/بعد (شرایط یکسان)

- دقت فیلد: **۶۴٫۳٪ (۹/۱۴) ← ۷۱٫۴٪ (۱۰/۱۴)** · میانگین زمان: **۶٫۸s ← ۳٫۷s (~۱٫۸× سریع‌تر)**
- شواهد: `scripts/evidence_v210/` و `docs/evaluation/evaluation-results-v210.json`
- محدودیت صادقانه: تصویر واقعی نمونهٔ کاربر در اختیار نبود؛ سازوکار تکرار تجمیعی با آزمون‌های مصنوعی بسته شد و تأیید نهایی نیازمند همان تصویر است.

### 🧪 پاریتی و آزمون‌ها

- **۱۷۰ pytest + ۷۰ Node همتا — همه پاس** · گیت نام به «رأی دو واریانت مستقل» سخت‌گیرانه‌تر شد
- تکمیل شناسه‌گذاری قطعه‌ها در موبایل (source_ids دیگر خالی نیست) · رفع آزمون شکنندهٔ نسخه

### 📚 مستندات هم‌راستا

- documentation.html (گام‌های ممیزی‌شده + تاریخچهٔ v2.10.0) · PDF ۹ صفحه‌ای (خلاصهٔ ممیزی + WBS و درخت مخزن + ارزیابی) · راهنماهای دسکتاپ/موبایل · README · START-HERE

### ⚠️ مهم برای نصب APK

کلید امضای این نسخه جدید است (محیط ساخت ریست شده) — ابتدا نسخهٔ قبلی را **Uninstall** کنید و سپس APK جدید را نصب کنید. (versionCode 21، versionName 2.10.0)

### نصب
- **بدون پایتون:** `Portable-Web.zip` → `START-WINDOWS.bat`
- **دسکتاپ:** `pip install -r requirements.txt` → `streamlit run app.py`
- **اندروید:** `Android.apk` (versionCode 21) — با کلید امضای جدید؛ Uninstall نسخهٔ قبل لازم است
- **تک‌فایل:** `label-reader-singlefile-v2.10.0.html` — دابل‌کلیک، بدون سرور

### یادآوری محدوده محصول
این ابزار فقط می‌گوید «روی بسته چه نوشته شده است»؛ تشخیص دارو، تجویز، تعیین مقدار مصرف یا توصیه پزشکی انجام نمی‌دهد. «قدرت درج‌شده» هرگز «دوز مصرف» نیست.
"""


def main() -> None:
    # بررسی وجود دارایی‌ها
    for path, name, _ in ASSETS:
        assert path.exists(), f"موجود نیست: {path}"
        print(f"✓ {name} ({path.stat().st_size/1e6:.1f} MB)")

    tag = f"v{VERSION}"
    # ساخت تگ اگر نباشد (v2.10.0 از قبل ساخته و پوش شده است)
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
        "name": f"LabelVoice {tag} — ممیزی مهندسی OCR و اصلاحات ریشه‌ای ادغام",
        "body": BODY, "draft": False, "prerelease": False}).encode())
    rel_id = rel["id"]
    print(f"Release id={rel_id}")

    for path, name, _ in ASSETS:
        data = path.read_bytes()
        boundary = "----labelvoice2100boundary"
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

    # راستی‌آزمایی نهایی
    check = gh("GET", f"releases/tags/{tag}")
    names = [a["name"] for a in check.get("assets", [])]
    print(f"دارایی‌های نهایی ({len(names)}): {', '.join(names)}")
    print("URL:", check.get("html_url"))


if __name__ == "__main__":
    main()

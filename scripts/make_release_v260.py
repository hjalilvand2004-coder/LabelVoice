#!/usr/bin/env python3
"""انتشار Release v2.6.0 — توکن فقط گذرا از ورودی استاندارد؛ هرگز ذخیره نمی‌شود.

v2.6.0 = تغییر فقط دسکتاپ (دیدن گام‌به‌گام OpenCV و خوانش خام OCR).
دارایی‌ها: Full-Project جدید + Portable-Web/Mobile-PWA/تک‌فایل/APK بازساخت‌شده
از منابع بدون تغییرِ موبایل (محتوای همان v2.5.0).
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
VERSION = "2.6.0"
ROOT = Path("/home/z/my-project/labelvoice-clone")
OUT = Path("/home/z/my-project/download")
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# ۱) ساخت بسته‌ها (همان منطق build_v230_zips.py با نسخهٔ جدید)
# ---------------------------------------------------------------------------
def is_ascii_name(name: str) -> bool:
    return all(ord(c) < 128 for c in name)


# ---------- پروژهٔ کامل ----------
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

# ---------- اپ موبایل PWA (منابع بدون تغییر) ----------
MOBILE = ROOT / "mobile-app"
mobile_zip = OUT / f"LabelVoice-v{VERSION}-Mobile-App-PWA.zip"
with zipfile.ZipFile(mobile_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    skip = {
        "label-reader-singlefile.html", "START-WINDOWS.bat",
        "server-windows.ps1", "شروع-در-ویندوز.bat", "شروع-در-لینوکس-مک.sh",
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

# ---------- دارایی‌های بدون تغییر (Portable-Web/تک‌فایل/APK از v2.5.0) ----------
PORTABLE_SRC = OUT / "LabelVoice-v2.5.0-Portable-Web.zip"
SINGLEFILE_SRC = ROOT / "mobile-app" / "label-reader-singlefile.html"
APK_SRC = ROOT / "android" / "build" / "LabelVoice-Android-2.5.0.apk"

ASSETS = [
    (full_zip, f"LabelVoice-v{VERSION}-Full-Project.zip",
     "کل پروژه با بخش جدید «دیدن گام‌به‌گام OpenCV و خوانش خام OCR» (دسکتاپ Streamlit)"),
    (PORTABLE_SRC, f"LabelVoice-v{VERSION}-Portable-Web.zip",
     "بستهٔ قابل حمل — بدون تغییر نسبت به ۲.۵.۰ (این نسخه فقط دسکتاپ را تغییر داده است)"),
    (mobile_zip, f"LabelVoice-v{VERSION}-Mobile-App-PWA.zip",
     "اپ موبایل (PWA) — بدون تغییر نسبت به ۲.۵.۰"),
    (SINGLEFILE_SRC, f"label-reader-singlefile-v{VERSION}.html",
     "تک‌فایل قابل حمل — بدون تغییر نسبت به ۲.۵.۰"),
    (APK_SRC, "LabelVoice-Android-2.5.0.apk",
     "نسخهٔ نصب‌پذیر اندروید (versionCode 17) — بدون تغییر نسبت به ۲.۵.۰؛ این نسخه فقط دسکتاپ را تغییر داده است"),
]

BODY = """## برچسب‌خوان هوشمند دارو و محصولات — نسخه ۲.۶.۰

**توسعه و طراحی: حمید جلیلوند و نوید بدری**

### 🔬 درخواست کاربر: «خروجی مرحله OpenCV را ببینم… اقداماتی که روی تصویر انجام می‌دهد… و بعد ببینم OCR چی خوند» ✅

بخش جدید **«🔬 دیدن کار OpenCV و خوانش خام OCR (گام‌به‌گام)»** در صفحهٔ «خواندن دارو» (دسکتاپ/Streamlit):

**۱) مسیر تصویر در پیش‌پردازش — خروجی هر عملیات:**
- ورودی پس از اعتبارسنجی ← برش دستی (در صورت انتخاب) ← صاف‌کردن چرخش کم‌زاویه (در صورت لزوم) ← بزرگ‌نمایی کنترل‌شده ← خاکستری + حذف نویز + CLAHE ← آستانه‌گذاری تطبیقی (دودویی) ← متن روشن روی زمینهٔ تیره ← جداسازی جوهر رنگی.
- هر گام: **تصویر حاصل از همان عملیات** + توضیح عین عملیات (نام تابع `cv2` و پارامترها) + معیارهای تیزی/کنتراست/روشنایی همان گام برای مقایسهٔ قبل/بعد.

**۲) خوانش خام هر نسخه — «OCR دقیقاً چه خواند؟» (قبل از ادغام و رأی‌گیری):**
- به‌ازای هر نسخهٔ پردازشی (original، gray_clahe، binarized، white_on_dark، ink_isolated): تصویر همان نسخه با **کادر سبز روی هر ناحیهٔ خوانده‌شده**، متن پیوستهٔ خوانش، جدول متن خام + درصد اطمینان + موتور خواننده (`tesseract:fas` / `tesseract:eng` / `easyocr`) + مختصات و اندازهٔ هر کادر.
- شمار قطعه‌های ردشدهٔ گیت کیفیت (زبالهٔ ترکیب‌خطی، نماد محض، کادر منحط و…) نیز اعلام می‌شود.

#### تغییرات فنی
- `label_reader/preprocess.py`: تابع جدید `build_variants_traced` (هر واریانت با عنوان/توضیح فارسیِ عین عملیات cv2)
- `label_reader/pipeline.py`: مسیر کامل `opencv_trace` (ورودی/برش/deskew/واریانت‌ها با معیارهای هر گام) + `variant_readings` (متن/اطمینان/مختصات هر قطعه + شمار ردشده‌ها) در اعلام مراحل
- `label_reader/stages.py`: سطر «مسیر گام‌به‌گام OpenCV» در اعلام مرحله ۱ و سطر «خوانش خام هر نسخه» در اعلام مرحله ۲ (در گزارش JSON مرحله‌ای هم درج می‌شود)
- `app.py`: بخش جدید با گرید تصویر گام‌ها + expander هر نسخه با کادرکشی و جدول خوانش خام
- مودال راهنمای جدید «چرا چند نسخه ساخته می‌شود؟» در `help_content.py`
- آزمون‌ها: **۱۳۸ pytest پاس** (۷ آزمون جدید `test_stage_trace.py`) + AppTest کامل (بارگذاری ← خواندن ← رندر بخش جدید) + اجرای واقعی با Tesseract روی نمونه‌های فارسی/انگلیسی

#### محدودهٔ این نسخه
- این ویژگی مربوط به **نسخهٔ دسکتاپ (Streamlit)** است — OpenCV و موتورهای پایتونی در مرورگر اجرا نمی‌شوند.
- وب / PWA / APK نسبت به v2.5.0 **بدون تغییر**‌اند (همان دارایی‌ها در این ریلیز هم قرار گرفت تا دانلود یکجا ممکن باشد).
"""

API = f"https://api.github.com/repos/{REPO}"


def req(method: str, url: str, data=None, headers=None, raw=False):
    h = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}
    if headers:
        h.update(headers)
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(r, timeout=300) as resp:
        body = resp.read()
        return body if raw else (json.loads(body) if body else {})


def upload(url: str, path: Path, name: str) -> None:
    mime = "application/octet-stream"
    for attempt in range(1, 4):
        try:
            data = path.read_bytes()
            req("POST", url + f"?name={name}", data=data,
                headers={"Content-Type": mime, "Content-Length": str(len(data))})
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
        "name": f"LabelVoice v{VERSION} — دیدن گام‌به‌گام OpenCV و خوانش خام OCR",
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

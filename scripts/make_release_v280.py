#!/usr/bin/env python3
"""انتشار Release v2.8.0 — توکن فقط گذرا از ورودی استاندارد؛ هرگز ذخیره نمی‌شود.

v2.8.0 = دکمهٔ «👁 نمایش تصویر پس از این عملیات» برای هر گام OpenCV
(خواستهٔ صریح کاربر) + لانچر نسخه‌محور START-WINDOWS با هشدار خودکار
کپی قدیمی و بازکردن صفحهٔ دانلود (رفع ریشهٔ «هنوز نمی‌بینم»).

هر ۵ دارایی: Full-Project / Mobile-App-PWA / Portable-Web / تک‌فایل /
APK (versionCode 19). پیش‌نیاز: build_portable_zip.py + build_apk.sh اجرا شده باشند.
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
VERSION = "2.8.0"
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
apk = ROOT / "android" / "build" / "LabelVoice-Android-2.8.0.apk"

ASSETS = [
    (full_zip, f"LabelVoice-v{VERSION}-Full-Project.zip",
     "کل پروژه — دسکتاپ (Streamlit) + وب/موبایل + اندروید + اسکریپت‌ها"),
    (portable_zip, f"LabelVoice-v{VERSION}-Portable-Web.zip",
     "بستهٔ قابل حمل بدون پایتون — با دکمهٔ نمایش تصویر هر گام + لانچر نسخه‌محور"),
    (mobile_zip, f"LabelVoice-v{VERSION}-Mobile-App-PWA.zip",
     "اپ موبایل PWA — دکمهٔ «👁 نمایش تصویر پس از این عملیات» برای هر گام"),
    (singlefile, f"label-reader-singlefile-v{VERSION}.html",
     "تک‌فایل آفلاین قابل حمل — موتور OCR و دادهٔ زبان تعبیه‌شده"),
    (apk, f"LabelVoice-v{VERSION}-Android.apk",
     "نسخهٔ نصب‌پذیر اندروید (versionCode 19، versionName 2.8.0)"),
]

BODY = """## برچسب‌خوان هوشمند دارو و محصولات — نسخه ۲.۸.۰

**توسعه و طراحی: حمید جلیلوند و نوید بدری**

### 👁 بازخورد کاربر: «دقیقاً در قالب یک دکمه به معنای نمایش خود تصویر بعد از انجام عملیات» ✅

هر گام در بخش «🔬 دیدن کار OpenCV و خوانش خام OCR» اکنون **دکمهٔ اختصاصی خودش** را دارد:

- **وب / موبایل / APK:** دکمهٔ **«👁 نمایش تصویر پس از این عملیات»** — با کلیک، تصویرِ همان لحظهٔ پس از انجام عملیات (روی همان تصویر اولیهٔ شما) باز می‌شود؛ کلیک دوباره آن را می‌بندد و دکمه به «🙈 پنهان‌کردن تصویر این گام» تبدیل می‌شود.
- **دسکتاپ (Streamlit):** دکمهٔ هر گام + کلید **«نمایش همهٔ تصاویر یک‌جا»**.
- خوانش خام OCR هر نسخهٔ پردازشی (متن پیوسته + تعداد قطعه + اطمینان) هم مثل قبل زیر همان بخش است.

### 🧭 چرا قابلیت را نمی‌دیدید؟ — لانچر نسخه‌محور START-WINDOWS

اگر قابلیت‌های جدید را نمی‌بینید، پوشهٔ استخراج‌شدهٔ شما از یک **ZIP قدیمی** است (START-WINDOWS همان پوشهٔ کناری خودش را اجرا می‌کند). از این نسخه:

- `START-WINDOWS.bat` بنر **نسخهٔ پوشه** (از `VERSION.txt`) + نسخهٔ آخر گیت‌هاب را نشان می‌دهد.
- `server-windows.ps1` نسخه را با آخرین Release مقایسه می‌کند؛ اگر کپی قدیمی باشد هشدار **«THIS COPY IS OUTDATED»** می‌دهد و **صفحهٔ دانلود خودکار باز می‌شود** (آفلاین → بی‌صدا رد می‌شود).
- `VERSION.txt` در ریشهٔ هر سه ZIP هست؛ چیپ «نسخهٔ وب ۲.۸.۰» در سایدبار اپ نیز دیده می‌شود.
- راهنمای به‌روزرسانی APK: نسخه‌های ۲.۵.۰ به بعد درجا نصب می‌شوند (versionCode 19)؛ نسخه‌های قدیمی‌تر را اول Uninstall کنید.

#### تغییرات فنی
- `mobile-app/js/app.js`: دکمهٔ باز/بستهٔ تصویر هر گام (`cv-step-btn`، aria-expanded) + `style.css`
- `app.py`: دکمهٔ per-step با session_state + toggle «نمایش همهٔ تصاویر یک‌جا»
- `START-WINDOWS.bat` / `server-windows.ps1` (هر دو ریشهٔ mobile-app و portable): بنر نسخه + بررسی آخرین Release با timeout ۶ ثانیه و بازکردن صفحهٔ دانلود
- `scripts/build_portable_zip.py`: `VERSION.txt` در ریشهٔ ZIP
- رفع باگ ارثی: ثبت `app_version` واقعی در JSON خروجی (جاافتاده از بازنویسی v2.0) + سازگاری آزمون‌ها با معماری فعلی
- نسخه‌ها: APK versionCode 19 (2.8.0) · کش سرویس‌ورکر → `lbr-mobile-v20`
- آزمون‌ها: ۱۴۲ pytest + ۶۹ Node (۶۴ عمومی + ۵ trace) + AppTest بدون استثنا + ران واقعی مرورگر با شاهد تصویری (باز/بسته‌شدن دکمهٔ هر گام)

#### یادآوری محدوده محصول
این ابزار فقط می‌گوید «روی بسته چه نوشته شده است»؛ تشخیص دارو، تجویز، تعیین مقدار مصرف یا توصیه پزشکی انجام نمی‌دهد.
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
        "name": f"LabelVoice v{VERSION} — دکمهٔ نمایش تصویر هر گام OpenCV + لانچر نسخه‌محور",
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

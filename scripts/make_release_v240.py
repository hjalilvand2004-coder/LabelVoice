#!/usr/bin/env python3
"""انتشار Release v2.4.0 — توکن فقط گذرا از ورودی استاندارد؛ هرگز ذخیره نمی‌شود."""
import json
import os
import sys
import urllib.request
from pathlib import Path

REPO = "hjalilvand2004-coder/LabelVoice"
TOKEN = os.environ.get("GH_TOKEN") or sys.stdin.readline().strip()
ASSETS = [
    ("/home/z/my-project/labelvoice-clone/mobile-app/label-reader-singlefile.html",
     "label-reader-singlefile-v2.4.0.html",
     "تک‌فایل قابل حمل با انتخاب‌گر موتور خوانش + هدر تصویری تعبیه‌شده — اجرا بدون پایتون با دوبار کلیک"),
    ("/home/z/my-project/download/LabelVoice-v2.4.0-Portable-Web.zip",
     "LabelVoice-v2.4.0-Portable-Web.zip",
     "بستهٔ قابل حمل: START-HERE.html + تک‌فایل + webapp/ + لانچرهای ویندوز/لینوکس"),
    ("/home/z/my-project/download/LabelVoice-v2.4.0-Mobile-App-PWA.zip",
     "LabelVoice-v2.4.0-Mobile-App-PWA.zip",
     "اپ موبایل (PWA): index.html + انتخاب‌گر موتور + Service Worker + Manifest + آیکون‌ها"),
    ("/home/z/my-project/download/LabelVoice-v2.4.0-Full-Project.zip",
     "LabelVoice-v2.4.0-Full-Project.zip",
     "کل پروژه: دسکتاپ Streamlit + وب + اپ موبایل + آزمون‌ها + مستندات"),
    ("/home/z/my-project/download/LabelVoice-Android-2.4.0.apk",
     "LabelVoice-v2.4.0-Android.apk",
     "نسخهٔ نصب‌پذیر اندروید (versionCode 16) — WebView محلی با انتخاب‌گر موتور خوانش، امضاشده"),
]
BODY = """## برچسب‌خوان هوشمند دارو و محصولات — نسخه ۲.۴.۰

**توسعه و طراحی: حمید جلیلوند و نوید بدری**

### 🧠 انتخاب‌گر موتور و مدل خوانش — اکنون در وب و موبایل هم (نه فقط دسکتاپ)
درخواست: «جایی در وب سایت و نرم افزار نیست که من بتوانم مدل انتخابی برای OCR را انتخاب کنم — هم در موبایل اپلیکیشن و هم در وب سایت».

**۱) وب / PWA / تک‌فایل — انتخاب‌گر همیشه‌نمایان «🧠 موتور و مدل خوانش (OCR)»** بالای دکمهٔ خواندن؛ پنج گزینهٔ واقعی مرورگری:

| # | مدل خوانش | توضیح |
|---|---|---|
| ۱ | **Tesseract.js 6 — سریع (integer) · fas+eng** | پیش‌فرض |
| ۲ | **Tesseract.js LSTM — دقیق‌تر (tessdata_best) · fas+eng** | کندتر اما دقیق‌تر |
| ۳ | **Tesseract.js — فقط فارسی (fas)** | برای برچسب‌های تمام‌فارسی |
| ۴ | **Tesseract.js — فقط انگلیسی (eng)** | برای برچسب‌های لاتین |
| ۵ | **Tesseract.js LSTM دقیق‌تر — فقط فارسی** | ترکیب دقیق + فارسی |

- انتخاب در `localStorage` ذخیره و در اجرای بعدی بازگردانی می‌شود؛ نام موتور در اعلام مراحل (مرحله ۲) و خروجی JSON درج می‌شود.
- همهٔ گزینه‌ها از **همان گیت کیفیت و رأی اجماعی** عبور می‌کنند — میان‌بر وجود ندارد.
- شفافیت: **EasyOCR، Surya و Qwen3-VL-2B-Instruct** فقط در نسخهٔ دسکتاپ اجرا می‌شوند (مرورگر فقط WASM) و در خود انتخاب‌گر اعلام می‌شوند.

**۲) دسکتاپ (Streamlit):** منوی ۵گزینه‌ای سایدبار (از v2.3.0: Tesseract 5 · EasyOCR · Surya · Qwen3-VL-2B-Instruct · خودکار) + **نشان جدید «موتور و مدل خوانش فعال»** درست زیر هیرو تا انتخاب کاربر همیشه بالای صفحه دیده شود.

**۳) هدر تصویری اختصاصی (درخواست کاربر):** تصویر هویت بصری پروژه (بطری دارو + آیکون‌های هوش مصنوعی + امواج آبی/قرمز) به‌عنوان پس‌زمینهٔ هدر در **هر سه رابط** (دسکتاپ، موبایل/PWA، صفحهٔ شروع بستهٔ قابل حمل) با پردهٔ روشن برای خوانایی متن؛ در حالت تاریک همان گرادیان سرمه‌ای قبلی.

**۴) رفع «START-WINDOWS نسخهٔ قدیم را اجرا می‌کند»:** ریشهٔ ماجرا محتوای کهنهٔ صفحهٔ شروع بود (START-HERE و پانویس موبایل هنوز نسخهٔ ۲.۲.۰/۲.۰.۰ را نشان می‌دادند). همهٔ سطوح نسخه یکدست به ۲.۴.۰ به‌روز شد و جدول مدل‌های صفحهٔ شروع با منوی ۵موتورهٔ دسکتاپ به‌روز شد.
> 💡 اگر باز نسخهٔ قدیمی دیدید: بستهٔ جدید را در یک پوشهٔ تازه استخراج کنید؛ اسکریپت خودترمیم START-HERE کش سرویس‌ورکرِ قدیمی را یک‌بار پاک می‌کند.

#### تغییرات فنی
- `index.html + js/app.js`: نقشهٔ ۵گزینه‌ای موتور → `settings.ocr_languages` + `langQuality` (integer/best)؛ بازگردانی و ذخیرهٔ انتخاب
- `scripts/build_singlefile.py`: تعبیهٔ تصویر هدر به‌صورت data URI در تک‌فایل (کاملاً آفلاین می‌ماند)
- `label_reader/ui_theme.py`: هیروی تصویری + بازگشت گرادیان در `DARK_THEME_CSS` + استایل نشان موتور فعال
- `portable/START-HERE.html`: هدر تصویری + نسخهٔ ۲.۴.۰ + جدول موتورهای به‌روز
- مستندات: `documentation.html` (تاریخچهٔ v2.3.0 + v2.4.0 + جدول مدل‌ها)، `help.js`، README، راهنمای درون‌اپی
- کش سرویس‌ورکر → `lbr-mobile-v17` (+ پیش‌بارگیری تصویر هدر)
- **اندروید:** versionCode **16** / versionName **2.4.0**
- آزمون: **۱۳۲/۱۳۲ pytest** + **۶۴/۶۴ Node** + AppTest بدون استثنا + **E2E واقعی مرورگر با هر دو موتور (سریع و LSTM)** — همگی پاس

### ⚠️ ارتقای APK اندروید
کلید امضای این نسخه با v2.3.0 **متفاوت** است (بازسازی محیط ساخت). اگر نسخهٔ قبلی را نصب دارید، ابتدا آن را **حذف (Uninstall)** و سپس APK جدید را نصب کنید.

### 🧠 شفافیت مدل‌ها (پابرجا)
| مرحله | مدل / موتور |
|---|---|
| پیش‌پردازش تصویر | **OpenCV** (کلاسیک، بدون مدل یادگیری) |
| خواندن متن — دسکتاپ | **Tesseract 5** · **EasyOCR** · **Surya** · **Qwen3-VL-2B-Instruct** — به انتخاب کاربر |
| خواندن متن — وب/موبایل/تک‌فایل/اندروید | **Tesseract.js 6.0.1 (WASM)** — مدل/زبان به انتخاب کاربر (v2.4.0) |
| پردازش متن و فیلدها | قواعد فارسی + گیت کیفیت + رأی اجماعی |
| تولید پاسخ فارسی | قالب‌ساز قاعده‌محور + نگهبان ایمنی |
| خوانش صوتی | دسکتاپ: **edge-tts** · وب: **Web Speech API** |

### ✔️ کیفیت و خط قرمز
- هر فیلد به شواهد موتورِ منتخبِ کاربر ردیابی‌پذیر است؛ «قدرت درج‌شده» هرگز «دوز مصرف» نیست؛ بدون توصیهٔ پزشکی
- 📚 مستندات کامل: https://hjalilvand2004-coder.github.io/LabelVoice/documentation.html
"""


API = f"https://api.github.com/repos/{REPO}"
HDR = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "Content-Type": "application/json",
}

CT_BY_EXT = {
    ".zip": "application/zip",
    ".apk": "application/vnd.android.package-archive",
    ".html": "text/html; charset=utf-8",
}


def req(url: str, data=None, method="GET", raw=None):
    body = raw if raw is not None else (json.dumps(data).encode() if data else None)
    r = urllib.request.Request(url, data=body, headers=HDR, method=method)
    with urllib.request.urlopen(r) as resp:
        payload = resp.read()
    return json.loads(payload) if payload else {}


def main() -> None:
    try:
        rel = req(f"{API}/releases", data={"tag_name": "v2.4.0", "target_commitish": "main",
                                           "name": "LabelVoice v2.4.0 — انتخاب‌گر موتور خوانش در وب و موبایل + هدر تصویری",
                                           "body": BODY, "draft": False, "prerelease": False}, method="POST")
        print(f"release created: #{rel['id']}")
    except Exception as e:
        if "already_exists" in str(e):
            rel = req(f"{API}/releases/tags/v2.4.0")
            rel = req(f"{API}/releases/{rel['id']}", data={"body": BODY, "name": "LabelVoice v2.4.0 — انتخاب‌گر موتور خوانش در وب و موبایل + هدر تصویری"}, method="PATCH")
            print(f"release exists, updated: #{rel['id']}")
        else:
            raise
    rid = rel["id"]

    for path, name, label in ASSETS:
        p = Path(path)
        assert p.exists(), f"missing asset: {p}"
        existing = {a["name"] for a in rel.get("assets", [])}
        if name in existing:
            print(f"asset exists, skipping: {name}")
            continue
        ct = CT_BY_EXT.get(p.suffix.lower(), "application/octet-stream")
        up = urllib.request.Request(
            f"https://uploads.github.com/repos/{REPO}/releases/{rid}/assets?name={name}",
            data=p.read_bytes(),
            headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": ct,
                     "Content-Length": str(p.stat().st_size)},
            method="POST")
        with urllib.request.urlopen(up) as resp:
            print(f"uploaded: {resp.status} {name}")
    print("DONE")


if __name__ == "__main__":
    main()

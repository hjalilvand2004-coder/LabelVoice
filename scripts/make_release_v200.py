#!/usr/bin/env python3
"""انتشار Release v2.0.0 — توکن فقط در حافظهٔ پردازش؛ هرگز در فایل/گیت ذخیره نمی‌شود."""
import json
import os
import sys
import urllib.request
from pathlib import Path

REPO = "hjalilvand2004-coder/LabelVoice"
TOKEN = os.environ.get("GH_TOKEN") or sys.stdin.readline().strip()
ASSETS = [
    ("/home/z/my-project/labelvoice-clone/mobile-app/label-reader-singlefile.html",
     "label-reader-singlefile-v2.0.0.html",
     "نشانگر: اجرا بدون پایتون با دوبار کلیک — OCR آفلاین تعبیه‌شده"),
    ("/home/z/my-project/download/LabelVoice-v2.0.0-Portable-Web.zip",
     "LabelVoice-v2.0.0-Portable-Web.zip",
     "بستهٔ قابل حمل ویندوز/موبایل: START-HERE.html + START-WINDOWS.bat (لانچر خودترمیم) + webapp/ + تک‌فایل"),
    ("/home/z/my-project/download/LabelVoice-v2.0.0-Full-Project.zip",
     "LabelVoice-v2.0.0-Full-Project.zip",
     "کل پروژه: دسکتاپ Streamlit + وب + آزمون‌ها (۱۱۷ pytest + ۶۴ Node) + مستندات"),
]
BODY = """## برچسب‌خوان هوشمند دارو و محصولات — نسخه ۲.۰.۰

**توسعه و طراحی: حمید جلیلوند و نوید بدری**

### 🚀 لانچر خودترمیم — پایان «بهم‌ریختگی» در اجرای START-WINDOWS.bat
گزارش کاربر: «با start.bat سایت به‌هم‌ریخته است ولی با فایل وب START-HERE درست است».
ریشهٔ مشکل: **سرویس‌ورکر نسخهٔ قدیمی** که روی `127.0.0.1:8765` ثبت شده بود، رابط کهنه را از کش سرو می‌کرد (تک‌فایل بدون سرویس‌ورکر سالم می‌ماند).

- ریشهٔ سرور محلی اکنون **START-HERE.html** است؛ این صفحه یک‌بار در هر مرورگر همهٔ سرویس‌ورکرها و کش‌های قدیمی همان آدرس را پاک می‌کند و همیشه نسخهٔ تازه از دیسک خوانده می‌شود.
- صفحهٔ ۴۰۴ سرور محلی هم به صفحهٔ شروع هدایت می‌شود.
- **راهنمای اجرا:** ZIP را کامل استخراج کنید ← `START-WINDOWS.bat` را دوبار کلیک کنید ← صفحهٔ شروع باز می‌شود ← «باز کردن نسخهٔ کامل» (دوربین زنده) یا «باز کردن نسخهٔ تک‌فایلی».

### 🧠 شفافیت کامل مدل‌ها و موتورها (درخواست کاربر)
اکنون کاربر می‌داند **برای هر بخش از چه مدل/موتوری استفاده می‌شود** — هم در مستندات و هم **درون سامانه در حین مراحل**:

| مرحله | مدل / موتور |
|---|---|
| پیش‌پردازش تصویر | OpenCV (کلاسیک، بدون مدل یادگیری) |
| خواندن متن — موتور اول | **Tesseract 5** (دادهٔ زبان fas+eng) |
| خواندن متن — موتور دوم مکمل | **EasyOCR** — CRNN (fa+en)، اختیاری |
| دستیار خوانش دوم (اختیاری) | **Qwen/Qwen3-VL-2B-Instruct** — کاملاً محلی، پیش‌فرض خاموش |
| پردازش متن و فیلدها | الگوها و قواعد فارسی + گیت کیفیت + رأی اجماعی (بدون مدل زبانی) |
| تولید پاسخ فارسی | قالب‌ساز قاعده‌محور + نگهبان ایمنی (بدون مدل ابری) |
| خوانش صوتی | **edge-tts** — صدای fa-IR-FaridNeural / DilaraNeural با رضایت صریح؛ جایگزین gTTS |
| وب / PWA / تک‌فایل | **Tesseract.js 6.0.1 (WASM)** + Web Speech API |

- رجیستری مرکزی با **تشخیص نسخهٔ زندهٔ** هر موتور از دستگاه کاربر: `label_reader/models_info.py`
- نمایش درون‌اپی: جدول «مدل‌ها و موتورها» در سایدبار دسکتاپ + مودال راهنما، expander «🧠 کدام مدل چه کاری انجام داد؟» در نتایج، معیار «موتور و مدل خوانش» در خط‌زمان مراحل رنگی، جدول رسمی در وب/PWA.
- دستیار Qwen3-VL: فقط سطرهای تازه (بدون تکرار) با شناسهٔ شاهد `vlm-*` اضافه می‌کند؛ هرگز پردازش اصلی را نمی‌شکند. فعال‌سازی: `pip install "transformers>=4.57" accelerate` و روشن‌کردن toggle سایدبار (دانلود اولیهٔ ~۴–۵ گیگابایت، پس از آن آفلاین).

### ✔️ کیفیت
- **۱۱۷/۱۱۷ آزمون pytest** (شامل ۱۱ آزمون جدید رجیستری مدل‌ها و دستیار VLM) + **۶۴/۶۴ آزمون Node** + AppTest استریم‌لیت
- کش سرویس‌ورکر → `lbr-mobile-v13`؛ تمام نام‌فایل‌های ZIP کاملاً ASCII

### 📦 پیوست‌ها
- `label-reader-singlefile-v2.0.0.html` — اجرا بدون پایتون با دوبار کلیک (کاملاً آفلاین)
- `LabelVoice-v2.0.0-Portable-Web.zip` — بستهٔ قابل حمل با لانچر خودترمیم
- `LabelVoice-v2.0.0-Full-Project.zip` — کل پروژه + آزمون‌ها + مستندات

> ⚠️ محدوده محصول: این ابزار فقط می‌گوید «روی بسته چه نوشته شده است»؛ توصیه پزشکی، دوز مصرف یا تشخیص ارائه نمی‌دهد. «قدرت درج‌شده» هرگز به‌جای «دوز مصرف» نمی‌نشیند.
"""

API = "https://api.github.com"
HDR = {"Authorization": f"Bearer {TOKEN}",
       "Accept": "application/vnd.github+json",
       "Content-Type": "application/json",
       "User-Agent": "labelvoice-release"}


def req(url, data=None, headers=None, method=None, raw=False):
    r = urllib.request.Request(url, data=data, headers=headers or HDR, method=method)
    with urllib.request.urlopen(r, timeout=300) as resp:
        body = resp.read()
    return body if raw else json.loads(body or b"{}")


def main():
    # Release تکراری حذف شود
    rels = req(f"{API}/repos/{REPO}/releases?per_page=20")
    for r in rels:
        if r.get("tag_name") == "v2.0.0":
            print(f"حذف Release تکراری id={r['id']}")
            req(f"{API}/repos/{REPO}/releases/{r['id']}", method="DELETE")

    rel = req(f"{API}/repos/{REPO}/releases", data=json.dumps({
        "tag_name": "v2.0.0",
        "target_commitish": "main",
        "name": "LabelVoice v2.0.0 — لانچر خودترمیم + شفافیت کامل مدل‌ها",
        "body": BODY,
        "draft": False, "prerelease": False,
    }).encode())
    rid, up = rel["id"], rel["upload_url"].split("{")[0]
    print(f"Release v2.0.0 id={rid}")

    for path, name, _ in ASSETS:
        p = Path(path)
        assert p.exists(), f"پیوست یافت نشد: {path}"
        data = p.read_bytes()
        req(f"{up}?name={name}", data=data,
            headers={**HDR, "Content-Type": "application/octet-stream"})
        print(f"  آپلود شد: {name} ({data.stat().st_size/1048576 if False else len(data)/1048576:.1f} MB)")

    rel2 = req(f"{API}/repos/{REPO}/releases/{rid}")
    print("دارایی‌ها:", [a["name"] for a in rel2["assets"]])


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""انتشار Release v2.1.0 — توکن فقط گذرا از ورودی استاندارد؛ هرگز ذخیره نمی‌شود."""
import json
import os
import sys
import urllib.request
from pathlib import Path

REPO = "hjalilvand2004-coder/LabelVoice"
TOKEN = os.environ.get("GH_TOKEN") or sys.stdin.readline().strip()
ASSETS = [
    ("/home/z/my-project/labelvoice-clone/mobile-app/label-reader-singlefile.html",
     "label-reader-singlefile-v2.1.0.html",
     "تک‌فایل قابل حمل با پالت داروخانه‌ای — اجرا بدون پایتون با دوبار کلیک"),
    ("/home/z/my-project/download/LabelVoice-v2.1.0-Portable-Web.zip",
     "LabelVoice-v2.1.0-Portable-Web.zip",
     "بستهٔ قابل حمل: START-HERE.html + START-WINDOWS.bat + webapp/ + تک‌فایل"),
    ("/home/z/my-project/download/LabelVoice-v2.1.0-Full-Project.zip",
     "LabelVoice-v2.1.0-Full-Project.zip",
     "کل پروژه: دسکتاپ Streamlit + وب + آزمون‌ها + مستندات"),
]
BODY = """## برچسب‌خوان هوشمند دارو و محصولات — نسخه ۲.۱.۰

**توسعه و طراحی: حمید جلیلوند و نوید بدری**

### 🎨 پالت داروخانه‌ای — درخواست کاربر
درخواست: «در گرافیک وب‌سایت و موبایل از رنگ‌بندی متناسب با فضای داروخانه و دارو استفاده کن».
بر اساس روان‌شناسی رنگ برند دارویی، **هر دو رابط وب دسکتاپ و موبایل/PWA** به یک پالت یکپارچهٔ داروخانه‌ای منتقل شد:

| رنگ | کد | معنا | کاربرد در رابط |
|---|---|---|---|
| 🔵 آبی اعتماد | `#1E88E5` | اعتماد و آرامش | رنگ اصلی برند: دکمه‌ها، سایدبار، هدر، پیوندها |
| 🟢 سبز سلامت | `#43A047` | سلامت و تعهد | موفقیت استخراج فیلد، تأکید ثانویه، دکمهٔ ثانویه |
| ⚪ سفید بهداشت | `#FFFFFF` | پاکیزگی و بهداشت | پس‌زمینهٔ کارت‌ها و پاسخ اصلی |
| 🔴 قرمز هشدار | `#E53935` | هشدار و توجه | تناقض/خطا، مرحلهٔ خوانش صوتی |

#### تغییرات فنی
- **دسکتاپ (Streamlit):** بازنویسی کامل `ui_theme.py` — تم روشن (سایدبار و هیرو با گرادیان آبی اعتماد، کارت‌های سفید بهداشت) و تم تاریک (سرمه‌ای عمیق آبی‌فام `#081426` + سطوح `#0E2440`)؛ چیپ‌های وضعیت فیلد با رنگ‌های معنایی پالت (استخراج‌شده = سبز، تناقض = قرمز هشدار، اصلاح دستی = آبی)
- **رنگ ۵ مرحلهٔ پردازش** هماهنگ با پالت: پیش‌پردازش آبی `#1E88E5` · خوانش فیروزه‌ای `#00ACC1` · فیلدها نارنجی `#FB8C00` · پاسخ سبز سلامت `#43A047` · خوانش صوتی قرمز `#E53935`
- **موبایل/PWA:** توکن‌های `style.css` (روشن + تاریک سیستم + تاریک دستی)، گرادیان هدر/سایدبار → آبی اعتماد، رنگ‌های متن سایدبار هماهنگ
- **آیکون‌های PWA بازتولید شد:** صلیب داروخانهٔ سفید + خط اسکن سبز روی گرادیان آبی (۱۹۲/۵۱۲/maskable)
- `manifest.webmanifest` و `theme-color` و مستندات `documentation.html` و لانچر `START-HERE.html` و صفحهٔ راهنما — همه هماهنگ با پالت
- `.streamlit/config.toml`: رنگ بومی ویجت‌های Streamlit هم به آبی اعتماد تغییر کرد
- کش سرویس‌ورکر → `lbr-mobile-v14` تا همهٔ کاربران نسخهٔ جدید را ببینند؛ نسخهٔ میزبانی‌شدهٔ gh-pages نیز به‌روز شد

### 🧠 شفافیت مدل‌ها (از v2.0.0 — پابرجا)
| مرحله | مدل / موتور |
|---|---|
| پیش‌پردازش تصویر | OpenCV (کلاسیک، بدون مدل یادگیری) |
| خواندن متن — موتور اول | **Tesseract 5** (دادهٔ زبان fas+eng) |
| خواندن متن — موتور دوم مکمل | **EasyOCR** — CRNN (fa+en)، اختیاری |
| دستیار خوانش دوم (اختیاری) | **Qwen/Qwen3-VL-2B-Instruct** — کاملاً محلی، پیش‌فرض خاموش |
| پردازش متن و فیلدها | الگوها و قواعد فارسی + گیت کیفیت + رأی اجماعی |
| تولید پاسخ فارسی | قالب‌ساز قاعده‌محور + نگهبان ایمنی |
| خوانش صوتی | **edge-tts** — fa-IR-FaridNeural / DilaNeural با رضایت صریح |
| وب / PWA / تک‌فایل | **Tesseract.js 6.0.1 (WASM)** + Web Speech API |

### ✔️ کیفیت
- **۱۱۷/۱۱۷ آزمون pytest** + **۶۴/۶۴ آزمون Node** + درون‌بودن (import) موفق اپ استریم‌لیت
- همهٔ نام‌فایل‌های ZIP کاملاً ASCII (مقاوم به مخدوش‌شدگی انکودینگ)

### 📦 پیوست‌ها
- `label-reader-singlefile-v2.1.0.html` — اجرا بدون پایتون با دوبار کلیک (کاملاً آفلاین)
- `LabelVoice-v2.1.0-Portable-Web.zip` — بستهٔ قابل حمل ویندوز/موبایل با لانچر خودترمیم
- `LabelVoice-v2.1.0-Full-Project.zip` — کل پروژه + آزمون‌ها + مستندات

> ⚠️ محدوده محصول: این ابزار فقط می‌گوید «روی بسته چه نوشته شده است»؛ توصیه پزشکی، دوز مصرف یا تشخیص ارائه نمی‌دهد. «قدرت درج‌شده» هرگز به‌جای «دوز مصرف» نمی‌نشیند.
"""

API = "https://api.github.com"
HDR = {"Authorization": f"Bearer {TOKEN}",
       "Accept": "application/vnd.github+json",
       "Content-Type": "application/json",
       "User-Agent": "labelvoice-release"}


def req(url, data=None, headers=None, method=None):
    r = urllib.request.Request(url, data=data, headers=headers or HDR, method=method)
    with urllib.request.urlopen(r, timeout=600) as resp:
        return json.loads(resp.read() or b"{}")


def main():
    rels = req(f"{API}/repos/{REPO}/releases?per_page=20")
    for r in rels:
        if r.get("tag_name") == "v2.1.0":
            print(f"حذف Release تکراری id={r['id']}")
            req(f"{API}/repos/{REPO}/releases/{r['id']}", method="DELETE")

    rel = req(f"{API}/repos/{REPO}/releases", data=json.dumps({
        "tag_name": "v2.1.0",
        "target_commitish": "main",
        "name": "LabelVoice v2.1.0 — پالت داروخانه‌ای (آبی اعتماد + سبز سلامت) در هر دو رابط",
        "body": BODY,
        "draft": False, "prerelease": False,
    }).encode())
    rid, up = rel["id"], rel["upload_url"].split("{")[0]
    print(f"Release v2.1.0 id={rid}")

    for path, name, _ in ASSETS:
        p = Path(path)
        assert p.exists(), f"پیوست یافت نشد: {path}"
        data = p.read_bytes()
        req(f"{up}?name={name}", data=data,
            headers={**HDR, "Content-Type": "application/octet-stream"})
        print(f"  آپلود شد: {name} ({len(data)/1048576:.1f} MB)")

    rel2 = req(f"{API}/repos/{REPO}/releases/{rid}")
    print("دارایی‌ها:", [a["name"] for a in rel2["assets"]])


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""انتشار Release v2.2.0 — توکن فقط گذرا از ورودی استاندارد؛ هرگز ذخیره نمی‌شود."""
import json
import os
import sys
import urllib.request
from pathlib import Path

REPO = "hjalilvand2004-coder/LabelVoice"
TOKEN = os.environ.get("GH_TOKEN") or sys.stdin.readline().strip()
ASSETS = [
    ("/home/z/my-project/labelvoice-clone/mobile-app/label-reader-singlefile.html",
     "label-reader-singlefile-v2.2.0.html",
     "تک‌فایل قابل حمل با موتور سوم Surya + پالت دارویی پررنگ — اجرا بدون پایتون با دوبار کلیک"),
    ("/home/z/my-project/download/LabelVoice-v2.2.0-Portable-Web.zip",
     "LabelVoice-v2.2.0-Portable-Web.zip",
     "بستهٔ قابل حمل: START-HERE.html + تک‌فایل + webapp/ + لانچرهای ویندوز/لینوکس"),
    ("/home/z/my-project/download/LabelVoice-v2.2.0-Mobile-App-PWA.zip",
     "LabelVoice-v2.2.0-Mobile-App-PWA.zip",
     "اپ موبایل (PWA): index.html + Service Worker + Manifest + آیکون‌ها — نصب روی گوشی یا میزبانی محلی"),
    ("/home/z/my-project/download/LabelVoice-v2.2.0-Full-Project.zip",
     "LabelVoice-v2.2.0-Full-Project.zip",
     "کل پروژه: دسکتاپ Streamlit + وب + اپ موبایل + آزمون‌ها + مستندات"),
]
BODY = """## برچسب‌خوان هوشمند دارو و محصولات — نسخه ۲.۲.۰

**توسعه و طراحی: حمید جلیلوند و نوید بدری**

### 🔎 موتور سوم اختیاری OCR: Surya — انتخاب کاربر
درخواست: «لطفا در بخش ocr به صورت انتخابی امکان استفاده از مدل surya را هم فراهم کن اگر کاربر خواست با این مدل استفاده نماید».
- موتور جدید **Surya OCR** (`surya-ocr` از PyPI) به‌عنوان گزینهٔ **اختیاری** در سایدبار اضافه شد؛ **پیش‌فرض بدون تغییر می‌ماند** (Tesseract + EasyOCR) تا کیفیت تأییدشدهٔ فارسی حفظ شود
- پیاده‌سازی با الگوی provider موجود: `label_reader/ocr/surya_provider.py` — import تنبل و پیام راهنما وقتی نصب نیست (`pip install surya-ocr`)؛ خطا هرگز کل اپ را نمی‌اندازد
- خروجی Surya از همان **گیت کیفیت + رأی اجماعی + نگهبان‌های زبانی** عبور می‌کند (بدون میان‌بر)
- در وب تک‌فایلی هم گزینهٔ Surya به‌صورت پیوستگی‌دار با Tesseract.js قابل انتخاب است

### 🎨 تجلی پررنگ‌تر آبی/سفید/سبز/قرمز در پس‌زمینه و گرافیک
درخواست: «تجلی رنگ آبی، سفید، سبز، قرمز بیشتر خودش رو نشون بده در پس زمینه و گرافیک صفحه».
- **ریبون چهاررنگ** (آبی اعتماد `#1E88E5` · سفید بهداشت · سبز سلامت `#43A047` · قرمز هشدار `#E53935`) در بالای صفحه
- هاله‌های رنگی نرم آبی/سبز/قرمز در **پس‌زمینهٔ هیرو و سایدبار** (هر دو تم روشن و تاریک)
- **خط گرادیانی چهاررنگ** روی کارت‌ها + لوگوی آبی اعتماد + نوار عنوان قرمز/سبز برای بخش‌های هشدار/موفق
- همین تجلی در **اپ موبایل/PWA** اعمال شد و کش سرویس‌ورکر → `lbr-mobile-v15`

### 📱 انتشار نسخهٔ موبایل اپلیکیشن
- داراییٔ اختصاصی **`LabelVoice-v2.2.0-Mobile-App-PWA.zip`**: PWA کامل (HTML/CSS/JS خالص + Service Worker + Manifest + آیکون‌های قابل‌نصب) — روی گوشی یا هر میزبان استاتیک قابل استقرار
- نسخهٔ اندروید: `versionCode 14 / versionName 2.2.0`
- راهنمای نصب گام‌به‌گام در `README-MOBILE-fa.md` داخل بسته

### 🧠 شفافیت مدل‌ها — نام‌بردن صریح در همهٔ مستندات و درون سامانه
درخواست: «در مستندات و راهنما و... حتما استفاده از مدل ها را با نام بردن از اون ها بیار».
| مرحله | مدل / موتور |
|---|---|
| پیش‌پردازش تصویر | **OpenCV** (کلاسیک، بدون مدل یادگیری) |
| خواندن متن — موتور اول | **Tesseract 5** (دادهٔ زبان `fas+eng`) |
| خواندن متن — موتور دوم مکمل | **EasyOCR** — CRNN (fa+en)، اختیاری |
| خواندن متن — موتور سوم | **Surya OCR** (`surya-ocr`) — اختیاری، انتخاب کاربر |
| دستیار خوانش دوم (اختیاری) | **Qwen/Qwen3-VL-2B-Instruct** — کاملاً محلی، پیش‌فرض خاموش |
| پردازش متن و فیلدها | الگوها و قواعد فارسی + گیت کیفیت + رأی اجماعی |
| تولید پاسخ فارسی | قالب‌ساز قاعده‌محور + نگهبان ایمنی |
| خوانش صوتی | **edge-tts** — `fa-IR-FaridNeural` / `fa-IR-DilaNeural` |
| وب / PWA / تک‌فایل | **Tesseract.js 6.0.1 (WASM)** + Web Speech API |

فناوری ساخت اپ موبایل: **PWA (Progressive Web App) با HTML/CSS/JS خالص + Service Worker (`sw.js`) + Web App Manifest + آیکون‌های maskable** — بدون فریم‌ورک، بدون نیاز به فروشگاه اپ.

### ✔️ کیفیت
- **۱۲۴/۱۲۴ آزمون pytest** + **۶۴/۶۴ آزمون Node**
- نام‌فایل‌های ZIP کاملاً ASCII (مقاوم به مخدوش‌شدگی انکودینگ)
- خط قرمز پابرجا: فقط بازخوانی «روی بسته چه نوشته»؛ بدون توصیهٔ پزشکی؛ ردیابی‌پذیری هر فیلد به شواهد OCR
"""

API = f"https://api.github.com/repos/{REPO}"
HDR = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "Content-Type": "application/json",
}


def req(url: str, data=None, method="GET", raw=None):
    body = raw if raw is not None else (json.dumps(data).encode() if data else None)
    r = urllib.request.Request(url, data=body, headers=HDR, method=method)
    with urllib.request.urlopen(r) as resp:
        payload = resp.read()
    return json.loads(payload) if payload else {}


def main() -> None:
    # ۱) Release را بساز (یا اگر بود همان را بگیر)
    try:
        rel = req(f"{API}/releases", data={"tag_name": "v2.2.0", "target_commitish": "main",
                                           "name": "LabelVoice v2.2.0 — Surya OCR اختیاری + پالت پررنگ + انتشار اپ موبایل",
                                           "body": BODY, "draft": False, "prerelease": False}, method="POST")
        print(f"release created: #{rel['id']}")
    except Exception as e:
        if "already_exists" in str(e):
            rel = req(f"{API}/releases/tags/v2.2.0")
            # بدنه را به‌روز کن
            rel = req(f"{API}/releases/{rel['id']}", data={"body": BODY, "name": "LabelVoice v2.2.0 — Surya OCR اختیاری + پالت پررنگ + انتشار اپ موبایل"}, method="PATCH")
            print(f"release exists, updated: #{rel['id']}")
        else:
            raise
    rid = rel["id"]

    # ۲) آپلود دارایی‌ها
    for path, name, label in ASSETS:
        p = Path(path)
        assert p.exists(), f"missing asset: {p}"
        existing = {a["name"] for a in rel.get("assets", [])}
        if name in existing:
            print(f"asset exists, skipping: {name}")
            continue
        up = urllib.request.Request(
            f"https://uploads.github.com/repos/{REPO}/releases/{rid}/assets?name={name}",
            data=p.read_bytes(),
            headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/zip",
                     "Content-Length": str(p.stat().st_size)},
            method="POST")
        with urllib.request.urlopen(up) as resp:
            print(f"uploaded: {resp.status} {name}")
    print("DONE")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""انتشار Release v2.3.0 — توکن فقط گذرا از ورودی استاندارد؛ هرگز ذخیره نمی‌شود."""
import json
import os
import sys
import urllib.request
from pathlib import Path

REPO = "hjalilvand2004-coder/LabelVoice"
TOKEN = os.environ.get("GH_TOKEN") or sys.stdin.readline().strip()
ASSETS = [
    ("/home/z/my-project/labelvoice-clone/mobile-app/label-reader-singlefile.html",
     "label-reader-singlefile-v2.3.0.html",
     "تک‌فایل قابل حمل با موتور سوم Surya + پالت دارویی پررنگ — اجرا بدون پایتون با دوبار کلیک"),
    ("/home/z/my-project/download/LabelVoice-v2.3.0-Portable-Web.zip",
     "LabelVoice-v2.3.0-Portable-Web.zip",
     "بستهٔ قابل حمل: START-HERE.html + تک‌فایل + webapp/ + لانچرهای ویندوز/لینوکس"),
    ("/home/z/my-project/download/LabelVoice-v2.3.0-Mobile-App-PWA.zip",
     "LabelVoice-v2.3.0-Mobile-App-PWA.zip",
     "اپ موبایل (PWA): index.html + Service Worker + Manifest + آیکون‌ها — نصب روی گوشی یا میزبانی محلی"),
    ("/home/z/my-project/download/LabelVoice-v2.3.0-Full-Project.zip",
     "LabelVoice-v2.3.0-Full-Project.zip",
     "کل پروژه: دسکتاپ Streamlit + وب + اپ موبایل + آزمون‌ها + مستندات"),
    ("/home/z/my-project/download/LabelVoice-Android-2.3.0.apk",
     "LabelVoice-v2.3.0-Android.apk",
     "نسخهٔ نصب‌پذیر اندروید (versionCode 15) — WebView محلی با موتور کامل PWA، امضاشده"),
]
BODY = """## برچسب‌خوان هوشمند دارو و محصولات — نسخه ۲.۳.۰

**توسعه و طراحی: حمید جلیلوند و نوید بدری**

### 🎛 منوی متنوع انتخاب موتور OCR — کاربر تصمیم می‌گیرد با کدام مدل خوانده شود
درخواست: «قرار بود برای موتور ocr حالت انتخابی را متنوع‌تر کنی از روش‌هایی مثل Surya یا Qwen3-VL-2B-Instruct و... یعنی کاربر بتواند انتخاب کند با کدام مدل خوانده شود».

سایدبار دسکتاپ اکنون **پنج گزینهٔ خوانش** دارد — خروجی هر موتور از همان گیت کیفیت، ادغام بهترین-اول و رأی اجماعی عبور می‌کند:

| # | موتور | نوع | وضعیت |
|---|---|---|---|
| ۱ | **Tesseract 5** (دادهٔ `fas+eng`) | سبک و سریع | پیش‌فرض |
| ۲ | **EasyOCR** — CRNN (fa+en) | شبکهٔ عمیق | اختیاری |
| ۳ | **Surya OCR** — ترنسفورمری چندزبانه | تشخیص خط + بازشناسی | اختیاری (v2.2.0) |
| ۴ | **Qwen/Qwen3-VL-2B-Instruct** — مدل زبانی-بینایی | خوانش یکجای کل تصویر | اختیاری (v2.3.0 — **جدید**) |
| ۵ | **خودکار** | اولین موتور در دسترس | tesseract ← easyocr |

#### تغییرات فنی v2.3.0
- **رابط کامل `OcrProvider` در `QwenVlmProvider` پیاده شد** — پیش‌تر این مدل فقط «دستیار مکمل» بود؛ حالا `run()` خروجی مدل را به قطعه‌های `OcrRaw` (شناسهٔ موتور `qwen3-vl`، اطمینان تخمینی ۰٫۶۰) تبدیل می‌کند تا دقیقاً از همان زنجیرهٔ گیت کیفیت/اجماع/استخراج فیلد عبور کند
- **انتخاب با `LBR_OCR_PROVIDER=qwen3-vl`** یا گزینهٔ سایدبار «Qwen3-VL-2B-Instruct»؛ نبود وابستگی با پیام شفاف راهنمای نصب رد می‌شود (`pip install "transformers>=4.57" accelerate`؛ نخستین اجرا ~۴-۵ گیگابایت دانلود و پس از آن آفلاین)
- **بهینه‌سازی خوانش یکجا:** واریانت‌های پیش‌پردازش برای این موتور به «original» محدود شد (`vlm_variants`) — مدل زبانی-بینایی کل تصویر را یکجا می‌خواند و گذرهای چندواریانته بی‌معناست
- **گارد تکرار:** اگر Qwen3-VL موتور اصلی باشد، دستیار مکمل دیگر دوباره اجرا نمی‌شود
- ثبت در رجیستری مدل‌ها (`models_info.py`) + راهنما + `docs/INSTALL.md` (بخش ۴-ج) + `docs/ARCHITECTURE.md` + راهنمای موبایل — کش سرویس‌ورکر → `lbr-mobile-v16`
- **اندروید:** versionCode **15** / versionName **2.3.0** — APK بازساخت و امضای مجدد شد
- آزمون: **۱۳۲/۱۳۲ pytest** (۹ آزمون جدید Qwen3-VL) + **۶۴/۶۴ Node**

### 🧠 شفافیت مدل‌ها (پابرجا)
| مرحله | مدل / موتور |
|---|---|
| پیش‌پردازش تصویر | **OpenCV** (کلاسیک، بدون مدل یادگیری) |
| خواندن متن — موتور ۱ | **Tesseract 5** — `fas+eng`، گذرهای زبانی جدا، PSM 3/6/11 |
| خواندن متن — موتور ۲ | **EasyOCR** — CRNN (fa+en)، اختیاری |
| خواندن متن — موتور ۳ | **Surya OCR** — ترنسفورمری، اختیاری |
| خواندن متن — موتور ۴ | **Qwen/Qwen3-VL-2B-Instruct** — زبانی-بینایی، اختیاری (**جدید**) |
| دستیار خوانش دوم (اختیاری) | **Qwen3-VL** — فقط سطرهای تازه با شناسهٔ `vlm-*` |
| پردازش متن و فیلدها | قواعد فارسی + گیت کیفیت + رأی اجماعی |
| تولید پاسخ فارسی | قالب‌ساز قاعده‌محور + نگهبان ایمنی |
| خوانش صوتی | **edge-tts** — `fa-IR-FaridNeural` / `DilaraNeural` |
| وب / PWA / تک‌فایل / اندروید | **Tesseract.js 6.0.1 (WASM)** + Web Speech API — کاملاً آفلاین |

### ✔️ کیفیت و خط قرمز
- هر فیلد به شواهد موتورِ منتخبِ کاربر ردیابی‌پذیر است؛ «قدرت درج‌شده» هرگز «دوز مصرف» نیست؛ بدون توصیهٔ پزشکی
- در نسخهٔ مرورگر/موبایل/تک‌فایل خوانش همیشه با Tesseract.js (WASM) انجام می‌شود — موتورهای سنگین فقط دسکتاپ
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
        rel = req(f"{API}/releases", data={"tag_name": "v2.3.0", "target_commitish": "main",
                                           "name": "LabelVoice v2.3.0 — Surya OCR اختیاری + پالت پررنگ + انتشار اپ موبایل",
                                           "body": BODY, "draft": False, "prerelease": False}, method="POST")
        print(f"release created: #{rel['id']}")
    except Exception as e:
        if "already_exists" in str(e):
            rel = req(f"{API}/releases/tags/v2.3.0")
            # بدنه را به‌روز کن
            rel = req(f"{API}/releases/{rel['id']}", data={"body": BODY, "name": "LabelVoice v2.3.0 — Surya OCR اختیاری + پالت پررنگ + انتشار اپ موبایل"}, method="PATCH")
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

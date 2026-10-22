# راهنمای نصب و اجرا

## پیش‌نیازها

- Python 3.11 یا بالاتر (توسعه و آزمون با Python 3.12 انجام شد)
- اتصال اینترنت برای نصب بسته‌ها و (فقط بار اول) دانلود داده زبان و مدل‌ها
- پردازش اصلی تصویر محلی است؛ GPU لازم نیست

## ۱) نصب Tesseract (موتور پیش‌فرض OCR)

**Ubuntu / Debian:**
```bash
sudo apt update && sudo apt install -y tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
- نصب‌کننده UB-Mannheim را از صفحه پروژه Tesseract دریافت و اجرا کنید.
- مسیر نصب (مثلاً `C:\Program Files\Tesseract-OCR`) را به PATH اضافه کنید.

بررسی:
```bash
tesseract --version
tesseract --list-langs
```

## ۲) داده زبان فارسی (fas.traineddata)

داده زبان فارسی در پروژه (`models/tessdata/fas.traineddata`) همراه بسته است. اگر حذف شده بود یا از نسخه خام استفاده می‌کنید:

```bash
python scripts/download_tessdata.py
```

این اسکریپت `fas.traineddata` (کیفیت tessdata_best، حدود ۳٫۳ مگابایت) را از مخزن رسمی tesseract-ocr دانلود و در صورت نیاز `eng.traineddata` را از نصب سیستمی کپی می‌کند.

**بدون این فایل، خواندن فارسی فعال نمی‌شود** و محصول صادقانه فقط eng را اعلام می‌کند (ادعای فارسی بدون داده واقعی وجود ندارد).

## ۳) محیط مجازی و وابستگی‌ها

```bash
python3 -m venv .venv
source .venv/bin/activate        # ویندوز: .venv\Scripts\activate
pip install -r requirements.txt
```

نسخه‌های تأییدشده در محیط توسعه (Python 3.12):

| بسته | نسخه |
|---|---|
| streamlit | 1.66.1 |
| opencv-python-headless | 4.13.0.90 |
| Pillow | 11.3.0 |
| numpy | 2.1.3 |
| pydantic / pydantic-settings | 2.12.5 / 2.13.1 |
| pytesseract | 0.3.13 |
| gTTS / edge-tts | 2.5.4 / 7.3.1 |
| pytest | 9.0.2 |

## ۴) EasyOCR (اختیاری)

نصب سنگین: PyTorch CPU حدود ۲۰۰ مگابایت + مدل‌های تشخیص/بازشناسی (~۲۸۵ مگابایت در اولین اجرا، به `~/.EasyOCR` دانلود می‌شود):

```bash
pip install -r requirements-easyocr.txt
```

سپس در رابط کاربری یا با `LBR_OCR_PROVIDER=easyocr` انتخاب کنید. اولین اجرا کند است (دانلود و بارگذاری مدل) و پس از آن نمونه در حافظه نگه داشته می‌شود.

## ۵) اجرا

```bash
# رابط کاربری (پیش‌فرض فقط روی localhost)
streamlit run app.py

# خط فرمان بدون رابط
python scripts/run_demo_cli.py sample_images/en_paracetamol_500mg.png
python scripts/run_demo_cli.py sample.png --engine easyocr --json out.json
```

## ۶) آزمون‌ها

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -q
```

آزمون‌های وابسته به موتور OCR واقعی در نبود Tesseract/داده زبان به‌صورت `skip` می‌شوند و عدد جعلی تولید نمی‌کنند. برای اجرای آزمون‌های TTS نیازمند اینترنت: `RUN_TTS_TESTS=1 python -m pytest tests/test_tts_llm.py -q`

## ۷) سنجش دقت (اختیاری)

```bash
python scripts/make_sample_images.py   # تولید مجدد نمونه‌ها
python scripts/evaluate.py             # جدول واقعی دقت/زمان روی sample_images
```

## ۸) تنظیمات (`.env`)

از `.env.example` کپی بگیرید. مهم‌ترین کلیدها (همگی با پیشوند `LBR_`):

| کلید | پیش‌فرض | توضیح |
|---|---|---|
| `LBR_OCR_PROVIDER` | tesseract | tesseract / easyocr / auto |
| `LBR_OCR_LANGUAGES` | fas+eng | زبان‌های Tesseract |
| `LBR_TTS_PROVIDER` | edge | edge / gtts / none |
| `LBR_TTS_VOICE` | fa-IR-FaridNeural | صدای فارسی edge-tts |
| `LBR_MAX_FILE_MB` | 10 | سقف حجم فایل تصویر |
| `LBR_LLM_ENABLED` | false | فعال‌سازی بازنویسی LLM |
| `LBR_LLM_BASE_URL` / `LBR_LLM_MODEL` / `LBR_LLM_API_KEY` | — | فقط با فعال‌سازی صریح؛ کلید از متغیر محیط |

## عیب‌یابی

- **«tesseract نصب نیست»**: مسیر باینری در PATH نیست؛ در ویندوز مسیر نصب را اضافه کنید.
- **«داده زبان فارسی یافت نشد»**: `python scripts/download_tessdata.py` را اجرا کنید.
- **«سرویس edge-tts پاسخ نداد»**: اینترنت لازم است؛ نتیجه متنی همچنان نمایش داده می‌شود و gTTS جایگزین می‌شود.
- **خوانش ضعیف ارقام فارسی**: محدودیت شناخته‌شده Tesseract است؛ موتور easyocr را امتحان کنید یا فیلد را با «اصلاح دستی» تصحیح کنید (docs/LIMITATIONS.md).

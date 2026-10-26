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
| sherpa-onnx | 1.12.40 (فونِم‌ساز داخلی — نسخهٔ 2.x کار نمی‌کند) |
| pytest | 9.0.2 |

## ۴) EasyOCR (اختیاری)

نصب سنگین: PyTorch CPU حدود ۲۰۰ مگابایت + مدل‌های تشخیص/بازشناسی (~۲۸۵ مگابایت در اولین اجرا، به `~/.EasyOCR` دانلود می‌شود):

```bash
pip install -r requirements-easyocr.txt
```

سپس در رابط کاربری یا با `LBR_OCR_PROVIDER=easyocr` انتخاب کنید. اولین اجرا کند است (دانلود و بارگذاری مدل) و پس از آن نمونه در حافظه نگه داشته می‌شود.

## ۴-ب) Surya OCR (اختیاری — v2.2.0، به انتخاب کاربر)

موتور سوم خوانش با تشخیص خط + بازشناسی ترنسفورمری (تک‌مدل چندزبانه شامل فارسی).
نصب (به torch نیاز دارد؛ برای CPU از ایندکس رسمی پایتورچ):

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install surya-ocr
```

- در رابط کاربری، «موتور OCR» را روی گزینهٔ «Surya» بگذارید یا `LBR_OCR_PROVIDER=surya` تنظیم کنید.
- بار اول وزن مدل‌ها از Hugging Face دانلود می‌شود (چند صد مگابایت در `~/.cache/datalab`)؛ پس از آن کاملاً آفلاین.
- حداقل حافظهٔ آزاد: ~۴ گیگابایت (در کمبود حافظه، بارگذاری خودکار به float16 برمی‌گردد).
- خروجی سوریا از همان گیت کیفیت و رأی اجماعی خط لوله عبور می‌کند و نامش در خط‌زمان مراحل اعلام می‌شود.
- در زنجیرهٔ «auto» قرار ندارد؛ فقط با انتخاب صریح اجرا می‌شود. در نسخهٔ مرورگر/تک‌فایل (WASM) پشتیبانی نمی‌شود.
- آزمون زندهٔ سنگین: `LBR_TEST_SURYA_LIVE=1 pytest tests/test_surya_provider.py -k live`

## ۴-ج) Qwen3-VL-2B-Instruct (اختیاری — v2.3.0، به انتخاب کاربر)

موتور چهارم خوانش — مدل زبانی-بینایی **Qwen/Qwen3-VL-2B-Instruct** که کل تصویر را یکجا سطر به سطر می‌خواند (همان مدلی که از v2.0.0 دستیار مکمل است).
نصب:

```bash
pip install "transformers>=4.57" accelerate
```

- در رابط کاربری، «موتور OCR» را روی گزینهٔ «Qwen3-VL-2B-Instruct» بگذارید یا `LBR_OCR_PROVIDER=qwen3-vl` تنظیم کنید.
- بار اول مدل از Hugging Face دانلود می‌شود (~۴ تا ۵ گیگابایت)؛ پس از آن کاملاً آفلاین.
- خروجی آن (با شناسهٔ موتور `qwen3-vl` و اطمینان تخمینی ۰٫۶۰) از همان گیت کیفیت و رأی اجماعی عبور می‌کند.
- اگر همین مدل موتور اصلی باشد، دستیار مکمل دیگر دوباره اجرا نمی‌شود (خوانش دوباره بی‌معناست).
- مناسب برچسب‌های شلوغ/چرخیده که موتورهای کلاسیک ضعیف می‌خوانند؛ کندتر از تسراکت است (استنتاج ترنسفورمری).
- در زنجیرهٔ «auto» قرار ندارد؛ فقط با انتخاب صریح اجرا می‌شود. در نسخهٔ مرورگر/تک‌فایل (WASM) پشتیبانی نمی‌شود.
- آزمون زندهٔ سنگین: `LBR_TEST_VLM_LIVE=1 pytest tests/test_qwen3vl_provider.py -k live`

> **خلاصهٔ انتخاب موتور (v2.3.0):** در سایدبار «موتور OCR» یکی از پنج گزینه:
> **Tesseract 5** (پیش‌فرض سبک) · **EasyOCR** (CRNN) · **Surya** (ترنسفورمری) ·
> **Qwen3-VL-2B-Instruct** (زبانی-بینایی) · **خودکار** — همهٔ موتورها خط پردازش
> مشترک (گیت کیفیت + رأی اجماعی) را طی می‌کنند.

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
| `LBR_OCR_PROVIDER` | tesseract | tesseract / easyocr / surya / auto |
| `LBR_OCR_LANGUAGES` | fas+eng | زبان‌های Tesseract |
| `LBR_TTS_PROVIDER` | local | local / none |
| `LBR_TTS_VOICE` | fa_IR-amir-medium (Piper — لوکال) | مدل باندل‌شده در `models/tts/piper-fa_IR-amir/`؛ مسیر جایگزین: `LBR_TTS_MODEL_DIR` |
| `LBR_MAX_FILE_MB` | 10 | سقف حجم فایل تصویر |
| `LBR_LLM_ENABLED` | false | فعال‌سازی بازنویسی LLM |
| `LBR_SURYA_VARIANTS` | original,gray_clahe | نسخه‌های پردازشی که سوریا اجرا می‌کند (v2.2.0) |
| `LBR_SURYA_MODEL_DIR` | — | مسیر اختصاصی کش مدل‌های سوریا (اختیاری) |
| `LBR_LLM_BASE_URL` / `LBR_LLM_MODEL` / `LBR_LLM_API_KEY` | — | فقط با فعال‌سازی صریح؛ کلید از متغیر محیط |

## محل فایل مدل‌ها (v2.12.2 — نوع، نام و مسیر هر مدل)

مدل‌های سامانه دو دسته‌اند: **باندل‌شده در پروژه** (فایل مدل داخل مخزن است و همراه بستهٔ قابل حمل آمادهٔ اجرا آفلاین می‌آید) و **نصب جداگانه** (موتور/کتابخانه با pip یا نصاب سیستمی؛ وزن‌ها در نخستین اجرا دانلود و روی همین دستگاه ذخیره می‌شود):

| نقش | نوع | نام مدل / داده | وضعیت | مسیر فایل |
|---|---|---|---|---|
| دادهٔ زبان Tesseract فارسی/انگلیسی | traineddata (LSTM) | fas (tessdata_best) + eng | باندل‌شده در پروژه | `models/tessdata/fas.traineddata` (~۳٫۳MB) · `models/tessdata/eng.traineddata` (~۴٫۱MB)؛ جایگزین: `LBR_TESSDATA_DIR` |
| خوانش صوتی — مدل | VITS — فایل ONNX | Piper «fa_IR-amir-medium» | باندل‌شده در پروژه | `models/tts/piper-fa_IR-amir/` — `model.onnx` (fp32 ~۶۳MB) + `model.int8.onnx` (~۱۸٫۶MB) + `tokens.txt` + `fa_IR-amir-medium.onnx.json` + `espeak-ng-data/` (۳۵۵ فایل)؛ جایگزین: `LBR_TTS_MODEL_DIR` |
| خوانش صوتی — مدل مرورگر/APK | همان مدل، کوانتیزهٔ int8 | `fa_IR-amir-medium.int8.onnx` | باندل‌شده در پروژه | `mobile-app/vendor/tts/` (+ onnxruntime-web و piper-phonemize WASM) |
| OCR موتور دوم (اختیاری) | CRNN + CRAFT | EasyOCR 1.7 (fa+en) | نصب جداگانه (pip) + دانلود وزن | وزن‌ها: `~/.EasyOCR/model/`؛ جایگزین: `LBR_EASYOCR_MODEL_DIR` |
| OCR موتور سوم (اختیاری) | ترنسفورمر تشخیص خط + بازشناسی | Surya (surya-ocr) | نصب جداگانه (pip) + دانلود وزن | وزن‌ها: کش Hugging Face `~/.cache/huggingface/hub`؛ جایگزین: `LBR_SURYA_MODEL_DIR` |
| OCR موتور چهارم + دستیار دوم (اختیاری) | مدل زبانی-بینایی (VLM) | Qwen/Qwen3-VL-2B-Instruct | نصب جداگانه (transformers) + دانلود وزن | `~/.cache/huggingface/hub/models--Qwen--Qwen3-VL-2B-Instruct/` (safetensors، ~۴ تا ۵GB) |
| موتور اجرای صوت دسکتاپ | کتابخانه استنتاج ONNX | sherpa-onnx 1.12.40 | نصب جداگانه (pip) | فونِم‌ساز espeak-ng داخلی — بدون فایل مدل جداگانه |

> موتور اول OCR (Tesseract 5) و کتابخانهٔ پیش‌پردازش (OpenCV) فایل مدل ندارند: باینری سیستمی نصب می‌شوند. جدول کامل و همیشه‌به‌روز: `label_reader/models_info.py` (تابع `models_paths_markdown_fa`).

## عیب‌یابی

- **«tesseract نصب نیست»**: مسیر باینری در PATH نیست؛ در ویندوز مسیر نصب را اضافه کنید.
- **«داده زبان فارسی یافت نشد»**: `python scripts/download_tessdata.py` را اجرا کنید.
- **«مدل صوتی لوکال یافت نشد»**: پوشهٔ `models/tts/piper-fa_IR-amir/` (یا `LBR_TTS_MODEL_DIR`) باید مدل و tokens.txt را داشته باشد؛ TTS کاملاً لوکال است و به اینترنت نیازی ندارد.
- **«پخش صوتی انجام نمی‌شود» (وب/موبایل)**: موتور صوتی کاملاً لوکال است (Piper روی onnxruntime-web) و به اینترنت نیاز ندارد؛ اگر صدا نشنیدید، دکمهٔ پخش را یک‌بار دیگر بزنید (WebView اندروید پخش را بعد از تعامل کاربر مجاز می‌کند) و حجم دستگاه را بررسی کنید. در دسکتاپ هم بستهٔ `sherpa-onnx==1.12.40` نصب باشد.
- **خوانش ضعیف ارقام فارسی**: محدودیت شناخته‌شده Tesseract است؛ موتور easyocr را امتحان کنید یا فیلد را با «اصلاح دستی» تصحیح کنید (docs/LIMITATIONS.md).

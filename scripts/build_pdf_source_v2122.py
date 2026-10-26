# -*- coding: utf-8 -*-
"""ساخت سند منبع PDF مستندات v2.12.2 از قالب v2.12.1

v2.12.2 = مستندات مدل‌ها:
  (۱) جدول «نوع، نام و مسیر فایل هر مدل» (باندل‌شده در پروژه / نصب جداگانه)
  (۲) بازنویسی مستندات با لحن «بر اساس بررسی و تحلیل صورت گرفته»
  (۳) حذف بازمانده‌های قدیمی (Web Speech API در جدول مدل‌ها)
"""
import shutil
from pathlib import Path

SRC = Path("/home/z/my-project/download/LabelVoice-Documentation-v2.12.1")
DST = Path("/home/z/my-project/download/LabelVoice-Documentation-v2.12.2")

if DST.exists():
    shutil.rmtree(DST)
shutil.copytree(SRC, DST)
(DST / "LabelVoice-Documentation-v2.12.1.pdf").unlink(missing_ok=True)

p = DST / "LabelVoice-Documentation.html"
html = p.read_text(encoding="utf-8")


def rep(old, new):
    global html
    assert old in html, "NOT FOUND: " + old[:80]
    html = html.replace(old, new)


# ---------- عنوان و جلد ----------
rep("<title>LabelVoice — مستندات فنی نسخهٔ ۲.۱۲.۰</title>",
    "<title>LabelVoice — مستندات فنی نسخهٔ ۲.۱۲.۲</title>")
rep('<div class="ver">نسخهٔ ۲.۱۲.۰ — مدل صوتی Piper فارسی باندل‌شده در پروژه · کاملاً لوکال و بدون اینترنت · جایگزینی کامل سرویس‌های آنلاین</div>',
    '<div class="ver">نسخهٔ ۲.۱۲.۲ — جدول «نوع، نام و مسیر فایل هر مدل» · تفکیک باندل‌شده در پروژه از نصب جداگانه · مستندات با لحن بررسی و تحلیل</div>')
rep('<div class="big">LabelVoice ۲.۱۲.۰</div>', '<div class="big">LabelVoice ۲.۱۲.۲</div>')
rep('مستندات کامل HTML: mobile-app/documentation.html · شواهد صوتی: scripts/evidence_v2120/',
    'مستندات کامل HTML: mobile-app/documentation.html · رجیستری مدل‌ها: label_reader/models_info.py')

# ---------- پاک‌سازی لحن: بخش ۴ (مدل صوتی) ----------
rep('بازخورد کاربر: «در مستند نام Edge TTS و دو صدای فارسی فرید و دلارا آمده است؛ این‌ها صداهای سرویس آنلاین مایکروسافت‌اند، نه مدل‌هایی که داخل پروژه دانلود شده باشند. من نیاز دارم یک مدل دانلود کنی و در فایل‌های پروژه قرار بدی و به‌صورت لوکال از مدل در برنامه استفاده کنم — برای همه موارد». پاسخ: مدل <b>Piper VITS «fa_IR-amir-medium»</b>',
    'چرایی — بر اساس بررسی و تحلیل مستندات قبلی: صداهای «فرید» و «دلارا» سرویس آنلاین مایکروسافت (Edge TTS) بودند، نه مدل باندل‌شده؛ نیازمندی پروژه این است که همهٔ مدل‌ها دانلود و داخل فایل‌های پروژه قرار بگیرند و کاملاً لوکال اجرا شوند. پاسخ: مدل <b>Piper VITS «fa_IR-amir-medium»</b>')

# ---------- بخش ۴: کارت جدید — جدول مسیر مدل‌ها (v2.12.2) ----------
paths_card = '''  <div class="card"><h4>۵) جدول «نوع، نام و مسیر فایل هر مدل» (تازه در v2.12.2)</h4>
    <p>هر مدل — باندل‌شده یا نصب جداگانه — با «نوع + نام + مسیر دقیق فایل» مستند می‌شود. «باندل‌شده در پروژه» یعنی فایل مدل داخل فایل‌های پروژه است و همراه با دانلود آمادهٔ اجرای آفلاین می‌آید؛ «نصب جداگانه» یعنی کتابخانه/موتور با pip یا نصاب سیستمی نصب می‌شود و وزن‌هایش در نخستین اجرا دانلود و روی همین دستگاه ذخیره می‌شود. تک‌منبع حقیقت: تابع <code>models_paths_markdown_fa</code> در <code>label_reader/models_info.py</code>.</p>
    <table>
      <thead><tr><th>نقش</th><th>نوع</th><th>نام مدل / داده</th><th>وضعیت</th><th>مسیر فایل</th></tr></thead>
      <tbody>
        <tr><td>دادهٔ زبان Tesseract فارسی/انگلیسی</td><td>traineddata (LSTM)</td><td>fas (tessdata_best) + eng</td><td>باندل‌شده در پروژه</td><td><code>models/tessdata/fas.traineddata</code> (~۳٫۳MB) · <code>models/tessdata/eng.traineddata</code> (~۴٫۱MB)</td></tr>
        <tr><td>خوانش صوتی — مدل</td><td>VITS — فایل ONNX</td><td>Piper «fa_IR-amir-medium» (rhasspy/piper-voices v1.0.0)</td><td>باندل‌شده در پروژه</td><td>دسکتاپ: <code>models/tts/piper-fa_IR-amir/</code> — model.onnx (fp32 ~۶۳MB) + model.int8.onnx (~۱۸٫۶MB) + tokens.txt + پیکربندی + espeak-ng-data (۳۵۵ فایل) · مرورگر/APK: <code>mobile-app/vendor/tts/fa_IR-amir-medium.int8.onnx</code> (~۱۸MB)</td></tr>
        <tr><td>خوانش صوتی — موتور اجرا (دسکتاپ)</td><td>کتابخانه استنتاج ONNX</td><td>sherpa-onnx 1.12.40 (فونِم‌ساز espeak-ng داخلی)</td><td>نصب جداگانه (pip)</td><td>کد: <code>label_reader/tts/local_provider.py</code>؛ مسیر مدل جایگزین: <code>LBR_TTS_MODEL_DIR</code></td></tr>
        <tr><td>خوانش صوتی — موتور اجرا (مرورگر/APK)</td><td>WebAssembly</td><td>onnxruntime-web 1.18 + piper-phonemize</td><td>باندل‌شده در پروژه</td><td><code>mobile-app/vendor/tts/</code> — ort + piper_phonemize WASM/data (espeak تریم‌شدهٔ fa+en)</td></tr>
        <tr><td>OCR موتور مرورگر/موبایل</td><td>WebAssembly</td><td>Tesseract.js 6.0.1 + core 6.1.2</td><td>باندل‌شده در پروژه</td><td><code>mobile-app/vendor/tesseract/</code> + <code>mobile-app/vendor/core/</code> + دادهٔ زبان <code>mobile-app/lang/integer|best/*.traineddata.gz</code></td></tr>
        <tr><td>OCR موتور دوم (اختیاری)</td><td>CRNN + تشخیص ناحیه CRAFT</td><td>EasyOCR 1.7 (fa+en)</td><td>نصب جداگانه (pip) + دانلود وزن</td><td>وزن‌ها: <code>~/.EasyOCR/model/</code>؛ جایگزین: <code>LBR_EASYOCR_MODEL_DIR</code></td></tr>
        <tr><td>OCR موتور سوم (اختیاری)</td><td>ترنسفورمر تشخیص خط + بازشناسی</td><td>Surya (surya-ocr)</td><td>نصب جداگانه (pip) + دانلود وزن</td><td>کش Hugging Face: <code>~/.cache/huggingface/hub</code>؛ جایگزین: <code>LBR_SURYA_MODEL_DIR</code></td></tr>
        <tr><td>OCR موتور چهارم + دستیار دوم (اختیاری)</td><td>مدل زبانی-بینایی (VLM)</td><td>Qwen/Qwen3-VL-2B-Instruct</td><td>نصب جداگانه (transformers) + دانلود وزن</td><td><code>~/.cache/huggingface/hub/models--Qwen--Qwen3-VL-2B-Instruct/</code> (safetensors، ~۴ تا ۵GB)</td></tr>
        <tr><td>موتور اول OCR و پیش‌پردازش</td><td>باینری سیستمی / کتابخانه (بدون مدل یادگیری)</td><td>Tesseract 5 · OpenCV 4.13</td><td>نصب جداگانه</td><td>بدون فایل مدل — کد: <code>label_reader/ocr/tesseract_provider.py</code> · <code>label_reader/preprocess.py</code></td></tr>
      </tbody>
    </table>
  </div>
'''
rep('''  <div class="card"><h4>۴) راستی‌آزمایی کیفیت کوانتیزهٔ int8</h4>''',
    paths_card + '''  <div class="card"><h4>۴) راستی‌آزمایی کیفیت کوانتیزهٔ int8</h4>''')

# ---------- WBS: نسخه‌های اجرا ----------
rep('│   ├─ sw.js (lbr-mobile-v25) · vendor/ · lang/       [WBS-8]  آفلاین کامل (+vendor/tts صوتی)',
    '│   ├─ sw.js (lbr-mobile-v27) · vendor/ · lang/       [WBS-8]  آفلاین کامل (+vendor/tts صوتی)')
rep('├─ android/                                           [WBS-9]  WebView — صدا با WASM لوکال (versionCode 24)',
    '├─ android/                                           [WBS-9]  WebView — صدا با WASM لوکال (versionCode 26)')
rep('PWA با کش <code>lbr-mobile-v25</code> کاملاً آفلاین است (شامل موتور صوتی)؛ APK اندروید versionCode 24 از صفحهٔ Releases — صدا بدون اینترنت.',
    'PWA با کش <code>lbr-mobile-v27</code> کاملاً آفلاین است (شامل موتور صوتی)؛ APK اندروید versionCode 26 (2.12.2) از صفحهٔ Releases — صدا بدون اینترنت.')
rep('موتورها: Tesseract 5 · EasyOCR · Surya · Qwen3-VL-2B-Instruct · صدا: Piper fa_IR-amir-medium (باندل‌شده)<br>',
    'موتورها: Tesseract 5 · EasyOCR · Surya · Qwen3-VL-2B-Instruct · صدا: Piper fa_IR-amir-medium (باندل‌شده)<br>مسیر فایل هر مدل در بخش ۴ (کارت ۵) و رجیستری مرکزی <code>label_reader/models_info.py</code><br>')

# ---------- تاریخچه: ردیف‌های v2.12.2 و v2.12.1 ----------
rep('''      <tr><td style="width:14%"><b>v2.12.0</b></td><td>مدل صوتی دانلودشده در فایل‌های پروژه:''',
    '''      <tr><td style="width:14%"><b>v2.12.2</b></td><td>مستندات مدل‌ها: جدول «نوع، نام و مسیر فایل هر مدل» با تفکیک باندل‌شده در پروژه از نصب جداگانه (تک‌منبع: <code>label_reader/models_info.py</code>) + بازنویسی همهٔ مستندات با لحن «بر اساس بررسی و تحلیل صورت گرفته» + حذف بازمانده‌های Web Speech API از جدول مدل‌ها و راهنمای کهنهٔ مرورگر Edge از عیب‌یابی؛ کش SW → lbr-mobile-v27؛ APK versionCode 26 (2.12.2).</td></tr>
      <tr><td style="width:14%"><b>v2.12.1</b></td><td>هم‌خوانی همهٔ نمایشگرهای نسخه با ریلیز — چیپ‌های جامانده در START-HERE، سایدبار/فوتر وب، مودال «درباره»، سند فنی و VERSION.txt ریشه (خوانده‌شده توسط bat) به ۲.۱۲.۱ رسید؛ کش SW → lbr-mobile-v26؛ APK versionCode 25.</td></tr>
      <tr><td style="width:14%"><b>v2.12.0</b></td><td>مدل صوتی دانلودشده در فایل‌های پروژه:''')
rep('<tr><td style="width:14%"><b>v2.11.0</b></td><td>مدل صوتی مشترک دسکتاپ/موبایل با Edge TTS (پل /api/tts + کلاینت مستقیم) — پس از بازخورد کاربر دربارهٔ وابستگی آنلاین، در v2.12.0 با مدل لوکال جایگزین شد.</td></tr>',
    '<tr><td style="width:14%"><b>v2.11.0</b></td><td>مدل صوتی مشترک دسکتاپ/موبایل با Edge TTS (پل /api/tts + کلاینت مستقیم) — بر اساس بررسی و تحلیل وابستگی آنلاین، در v2.12.0 با مدل لوکال جایگزین شد.</td></tr>')

p.write_text(html, encoding="utf-8")
print("source HTML v2.12.2 built:", p, len(html), "chars")
print("بازخورد کاربر remaining:", html.count("بازخورد کاربر"))

# -*- coding: utf-8 -*-
"""ساخت سند منبع PDF مستندات v2.12.0 از قالب QA-passed v2.10.0"""
import shutil
from pathlib import Path

SRC = Path("/home/z/my-project/download/LabelVoice-Documentation-v2.10.0")
DST = Path("/home/z/my-project/download/LabelVoice-Documentation-v2.12.0")

if DST.exists():
    shutil.rmtree(DST)
shutil.copytree(SRC, DST)
(DST / "LabelVoice-Documentation-v2.10.0.pdf").unlink(missing_ok=True)

p = DST / "LabelVoice-Documentation.html"
html = p.read_text(encoding="utf-8")


def rep(old, new):
    global html
    assert old in html, "NOT FOUND: " + old[:80]
    html = html.replace(old, new)


# ---------- عنوان و جلد ----------
rep("<title>LabelVoice — مستندات فنی نسخهٔ ۲.۱۰.۰</title>",
    "<title>LabelVoice — مستندات فنی نسخهٔ ۲.۱۲.۰</title>")
rep('<div class="sub">مستندات فنی — معماری، ممیزی مهندسی، ساختار شکست کار (WBS) و نقشهٔ درختی مخزن</div>',
    '<div class="sub">مستندات فنی — معماری، مدل صوتی لوکال، ساختار شکست کار (WBS) و نقشهٔ درختی مخزن</div>')
rep('<div class="ver">نسخهٔ ۲.۱۰.۰ — ممیزی مهندسی: ایمنی عدد در ادغام · حذف دوقلوی سرگردان · پیش‌پردازش مشروط · رکورد کامل خوانش خام</div>',
    '<div class="ver">نسخهٔ ۲.۱۲.۰ — مدل صوتی Piper فارسی باندل‌شده در پروژه · کاملاً لوکال و بدون اینترنت · جایگزینی کامل سرویس‌های آنلاین</div>')
rep('موتورها: Tesseract 5 · EasyOCR · Surya · Qwen3-VL-2B-Instruct (Qwen/Qwen3-VL-2B-Instruct)<br>',
    'موتورها: Tesseract 5 · EasyOCR · Surya · Qwen3-VL-2B-Instruct · صدا: Piper fa_IR-amir-medium (باندل‌شده)<br>')

# ---------- بخش ۲: معماری ----------
rep('← پاسخ قالبی + نگهبان ایمنی ← TTS (edge-tts/gTTS). موتورهای انتخابی:',
    '← پاسخ قالبی + نگهبان ایمنی ← TTS لوکال (Piper fa_IR-amir-medium با sherpa-onnx — بدون اینترنت). موتورهای انتخابی:')
rep('← TTS دستگاه (با پل بومی اندروید). «پل OCR» دسکتاپ',
    '← TTS لوکال (مدل Piper int8 در vendor/tts با onnxruntime-web — بدون سرویس ابری و بدون TTS گوشی). «پل OCR» دسکتاپ')

# ---------- بخش ۳: گام ۹ ----------
rep('دستورهای چاپ‌شده فقط داخل گیومه؛ پخش صوتی فقط با رضایت صریح.',
    'دستورهای چاپ‌شده فقط داخل گیومه؛ پخش صوتی با مدل لوکال Piper روی خود دستگاه — بدون هیچ سرویسی.')

# ---------- بخش جدید ۴ (TTS لوکال) + تغییر شماره بخش‌های بعدی ----------
new_section = '''  <!-- ۴ — v2.12.0 -->
  <div class="chapter-header">
    <div class="eyebrow">■ بخش ۴</div>
    <h2>تازه در v2.12.0 — مدل صوتی دانلودشده در فایل‌های پروژه (کاملاً لوکال)</h2>
    <div class="divider"></div>
  </div>
  <p>بازخورد کاربر: «در مستند نام Edge TTS و دو صدای فارسی فرید و دلارا آمده است؛ این‌ها صداهای سرویس آنلاین مایکروسافت‌اند، نه مدل‌هایی که داخل پروژه دانلود شده باشند. من نیاز دارم یک مدل دانلود کنی و در فایل‌های پروژه قرار بدی و به‌صورت لوکال از مدل در برنامه استفاده کنم — برای همه موارد». پاسخ: مدل <b>Piper VITS «fa_IR-amir-medium»</b> (منبع rhasspy/piper-voices v1.0.0 — لایسنس MIT) دانلود، کوانتیزه، راستی‌آزمایی و در هر دو زیرسیستم باندل شد؛ و همهٔ مسیرهای آنلاین به‌کلی حذف شدند.</p>
  <div class="card"><h4>۱) باندل مدل در هر دو زیرسیستم</h4>
    <p>دسکتاپ: <code>models/tts/piper-fa_IR-amir/</code> شامل <code>model.onnx</code> (fp32، ۶۳٫۲MB — کیفیت کامل و سریع) و <code>model.int8.onnx</code> (۱۸٫۶MB) + <code>tokens.txt</code> + <code>espeak-ng-data/</code> (۳۵۵ فایل) + گزارش کوانتیزه. وب/موبایل/APK: <code>mobile-app/vendor/tts/</code> شامل مدل int8 + پیکربندی Piper + onnxruntime-web 1.30 (WASM/SIMD) + فونِم‌ساز piper-phonemize WASM با دادهٔ espeak <b>تریم‌شدهٔ fa+en</b> (۱۸٫۰۸MB → ۱٫۲۸MB؛ ۴۹۴ → ۳۸۳ فایل — حذف واژه‌نامه‌های زبان‌های دیگر مثل ru_dict با ۸٫۵MB).</p>
  </div>
  <div class="card"><h4>۲) اجرای کاملاً محلی در هر سه رابط</h4>
    <p>دسکتاپ با <b>sherpa-onnx 1.12.40</b> (فونِم‌ساز espeak-ng داخلی؛ نسخهٔ 2.x حذفش دارد) در <code>label_reader/tts/local_provider.py</code>؛ مرورگر/WebView با <b>onnxruntime-web</b> در موتور بازنویسی‌شدهٔ <code>js/tts.js</code> (فونِم‌سازی → استنتاج → سرگذاشتن WAV 22050Hz → پخش) — در APK هم همین موتور WASM در زمینهٔ امن <code>appassets</code> اجرا می‌شود. سرعت خوانش (−۱۵٪ تا +۲۰٪) با قاعدهٔ پاریتی پایتون/JS به مقیاس طول تبدیل می‌شود.</p>
  </div>
  <div class="card"><h4>۳) حذف کامل مسیرهای آنلاین</h4>
    <p><code>edge_provider.py</code> و <code>gtts_provider.py</code> حذف؛ اندپوینت <code>POST /api/tts</code> از پل حذف؛ چک‌باکس «رضایت ارسال به سرویس ابری» از هر دو رابط حذف؛ کلاینت WebSocket مستقیم Edge و هک UA «Edg/» در MainActivity برداشته شد. <b>هیچ متنی از دستگاه خارج نمی‌شود و TTS بدون اینترنت کار می‌کند.</b></p>
  </div>
  <div class="card"><h4>۴) راستی‌آزمایی کیفیت کوانتیزهٔ int8</h4>
    <p>مدت خوانش int8 نسبت به fp32 برای دو جملهٔ فارسی: نسبت ۱٫۰۰۶ و ۱٫۰۷۶ (بازهٔ پذیرش ۰٫۷۵–۱٫۳) — شواهد: <code>models/tts/piper-fa_IR-amir/quantization-report.json</code> و <code>scripts/evidence_v2120/</code>. آزمون زندهٔ مرورگر: سنتز موفق WAV فارسی ۳٫۷ ثانیه‌ای با موتور WASM و دادهٔ تریم‌شده (<code>scripts/evidence_v2120/browser_tts_fa.wav</code>)؛ آزمون زندهٔ دسکتاپ: WAV ۸٫۳ ثانیه‌ای از پاسخ واقعی. آزمون‌ها: ۱۷۷ pytest + ۷۱ Node + AppTest — همه پاس.</p>
  </div>
'''
rep('  <!-- ۴ -->\n  <div class="chapter-header">\n    <div class="eyebrow">■ بخش ۴</div>\n    <h2>تازه در v2.10.0 — ممیزی مهندسی و اصلاحات ریشه‌ای</h2>',
    new_section + '  <!-- ۵ -->\n  <div class="chapter-header">\n    <div class="eyebrow">■ بخش ۵</div>\n    <h2>تازه در v2.10.0 — ممیزی مهندسی و اصلاحات ریشه‌ای</h2>')

# شماره بخش‌های بعدی
rep('■ بخش ۵</div>\n    <h2>ساختار شکست کار (WBS)', '■ بخش ۶</div>\n    <h2>ساختار شکست کار (WBS)')
rep('■ بخش ۶</div>\n    <h2>ارزیابی — قبل/بعد v2.10.0', '■ بخش ۷</div>\n    <h2>ارزیابی — قبل/بعد v2.10.0')
rep('■ بخش ۷</div>\n    <h2>ایمنی، حریم خصوصی و محدودیت‌ها', '■ بخش ۸</div>\n    <h2>ایمنی، حریم خصوصی و محدودیت‌ها')
rep('■ بخش ۸</div>\n    <h2>نصب، اجرا و ارزیابی مجدد', '■ بخش ۹</div>\n    <h2>نصب، اجرا و ارزیابی مجدد')
rep('■ بخش ۹</div>\n    <h2>تاریخچهٔ نسخه‌ها (خلاصه)', '■ بخش ۱۰</div>\n    <h2>تاریخچهٔ نسخه‌ها (خلاصه)')

# ---------- WBS ----------
rep('<tr><td><b>WBS-10</b></td><td>خوانش صوتی</td><td><code>label_reader/tts/*</code> · <code>response/tts_prep.py</code></td></tr>',
    '<tr><td><b>WBS-10</b></td><td>خوانش صوتی (لوکال)</td><td><code>label_reader/tts/local_provider.py</code> · <code>models/tts/piper-fa_IR-amir/</code> · <code>mobile-app/vendor/tts/</code> · <code>response/tts_prep.py</code> ⇄ <code>js/tts.js</code></td></tr>')
rep('<code>tests/</code> (۱۷۰ pytest) · <code>tests-js/</code> (۷۰ Node + E2E)',
    '<code>tests/</code> (۱۷۷ pytest) · <code>tests-js/</code> (۷۱ Node + E2E)')
rep('│   ├─ tts/                                           [WBS-10] edge-tts / gTTS',
    '│   ├─ tts/                                           [WBS-10] Piper لوکال (local_provider)')
rep('│   └─ ui_helpers.py · ui_theme.py · help_content.py  [WBS-7]  اجزای رابط و راهنما',
    '│   └─ ui_helpers.py · ui_theme.py · help_content.py  [WBS-7]  اجزای رابط و راهنما\n├─ models/tts/piper-fa_IR-amir/                       [WBS-10] مدل Piper (fp32+int8+espeak-ng-data)')
rep('├─ models/tessdata/                                   [WBS-5]  fas + eng (tessdata_best)',
    '├─ models/tessdata/                                   [WBS-5]  fas + eng (tessdata_best)')
rep('│   ├─ sw.js (lbr-mobile-v22) · vendor/ · lang/       [WBS-8]  آفلاین کامل',
    '│   ├─ sw.js (lbr-mobile-v25) · vendor/ · lang/       [WBS-8]  آفلاین کامل (+vendor/tts صوتی)')
rep('├─ android/                                           [WBS-9]  WebView + پل TTS بومی (versionCode 21)',
    '├─ android/                                           [WBS-9]  WebView — صدا با WASM لوکال (versionCode 24)')
rep('├─ tests/ · tests-js/                                 [WBS-11] ۱۷۰ pytest + ۷۰ Node + E2E\n│                                                                (+ test_dedupe_v210.py)',
    '├─ tests/ · tests-js/                                 [WBS-11] ۱۷۷ pytest + ۷۱ Node + E2E\n│                                                                (+ test_tts_llm.py: TTS لوکال)')

# ---------- ایمنی/حریم خصوصی ----------
rep('دستورهای چاپ‌شده فقط داخل گیومه با پیشوند مجاز؛ پخش صوتی فقط با رضایت صریح.</li>',
    'دستورهای چاپ‌شده فقط داخل گیومه با پیشوند مجاز؛ تبدیل گفتار کاملاً محلی است و هیچ متنی به هیچ سرویسی ارسال نمی‌شود (v2.12.0).</li>')
rep('پردازش کاملاً محلی؛ هیچ تصویر/متنی در حالت عادی روی دیسک یا لاگ ذخیره نمی‌شود؛ گزارش مرحله‌ای JSON بدون تصویر و بدون متن کامل برچسب است.</li>',
    'پردازش و تبدیل گفتار کاملاً محلی؛ هیچ تصویر/متنی در حالت عادی روی دیسک یا لاگ ذخیره نمی‌شود؛ گزارش مرحله‌ای JSON بدون تصویر و بدون متن کامل برچسب است.</li>')

# ---------- نصب ----------
rep('PWA با کش <code>lbr-mobile-v22</code> کاملاً آفلاین است؛ APK اندروید versionCode 21 از صفحهٔ Releases.',
    'PWA با کش <code>lbr-mobile-v25</code> کاملاً آفلاین است (شامل موتور صوتی)؛ APK اندروید versionCode 24 از صفحهٔ Releases — صدا بدون اینترنت.')
rep('<li><b>دسکتاپ:</b> <code>pip install -r requirements.txt</code> سپس <code>streamlit run app.py</code>',
    '<li><b>دسکتاپ:</b> <code>pip install -r requirements.txt</code> (شامل <code>sherpa-onnx==1.12.40</code> — نسخهٔ 2.x فونِم‌ساز داخلی ندارد) سپس <code>streamlit run app.py</code>')

# ---------- تاریخچه ----------
rep('''      <tr><td style="width:14%"><b>v2.10.0</b></td>''',
    '''      <tr><td style="width:14%"><b>v2.12.0</b></td><td>مدل صوتی دانلودشده در فایل‌های پروژه: Piper fa_IR-amir-medium باندل‌شده (دسکتاپ sherpa-onnx؛ مرورگر onnxruntime-web + دادهٔ espeak تریم‌شده)؛ حذف کامل سرویس‌های آنلاین و پل صوتی؛ راستی‌آزمایی کوانتیزه + آزمون زندهٔ مرورگر.</td></tr>
      <tr><td style="width:14%"><b>v2.11.0</b></td><td>مدل صوتی مشترک دسکتاپ/موبایل با Edge TTS (پل /api/tts + کلاینت مستقیم) — پس از بازخورد کاربر دربارهٔ وابستگی آنلاین، در v2.12.0 با مدل لوکال جایگزین شد.</td></tr>
      <tr><td style="width:14%"><b>v2.10.1</b></td><td>رفع «لانچر نسخهٔ قدیم را نشان می‌دهد»: پاکسازی SW وابسته به نسخه + رفرش خودکار یک‌باره + تشخیص چیدمان Full-Project در START-HERE.</td></tr>
      <tr><td style="width:14%"><b>v2.10.0</b></td>''')

# ---------- صفحهٔ پایانی ----------
rep('<div class="big">LabelVoice ۲.۱۰.۰</div>', '<div class="big">LabelVoice ۲.۱۲.۰</div>')
rep('مستندات کامل HTML: mobile-app/documentation.html · شواهد ارزیابی: scripts/evidence_v210/',
    'مستندات کامل HTML: mobile-app/documentation.html · شواهد صوتی: scripts/evidence_v2120/')

p.write_text(html, encoding="utf-8")
print("source HTML v2.12.0 built:", p, len(html), "chars")

# -*- coding: utf-8 -*-
"""پچ جامع documentation.html برای v2.12.0 — TTS لوکال Piper"""
import re

P = 'mobile-app/documentation.html'
src = open(P, encoding='utf-8').read()
n0 = len(src)


def rep(old, new, must=True):
    global src
    if old in src:
        src = src.replace(old, new)
        return True
    if must:
        raise AssertionError('NOT FOUND: ' + old[:90])
    return False


# 1) معماری — دو زیرسیستم
rep('<li><b>گفتار:</b> edge-tts (اصلی) + gTTS (جایگزین) فقط با رضایت صریح</li>',
    '<li><b>گفتار:</b> Piper fa_IR-amir-medium — مدل دانلودشده داخل پروژه، اجرای کاملاً لوکال (بدون اینترنت)</li>')
rep('<li><b>گفتار (v2.11.0):</b> Microsoft Edge TTS — همان مدل دسکتاپ؛ کلاینت <code>js/tts.js</code> + پل <code>POST /api/tts</code> (بدون TTS خود گوشی)</li>',
    '<li><b>گفتار (v2.12.0):</b> Piper فارسی — وزن‌های int8 در <code>vendor/tts/</code>؛ استنتاج با onnxruntime-web (WASM) روی خود دستگاه (بدون TTS گوشی و بدون سرویس ابری)</li>')

# 2) جدول ملزومات — دو ردیف
rep('یک مدل مشترک در همهٔ رابط‌ها: صداهای نورال فارسی Microsoft Edge (fa-IR-FaridNeural/DilaraNeural) با رضایت صریح؛ در موبایل از TTS خود گوشی استفاده نمی‌شود (v2.11.0)</td>',
    'یک مدل مشترک در همهٔ رابط‌ها: Piper VITS «fa_IR-amir-medium» — وزن‌ها باندل‌شده در پروژه و اجرای کاملاً لوکال؛ نه TTS گوشی و نه سرویس ابری (v2.12.0)</td>')
rep('<code>label_reader/response/builder.py</code> + <code>tts/*</code> + <code>bridge.py (/api/tts)</code> ⇄ <code>mobile-app/js/responder.js</code> + <code>js/tts.js</code>',
    '<code>label_reader/response/builder.py</code> + <code>tts/local_provider.py</code> ⇄ <code>mobile-app/js/responder.js</code> + <code>js/tts.js</code> + <code>vendor/tts/*</code>')
rep('خوانش صوتی همان پاسخ تأییدشده با یک مدل مشترک (Edge TTS فارسی) در همهٔ رابط‌ها؛ همیشه با رضایت صریح (v2.11.0)</td><td style="padding:.55rem .6rem"><code>label_reader/tts/*</code> + <code>app.py</code> (Streamlit RTL)</td><td style="padding:.55rem .6rem"><code>js/tts.js</code> + پل <code>POST /api/tts</code> (bridge.py) در <code>mobile-app/index.html</code>',
    'خوانش صوتی همان پاسخ تأییدشده با یک مدل مشترک لوکال (Piper فارسی) در همهٔ رابط‌ها؛ بدون اینترنت (v2.12.0)</td><td style="padding:.55rem .6rem"><code>label_reader/tts/local_provider.py</code> + <code>models/tts/</code> + <code>app.py</code> (Streamlit RTL)</td><td style="padding:.55rem .6rem"><code>js/tts.js</code> + <code>vendor/tts/*</code> در <code>mobile-app/index.html</code>')

# 3) کارت مرحله ۵
rep('<h4>TTS + رابط کاربری — خواندن اطلاعات و نمایش متن استخراج‌شده <span class="chip">Edge TTS فارسی — یک مدل مشترک (v2.11.0)</span></h4>',
    '<h4>TTS + رابط کاربری — خواندن اطلاعات و نمایش متن استخراج‌شده <span class="chip">Piper فارسی — مدل لوکال مشترک (v2.12.0)</span></h4>')
rep('<b>فایل دسکتاپ:</b> <code>label_reader/tts/*</code> + <code>app.py</code> (Streamlit) &nbsp;|&nbsp; <b>موبایل:</b> <code>mobile-app/js/tts.js</code> (پل <code>POST /api/tts</code> به bridge.py یا کلاینت مستقیم Edge) — بدون speechSynthesis/TTS بومی گوشی',
    '<b>فایل دسکتاپ:</b> <code>label_reader/tts/local_provider.py</code> (sherpa-onnx) + <code>models/tts/piper-fa_IR-amir/</code> + <code>app.py</code> (Streamlit) &nbsp;|&nbsp; <b>موبایل:</b> <code>mobile-app/js/tts.js</code> (Piper روی onnxruntime-web) + <code>vendor/tts/</code> — بدون speechSynthesis/TTS بومی گوشی و بدون هر سرویس ابری')

# 4) مرحله ۵ جدول اعلام
rep('موتور صوتی (Edge TTS — همان مدل دسکتاپ)، آماده‌سازی تلفظ، وضعیت صوت (همیشه با رضایت)</td><td style="padding:.55rem .6rem"><code>label_reader/tts/*</code> + <code>app.py</code></td><td style="padding:.55rem .6rem"><code>js/tts.js</code> (پل /api/tts یا کلاینت مستقیم Edge)</td>',
    'موتور صوتی (Piper fa_IR-amir-medium — لوکال)، آماده‌سازی تلفظ، وضعیت صوت</td><td style="padding:.55rem .6rem"><code>label_reader/tts/local_provider.py</code> + <code>app.py</code></td><td style="padding:.55rem .6rem"><code>js/tts.js</code> + <code>vendor/tts/*</code></td>')

# 5) WBS
rep('<tr><td><b>WBS-10</b></td><td>خوانش صوتی فارسی (TTS) — یک مدل مشترک در همهٔ رابط‌ها (v2.11.0)</td><td>edge-tts (عصبی: Farid/Dilara) با جایگزین gTTS؛ در موبایل همان مدل از پل <code>/api/tts</code> یا کلاینت مستقیم <code>js/tts.js</code> — بدون TTS گوشی</td><td><code>label_reader/tts/*</code> · <code>response/tts_prep.py</code> · <code>bridge.py</code> · <code>mobile-app/js/tts.js</code></td></tr>',
    '<tr><td><b>WBS-10</b></td><td>خوانش صوتی فارسی (TTS) — مدل لوکال مشترک در همهٔ رابط‌ها (v2.12.0)</td><td>Piper VITS «fa_IR-amir-medium» باندل‌شده در پروژه؛ دسکتاپ: sherpa-onnx؛ وب/موبایل/APK: onnxruntime-web + piper-phonemize (WASM) — بدون اینترنت، بدون سرویس ابری، بدون TTS گوشی</td><td><code>label_reader/tts/local_provider.py</code> · <code>models/tts/piper-fa_IR-amir/</code> · <code>response/tts_prep.py</code> · <code>mobile-app/js/tts.js</code> · <code>mobile-app/vendor/tts/</code></td></tr>')
rep('│   ├─ tts/                                           [WBS-10] edge-tts / gTTS (مدل مشترک همهٔ رابط‌ها)',
    '│   ├─ tts/                                           [WBS-10] Piper لوکال (local_provider)')
rep('│   ├─ bridge.py                                      [WBS-10] پل OCR + POST /api/tts (v2.11.0)',
    '│   ├─ bridge.py                                      [WBS-10] پل OCR (GET /ping · POST /ocr)')
rep('<tr><td class="p"><code>tts/edge_provider.py</code> · <code>gtts_provider.py</code></td><td class="d">edge-tts (صداهای عصبی فارسی) و gTTS — با پیام وضعیت فارسی</td></tr>',
    '<tr><td class="p"><code>tts/local_provider.py</code></td><td class="d">ارائه‌دهندهٔ Piper لوکال (sherpa-onnx) — مدل داخل models/tts؛ پیام وضعیت فارسی</td></tr>')
rep('<tr><td class="p"><code>bridge.py</code> · <code>mobile-app/js/tts.js</code></td><td class="d">پل محلی (GET /ping · POST /ocr · POST /api/tts با رضایت) و کلاینت مستقیم Edge در مرورگر — صدای موبایل = همان مدل دسکتاپ (v2.11.0)</td></tr>',
    '<tr><td class="p"><code>bridge.py</code> · <code>mobile-app/js/tts.js</code></td><td class="d">پل محلی (GET /ping · POST /ocr) و موتور صوتی لوکال مرورگر (Piper روی onnxruntime-web) — صدا روی خود دستگاه در همهٔ رابط‌ها (v2.12.0)</td></tr>')

# 6) FAQ موبایل
rep('خوانش صوتی از نسخهٔ ۲.۱۱.۰ با <b>همان مدل دسکتاپ</b> (صداهای نورال فارسی Microsoft Edge) انجام می‌شود — از مسیر «پل دسکتاپ» (<code>POST /api/tts</code> با همان کد پایتون) یا کلاینت مستقیم <code>js/tts.js</code> (مرورگر Edge/APK) و به‌طور عمدی از TTS خود گوشی استفاده نمی‌شود؛',
    'خوانش صوتی از نسخهٔ ۲.۱۲.۰ با <b>مدل Piper فارسی (fa_IR-amir-medium)</b> انجام می‌شود که وزن‌هایش داخل فایل‌های برنامه باندل شده و با <b>onnxruntime-web (WASM)</b> روی همین دستگاه اجرا می‌شود — نه سرویس ابری و نه TTS خود گوشی؛')

# 7) کارت‌های فناوری
rep('<div class="techcard reveal" style="--tc:#0f9d58"><div class="glyph">edge</div><h4>edge-tts</h4><div class="role">گفتار عصبی فارسی (Farid/Dilara) — مدل مشترک دسکتاپ و موبایل (v2.11.0)</div><span class="where">tts/edge_provider.py · js/tts.js</span></div>',
    '<div class="techcard reveal" style="--tc:#0f9d58"><div class="glyph">Piper</div><h4>Piper VITS — fa_IR-amir-medium</h4><div class="role">مدل صوتی فارسی دانلودشده داخل پروژه (int8؛ منبع rhasspy/piper-voices — MIT) — اجرای کاملاً لوکال (v2.12.0)</div><span class="where">models/tts/piper-fa_IR-amir · vendor/tts</span></div>')
rep('<div class="techcard reveal" style="--tc:#4285f4"><div class="glyph">gT</div><h4>gTTS</h4><div class="role">جایگزین گفتار در نبود edge-tts</div><span class="where">tts/gtts_provider.py</span></div>',
    '<div class="techcard reveal" style="--tc:#4285f4"><div class="glyph">espeak</div><h4>espeak-ng (piper-phonemize WASM)</h4><div class="role">فونِم‌سازی فارسی/انگلیسی برای Piper — دادهٔ تریم‌شدهٔ fa+en (۱.۳MB از ۱۸MB)</div><span class="where">vendor/tts/piper_phonemize.*</span></div>')
rep('<div class="techcard reveal" style="--tc:#38bdf8"><div class="glyph">TTS</div><h4>کلاینت Edge TTS (js/tts.js)</h4><div class="role">همان مدل صوتی دسکتاپ در وب/موبایل — پل /api/tts یا مسیر مستقیم Edge (بدون TTS گوشی)</div><span class="where">js/tts.js · bridge.py</span></div>',
    '<div class="techcard reveal" style="--tc:#38bdf8"><div class="glyph">ORT</div><h4>onnxruntime-web + sherpa-onnx</h4><div class="role">اجرای استنتاج VITS روی خود دستگاه: مرورگر با onnxruntime-web (WASM/SIMD)، دسکتاپ با sherpa-onnx 1.12 — همان مدل، خروجی یکسان</div><span class="where">vendor/tts/ort* · tts/local_provider.py</span></div>')

# 8) جدول فناوری (بخش فناوری‌ها)
rep('<tr><td>۵. خوانش صوتی (TTS)</td><td><b>edge-tts</b> — صداهای fa-IR-FaridNeural / fa-IR-DilaraNeural — <b>همین مدل در وب/موبایل/APK هم (v2.11.0)</b></td><td>خواندن همان پاسخ تأییدشده؛ جایگزین خودکار: gTTS (گوگل)</td><td>فقط متن پاسخ، با رضایت صریح</td></tr>',
    '<tr><td>۵. خوانش صوتی (TTS)</td><td><b>Piper VITS — fa_IR-amir-medium</b> (باندل‌شده؛ دسکتاپ fp32/int8 با sherpa-onnx، وب/موبایل int8 با onnxruntime-web — v2.12.0)</td><td>خواندن همان پاسخ تأییدشده؛ خروجی WAV 22050Hz؛ سرعت خوانش پاریتی</td><td>کاملاً لوکال — هیچ متنی از دستگاه خارج نمی‌شود</td></tr>')
rep('<td>کاملاً آفلاین (تک‌فایل/OCR) + پل محلی اختیاری؛ TTS نیازمند اینترنت یا پل</td></tr>',
    '<td>کاملاً آفلاین (تک‌فایل/OCR/TTS) + پل محلی اختیاری فقط برای موتورهای سنگین OCR</td></tr>')
rep('خوانش صوتی (v2.11.0) با همان مدل دسکتاپ: پل <code>POST /api/tts</code> یا کلاینت مستقیم <code>js/tts.js</code> (مرورگر Edge/APK) — بدون TTS خود گوشی</td>',
    'خوانش صوتی (v2.12.0) با مدل لوکال Piper روی onnxruntime-web — بدون TTS خود گوشی و بدون اینترنت</td>')

open(P, 'w', encoding='utf-8').write(src)
print('documentation.html patched; delta bytes:', len(src) - n0)

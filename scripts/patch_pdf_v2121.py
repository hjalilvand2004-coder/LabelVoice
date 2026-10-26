# -*- coding: utf-8 -*-
"""پچ‌های v2.12.1 روی سند منبع PDF (پس از build_pdf_source_v2121.py)"""
from pathlib import Path

p = Path("/home/z/my-project/download/LabelVoice-Documentation-v2.12.1/LabelVoice-Documentation.html")
html = p.read_text(encoding="utf-8")


def rep(old, new):
    global html
    assert old in html, "NOT FOUND: " + old[:80]
    html = html.replace(old, new)


# عنوان و جلد
rep("<title>LabelVoice — مستندات فنی نسخهٔ ۲.۱۲.۰</title>",
    "<title>LabelVoice — مستندات فنی نسخهٔ ۲.۱۲.۱</title>")
rep('<div class="ver">نسخهٔ ۲.۱۲.۰ — مدل صوتی Piper فارسی باندل‌شده در پروژه · کاملاً لوکال و بدون اینترنت · جایگزینی کامل سرویس‌های آنلاین</div>',
    '<div class="ver">نسخهٔ ۲.۱۲.۱ — مدل صوتی Piper فارسی باندل‌شده در پروژه · کاملاً لوکال و بدون اینترنت · هم‌خوانی همهٔ نمایشگرهای نسخه با ریلیز</div>')

# بخش ۴ — پاراگراف پایانی: افزودن اشارهٔ v2.12.1
rep('آزمون‌ها: ۱۷۷ pytest + ۷۱ Node + AppTest — همه پاس.</p>',
    'آزمون‌ها: ۱۷۷ pytest + ۷۱ Node + AppTest — همه پاس. در v2.12.۱ همهٔ چیپ‌های نمایش نسخه (START-HERE، سایدبار/فوتر وب، مودال «درباره»، سند فنی و VERSION.txt ریشه که bat نشان می‌دهد) با ریلیز هم‌تراز شدند.</p>')

# نصب — SW و versionCode
rep('PWA با کش <code>lbr-mobile-v25</code> کاملاً آفلاین است (شامل موتور صوتی)؛ APK اندروید versionCode 24 از صفحهٔ Releases — صدا بدون اینترنت.',
    'PWA با کش <code>lbr-mobile-v26</code> کاملاً آفلاین است (شامل موتور صوتی)؛ APK اندروید versionCode 25 (2.12.1) از صفحهٔ Releases — صدا بدون اینترنت.')

# درخت WBS
rep('│   ├─ sw.js (lbr-mobile-v25) · vendor/ · lang/       [WBS-8]  آفلاین کامل (+vendor/tts صوتی)',
    '│   ├─ sw.js (lbr-mobile-v26) · vendor/ · lang/       [WBS-8]  آفلاین کامل (+vendor/tts صوتی)')
rep('├─ android/                                           [WBS-9]  WebView — صدا با WASM لوکال (versionCode 24)',
    '├─ android/                                           [WBS-9]  WebView — صدا با WASM لوکال (versionCode 25)')

# تاریخچه — ردیف v2.12.1
rep('      <tr><td style="width:14%"><b>v2.12.0</b></td>',
    '''      <tr><td style="width:14%"><b>v2.12.1</b></td><td>هم‌خوانی همهٔ نمایشگرهای نسخه با ریلیز (بازخورد کاربر: bat و START-HERE نسخهٔ قدیم را نشان می‌دادند) — چیپ‌های جامانده ۲.۱۱.۰ در START-HERE، سایدبار/فوتر وب، مودال «درباره»، سند فنی و VERSION.txt ریشه به ۲.۱۲.۱ رسید؛ کش SW → lbr-mobile-v26؛ APK versionCode 25؛ بازساخت تک‌فایل و ZIPها.</td></tr>
      <tr><td style="width:14%"><b>v2.12.0</b></td>''')

# صفحهٔ پایانی
rep('<div class="big">LabelVoice ۲.۱۲.۰</div>', '<div class="big">LabelVoice ۲.۱۲.۱</div>')

p.write_text(html, encoding="utf-8")
print("patched v2.12.1:", p, len(html), "chars")

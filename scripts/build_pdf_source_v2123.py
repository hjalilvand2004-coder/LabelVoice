# -*- coding: utf-8 -*-
"""ساخت سند منبع PDF مستندات v2.12.3 از قالب v2.12.2

v2.12.3 = رفع خطای پخش صوتی در بستهٔ پرتیبل:
  (۱) MIME درست ماژول .mjs در server-windows.ps1 (هر دو نسخهٔ پرتیبل و Full-Project)
  (۲) پیام‌های خطای شفاف فارسی در js/tts.js (تشخیص file:// + پوشش خطاهای fetch/ort)
  (۳) هشدار file:// در START-HERE + اصلاح متن لانچر + آزمون رگرسیون MIME
"""
import shutil
from pathlib import Path

SRC = Path("/home/z/my-project/download/LabelVoice-Documentation-v2.12.2")
DST = Path("/home/z/my-project/download/LabelVoice-Documentation-v2.12.3")

if DST.exists():
    shutil.rmtree(DST)
shutil.copytree(SRC, DST)
(DST / "LabelVoice-Documentation-v2.12.2.pdf").unlink(missing_ok=True)

p = DST / "LabelVoice-Documentation.html"
html = p.read_text(encoding="utf-8")


def rep(old, new, count=1):
    global html
    assert old in html, "NOT FOUND: " + old[:90]
    html = html.replace(old, new, count)


# ---------- عنوان و جلد ----------
rep("<title>LabelVoice — مستندات فنی نسخهٔ ۲.۱۲.۲</title>",
    "<title>LabelVoice — مستندات فنی نسخهٔ ۲.۱۲.۳</title>")
rep('<div class="ver">نسخهٔ ۲.۱۲.۲ — جدول «نوع، نام و مسیر فایل هر مدل» · تفکیک باندل‌شده در پروژه از نصب جداگانه · مستندات با لحن بررسی و تحلیل</div>',
    '<div class="ver">نسخهٔ ۲.۱۲.۳ — رفع خطای پخش صوتی در بستهٔ پرتیبل: MIME درست ماژول mjs در سرور محلی ویندوز · پیام‌های خطای شفاف فارسی (تشخیص file://) · هشدار صفحهٔ شروع</div>')
rep('<div class="big">LabelVoice ۲.۱۲.۲</div>', '<div class="big">LabelVoice ۲.۱۲.۳</div>')

# ---------- نسخه‌های اجرا ----------
html = html.replace("lbr-mobile-v27", "lbr-mobile-v28")
rep("(versionCode 26)", "(versionCode 27)")
rep("APK اندروید versionCode 26 (2.12.2) از صفحهٔ Releases",
    "APK اندروید versionCode 27 (2.12.3) از صفحهٔ Releases")

# ---------- تاریخچه: ردیف v2.12.3 ----------
v2123_row = ('<tr><td style="width:14%"><b>v2.12.3</b></td><td>'
             'رفع خطای پخش صوتی در بستهٔ پرتیبل: بر اساس بررسی و تحلیل صورت گرفته روی گزارش '
             '«تولید صدا ناموفق بود»، دو علت مستقل شناسایی و رفع شد — '
             '(۱) جدول MIME سرور محلی ویندوز فایل‌های <code>.mjs</code> را با '
             '<code>application/octet-stream</code> می‌فرستاد و مرورگرها import ماژول ES با MIME '
             'غیرجاوااسکریپتی را رد می‌کردند (راه‌اندازی onnxruntime-web در همان مرحله شکست می‌خورد)؛ '
             'اکنون <code>.mjs</code> با <code>text/javascript</code> سرو می‌شود (+ تعریف صریح '
             '.onnx/.data/.txt) در هر دو نسخهٔ سرور و آزمون رگرسیون MIME اضافه شد. '
             '(۲) بازکردن مستقیم HTML از Explorer (حالت file://) بارگیری مدل‌ها را مسدود و خطا را '
             'بدون پیام فارسی نشان می‌داد؛ اکنون موتور صوتی file:// را تشخیص می‌دهد و راهنمای دقیق '
             'فارسی می‌دهد، همهٔ خطاهای fetch/راه‌اندازی موتور با پیام فارسیِ قابل‌اقدام پوشش شده‌اند، '
             'START-HERE در حالت file:// هشدار می‌دهد و متن گمراه‌کنندهٔ لانچر اصلاح شد. '
             'شواهد E2E: بازتولید شکست با سرور MIME نادرست + سنتز موفق با سرور اصلاح‌شده '
             '(scripts/evidence_v2123) و سنتز آفلاین تک‌فایل با file:// (WAV ۱۰۸KB). '
             'کش SW → lbr-mobile-v28؛ APK versionCode 27 (2.12.3)؛ تک‌فایل بازساخت (۶۰MB) + '
             'رفع خطای نحوی prelude کارگر OCR تک‌فایل (__LBR_U[m[1]]).</td></tr>\n'
             '      <tr><td style="width:14%"><b>v2.12.2</b></td><td>مستندات مدل‌ها:')
rep('<tr><td style="width:14%"><b>v2.12.2</b></td><td>مستندات مدل‌ها:', v2123_row)

p.write_text(html, encoding="utf-8")
print("source HTML v2.12.3 built:", p, len(html), "chars")
print("v28 refs:", html.count("lbr-mobile-v28"), "| vc27 refs:", html.count("versionCode 27"))

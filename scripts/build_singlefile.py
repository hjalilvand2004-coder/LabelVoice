#!/usr/bin/env python3
"""ساخت نسخه تک‌فایل برچسب‌خوان موبایل (label-reader-singlefile.html)

همه فایل‌های محلی js/css به‌صورت inline در یک HTML قرار می‌گیرند؛
موتور OCR (tesseract.min.js) مانند قبل از CDN بارگیری می‌شود (حالت file://
در js/ocr.js همین مسیر را انتخاب می‌کند).

کاربرد: python3 scripts/build_singlefile.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'mobile-app'
OUT = ROOT / 'label-reader-singlefile.html'

html = (ROOT / 'index.html').read_text(encoding='utf-8')

# حذف لینک manifest و SW ثبت‌شونده در تک‌فایل بی‌معناست؛ فقط استایل‌شیت را inline کن
html = html.replace('<link rel="manifest" href="manifest.webmanifest">\n', '')
html = re.sub(
    r'<link rel="stylesheet" href="css/style.css">',
    '<style>\n' + (ROOT / 'css/style.css').read_text(encoding='utf-8') + '\n</style>',
    html)

def inline_script(m: 're.Match') -> str:
    src = m.group(1)
    if src.startswith('http'):
        return m.group(0)  # CDN دست‌نخورده
    path = ROOT / src
    if not path.exists():
        raise SystemExit(f'فایل یافت نشد: {path}')
    code = path.read_text(encoding='utf-8')
    return '<script>\n' + code + '\n</script>'

html = re.sub(r'<script src="([^"]+)"></script>', inline_script, html)

# جلوگیری از ثبت Service Worker در نسخه تک‌فایل (pathهای محلی وجود ندارند)
html = html.replace(
    "navigator.serviceWorker.register('./sw.js')",
    "Promise.reject(new Error('singlefile: no sw'))"
)

OUT.write_text(html, encoding='utf-8')
print(f'OK: {OUT} ({OUT.stat().st_size // 1024} KB)')

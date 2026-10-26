#!/usr/bin/env python3
"""ساخت نسخه تک‌فایل برچسب‌خوان (label-reader-singlefile.html) — v2.12.0

همه فایل‌های محلی js/css به‌صورت inline در یک HTML قرار می‌گیرند و برخلاف
نسخه‌های قبل، موتور OCR (worker + هسته WASM + داده زبان فارسی/انگلیسی)
و نیز **موتور صوتی لوکال Piper** (مدل int8 + onnxruntime-web + فونِم‌ساز)
داخل فایل تزریق می‌شود؛ نتیجه: فایل تک‌فایلی حتی بدون اینترنت و بدون
پایتون روی هر سیستمی کار می‌کند — هم خوانش متن هم خوانش صوتی.

کاربرد: python3 scripts/build_singlefile.py
"""
import base64
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'mobile-app'
OUT = ROOT / 'label-reader-singlefile.html'

html = (ROOT / 'index.html').read_text(encoding='utf-8')

# حذف لینک manifest و SW ثبت‌شونده در تک‌فایل بی‌معناست؛ فقط استایل‌شیت را inline کن
html = html.replace('<link rel="manifest" href="manifest.webmanifest">\n', '')
html = re.sub(
    r'<link rel="stylesheet" href="css/style\.css(?:\?v=[^"]*)?">',
    '<style>\n' + (ROOT / 'css/style.css').read_text(encoding='utf-8') + '\n</style>',
    html)

# ---- v1.8.2: تزریق موتور OCR کاملاً آفلاین ----
# راهبرد (پس از ماتریس آزمون Worker روی file://):
#  - importScripts(blob:) در کارگرِ مبدا-ناشناس مسدود است؛ importScripts(data:) مجاز است
#  - پس همهٔ منابع داخل کارگر با data: URL تزریق می‌شوند
#  - خودِ پرلود Blob است و با workerBlobURL:false مستقیم new Worker می‌شود
def b64(data: bytes) -> str:
    return base64.b64encode(data).decode('ascii')

worker_b64 = b64((ROOT / 'vendor/tesseract/worker.min.js').read_bytes())
core_b64 = b64((ROOT / 'vendor/core/tesseract-core-simd-lstm.wasm.js').read_bytes())
wasm_b64 = b64((ROOT / 'vendor/core/tesseract-core-simd-lstm.wasm').read_bytes())
fas_b64 = b64((ROOT / 'lang/best/fas.traineddata.gz').read_bytes())
eng_b64 = b64((ROOT / 'lang/best/eng.traineddata.gz').read_bytes())

prelude = (
    'var __LBR_U={'
    'coreJs:"data:text/javascript;base64,' + core_b64 + '",'
    'wasm:"data:application/wasm;base64,' + wasm_b64 + '",'
    'fas:"data:application/octet-stream;base64,' + fas_b64 + '",'
    'eng:"data:application/octet-stream;base64,' + eng_b64 + '"};'
    'var __oif=self.importScripts;'
    'self.importScripts=function(){var a=[].slice.call(arguments).map(function(u){'
    'u=String(u);return /tesseract-core-[a-z-]+\\.wasm\\.js(\\?|$)/.test(u)?__LBR_U.coreJs:u});'
    'return __oif.apply(self,a)};'
    'var __of=self.fetch;'
    'self.fetch=function(u,o){u=String(u);'
    'if(/tesseract-core-[a-z-]+\\.wasm(\\?|$)/.test(u))return __of(__LBR_U.wasm,o);'
    'var m=/\\/([a-z]{3})\\.traineddata\\.gz(\\?|$)/.exec(u);'
    'if(m&&__LBR_U[m[1]])return __of(__LBR_U[m[1]],o);'
    'return __of.apply(self,[u,o])};'
    'importScripts("data:text/javascript;base64,' + worker_b64 + '");'
)

offline_js = '<script>window.__LBR_OFFLINE__ = ' + json.dumps({
    'v': '2.12.0',
    'prelude': prelude,
}) + ';</script>'
tag = re.search(r'<script src="js/offline-engine\.js(?:\?v=[^"]*)?"></script>', html)
if not tag:
    raise SystemExit('تگ js/offline-engine.js در index.html یافت نشد')
html = html[:tag.start()] + offline_js + html[tag.end():]

# ---- v2.12.0: تعبیهٔ موتور صوتی لوکال (Piper) در تک‌فایل ----
# js/tts.js مسیرها را از window.__LBR_TTS_ASSETS__ حل می‌کند (rurl)؛
# در تک‌فایل همهٔ دارایی‌ها data: URL هستند — بدون هیچ درخواست شبکه‌ای.
tts_assets = {
    './vendor/tts/ort.wasm.min.js': 'data:text/javascript;base64,' + b64(
        (ROOT / 'vendor/tts/ort.wasm.min.js').read_bytes()),
    './vendor/tts/ort-wasm-simd-threaded.mjs': 'data:text/javascript;base64,' + b64(
        (ROOT / 'vendor/tts/ort-wasm-simd-threaded.mjs').read_bytes()),
    './vendor/tts/ort-wasm-simd-threaded.wasm': 'data:application/wasm;base64,' + b64(
        (ROOT / 'vendor/tts/ort-wasm-simd-threaded.wasm').read_bytes()),
    './vendor/tts/piper-phonemize.js': 'data:text/javascript;base64,' + b64(
        (ROOT / 'vendor/tts/piper-phonemize.js').read_bytes()),
    './vendor/tts/piper_phonemize.wasm': 'data:application/wasm;base64,' + b64(
        (ROOT / 'vendor/tts/piper_phonemize.wasm').read_bytes()),
    './vendor/tts/piper_phonemize.data': 'data:application/octet-stream;base64,' + b64(
        (ROOT / 'vendor/tts/piper_phonemize.data').read_bytes()),
    './vendor/tts/fa_IR-amir-medium.int8.onnx': 'data:application/octet-stream;base64,' + b64(
        (ROOT / 'vendor/tts/fa_IR-amir-medium.int8.onnx').read_bytes()),
    './vendor/tts/fa_IR-amir-medium.onnx.json': 'data:application/json;base64,' + b64(
        (ROOT / 'vendor/tts/fa_IR-amir-medium.onnx.json').read_bytes()),
}
tts_js = ('<script>window.__LBR_TTS_ASSETS__ = ' +
          json.dumps(tts_assets) + ';</script>')
html = html.replace('<script src="js/tts.js?v=2.12.0"></script>',
                    tts_js + '<script src="js/tts.js?v=2.12.0"></script>')

def inline_script(m: 're.Match') -> str:
    src = m.group(1)
    if src.startswith('http'):
        return m.group(0)  # CDN دست‌نخورده
    path = ROOT / src.split('?')[0]  # پشتیبانی از کش-باست (?v=…)
    if not path.exists():
        raise SystemExit(f'فایل یافت نشد: {path}')
    code = path.read_text(encoding='utf-8')
    return '<script>\n' + code + '\n</script>'

html = re.sub(r'<script src="([^"]+)"></script>', inline_script, html)

# نظارت: دارایی‌های صوتی تعبیه شده باشند
if '__LBR_TTS_ASSETS__' not in html or 'fa_IR-amir-medium.int8.onnx' not in html:
    raise SystemExit('تعبیهٔ دارایی‌های صوتی در تک‌فایل انجام نشد')

# جلوگیری از ثبت Service Worker در نسخه تک‌فایل (pathهای محلی وجود ندارند)
html = html.replace(
    "navigator.serviceWorker.register('./sw.js')",
    "Promise.reject(new Error('singlefile: no sw'))"
)

# v2.5.0: هدر پالتی (بدون تصویر) — نیازی به تعبیهٔ assets/header-bg-wide.jpg نیست
if "assets/header-bg-wide.jpg" in html or "header-bg-wide.jpg" in html:
    raise SystemExit('ارجاع به تصویر هدر قدیمی در index.html باقی مانده — باید حذف شود')

OUT.write_text(html, encoding='utf-8')
print(f'OK: {OUT} ({OUT.stat().st_size // (1024*1024)} MB / {OUT.stat().st_size // 1024} KB)')

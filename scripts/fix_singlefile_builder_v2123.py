#!/usr/bin/env python3
"""بررسی و اعمال قطعی ۴ اصلاح build_singlefile.py (v2.12.3) — پایتون مرجع حقیقت"""
import io
import re
import sys

P = '/home/z/my-project/labelvoice-clone/scripts/build_singlefile.py'
s = open(P, encoding='utf-8').read()
orig = s
report = []

# ---- ۱) اصلاح خرابی __LBR_U[1]] → __LBR_U[m[1]] ----
if '__LBR_U[1]]' in s:
    s = s.replace('__LBR_U[1]]', '__LBR_U[m[1]]')
    report.append('fix1-corruption: APPLIED (was corrupted)')
elif '__LBR_U[m[1]]' in s:
    report.append('fix1-corruption: already OK')
else:
    report.append('fix1-corruption: !!! NEITHER FOUND — manual check needed')

# ---- ۲) نسخهٔ __LBR_OFFLINE__ → 2.12.3 ----
if "'v': '2.12.2'" in s:
    s = s.replace("'v': '2.12.2'", "'v': '2.12.3'")
    report.append('fix2-offline-v: APPLIED 2.12.2→2.12.3')
elif "'v': '2.12.3'" in s:
    report.append('fix2-offline-v: already OK')
else:
    report.append('fix2-offline-v: !!! version json not found')

# ---- ۳) جایگزینی سخت‌کدشدهٔ تگ tts.js → regex نسخه‌مستقل ----
hard = "html = html.replace('<script src=\"js/tts.js?v=2.12.2\"></script>',\n                    tts_js + '<script src=\"js/tts.js?v=2.12.2\"></script>')"
regexv = ("html = re.sub(r'<script src=\"js/tts\\.js(?:\\?v=[^\"]*)?\"></script>',\n"
          "              tts_js + '<script src=\"js/tts.js\"></script>', html)")
if "js/tts.js?v=2.12.2" in s:
    # هر شکلی از replace سخت‌کدشده را با نسخهٔ regex عوض کن
    s = re.sub(
        r"html = html\.replace\('<script src=\"js/tts\.js\?v=[^\"]*\"></script>',\s*\n\s*tts_js \+ '<script src=\"js/tts\.js\?v=[^\"]*\"></script>'\)",
        regexv.replace('\\', '\\\\'), s, count=1)
    report.append('fix3-tts-tag: regex APPLIED')
elif "re.sub(r'<script src=\"js/tts" in s:
    report.append('fix3-tts-tag: already OK (regex)')
else:
    report.append('fix3-tts-tag: !!! tts tag handling not found')

# ---- ۴) بررسی نهایی سخت‌گیرانهٔ تعبیهٔ مدل (data: URL واقعی) ----
old_check = ("if '__LBR_TTS_ASSETS__' not in html or 'fa_IR-amir-medium.int8.onnx' not in html:\n"
             "    raise SystemExit('تعبیهٔ دارایی‌های صوتی در تک‌فایل انجام نشد')")
new_check = ("MODEL_DATA_MARK = '\\\"./vendor/tts/fa_IR-amir-medium.int8.onnx\\\": \\\"data:application/octet-stream;base64,'\n"
             "if '__LBR_TTS_ASSETS__' not in html or MODEL_DATA_MARK not in html:\n"
             "    raise SystemExit('تعبیهٔ دارایی‌های صوتی در تک‌فایل انجام نشد (data: URL مدل یافت نشد)')")
if 'MODEL_DATA_MARK' in s:
    report.append('fix4-hard-check: already OK')
elif old_check in s:
    s = s.replace(old_check, new_check)
    report.append('fix4-hard-check: APPLIED')
else:
    report.append('fix4-hard-check: !!! old check not found verbatim')

if s != orig:
    open(P, 'w', encoding='utf-8').write(s)
    report.append('FILE WRITTEN')
else:
    report.append('no changes needed')

# راستی‌آزمایی نهایی با خوانش تازه
v = open(P, encoding='utf-8').read()
report.append('verify: m[1]×' + str(v.count('__LBR_U[m[1]]')))
report.append('verify: bad-token×' + str(v.count('__LBR_U[1]]')))
report.append('verify: offline-v-2.12.3=' + str("'v': '2.12.3'" in v))
report.append('verify: tts-regex=' + str("re.sub(r'<script src=\"js/tts" in v))
report.append('verify: hard-check=' + str('MODEL_DATA_MARK' in v))
print('\n'.join(report))
sys.exit(0)

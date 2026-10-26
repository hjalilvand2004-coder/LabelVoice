/* آزمون رگرسیون v2.12.3 — جدول MIME سرورهای محلی ویندوز (ps1)
 *
 * باگ: سرور داخلی server-windows.ps1 فایل .mjs را با application/octet-stream
 * می‌فرستاد؛ مرورگرها import() ماژول ES با MIME غیرجاوااسکریپتی را رد می‌کنند
 * و onnxruntime-web هنگام ساخت نشست، ort-wasm-simd-threaded.mjs را import
 * می‌کند → راه‌اندازی موتور صوتی لوکال بی‌صدا شکست می‌خورد.
 *
 * این آزمون تضمین می‌کند هر دو نسخهٔ سرور (پرتیبل و mobile-app):
 *   - .mjs  → text/javascript
 *   - .onnx → application/octet-stream
 *   - .data → application/octet-stream
 *   - .wasm → application/wasm
 * را تعریف کرده باشند.
 */
'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const PS1_FILES = [
  path.join(ROOT, 'portable', 'server-windows.ps1'),
  path.join(ROOT, 'mobile-app', 'server-windows.ps1'),
];

const REQUIRED = [
  ["'.mjs'", 'text/javascript'],
  ["'.onnx'", 'application/octet-stream'],
  ["'.data'", 'application/octet-stream'],
  ["'.wasm'", 'application/wasm'],
];

let failures = 0;
for (const file of PS1_FILES) {
  const src = fs.readFileSync(file, 'utf8');
  for (const [ext, mime] of REQUIRED) {
    // همان سطر تعریف باید هر دو مقدار را داشته باشد
    const line = src.split('\n').find((l) => l.includes(ext) && l.includes('='));
    if (!line || !line.includes(mime)) {
      console.error(`FAIL ${path.relative(ROOT, file)}: ${ext} باید ${mime} باشد — یافت نشد`);
      failures++;
    } else {
      console.log(`ok   ${path.relative(ROOT, file)}: ${ext} → ${mime}`);
    }
  }
  // .js هم باید text/javascript باشد (برای سازگاری قبلی)
  const jsLine = src.split('\n').find((l) => l.includes("'.js'"));
  if (!jsLine || !jsLine.includes('text/javascript')) {
    console.error(`FAIL ${path.relative(ROOT, file)}: .js باید text/javascript باشد`);
    failures++;
  }
}

// آزمون منطق tts.js: wrapFetchError باید همیشه خطای دارای fa برگرداند
const ttsSrc = fs.readFileSync(path.join(ROOT, 'mobile-app', 'js', 'tts.js'), 'utf8');
if (!ttsSrc.includes("location.protocol === 'file:'")) {
  console.error('FAIL tts.js: تشخیص file:// وجود ندارد');
  failures++;
}
if (!ttsSrc.includes('wrapFetchError')) {
  console.error('FAIL tts.js: پوشش خطای fetch (wrapFetchError) وجود ندارد');
  failures++;
}
// خطای ساخت نشست ort باید پوشش فارسی داشته باشد
if (!ttsSrc.includes('راه\u200cاندازی موتور اجرا (onnxruntime) ناموفق بود')) {
  console.error('FAIL tts.js: پیام فارسی خطای ساخت نشست ort وجود ندارد');
  failures++;
}
console.log('ok   tts.js: تشخیص file:// + پوشش خطاهای fetch/ort');

if (failures) {
  console.error(`\n${failures} مورد ناموفق`);
  process.exit(1);
}
console.log('\nهمهٔ آزمون‌های MIME v2.12.3 پاس شد.');

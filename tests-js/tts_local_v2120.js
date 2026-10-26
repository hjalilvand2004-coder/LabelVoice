/* آزمون‌های v2.12.0 — موتور صوتی لوکال Piper (ابزارهای خالص js/tts.js)
 * اجرا: مستقیم یا از طریق run_tests.js
 * بدون وابستگی به WASM/مرورگر — فقط قواعد خالص (پاریتی با پایتون).
 */
'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const tts = require(path.join(__dirname, '..', 'mobile-app', 'js', 'tts.js'));

let count = 0;
function t(name, fn) {
  fn();
  count++;
  console.log('  ✓ ' + name);
}

/* ---------- rateToSpeed — پاریتی با rate_to_speed پایتون ---------- */
t('rateToSpeed پاریتی با پایتون', () => {
  assert.strictEqual(tts._internal.rateToSpeed('+0%'), 1.0);
  assert.ok(Math.abs(tts._internal.rateToSpeed('+10%') - 1.1) < 1e-9);
  assert.ok(Math.abs(tts._internal.rateToSpeed('-15%') - 0.85) < 1e-9);
  assert.strictEqual(tts._internal.rateToSpeed(''), 1.0);
  assert.strictEqual(tts._internal.rateToSpeed('نامعتبر'), 1.0);
  assert.strictEqual(tts._internal.rateToSpeed('+500%'), 2.0);
  assert.strictEqual(tts._internal.rateToSpeed('-200%'), 0.5);
});

/* ---------- cleanText ---------- */
t('cleanText: حفظ ZWNJ و حذف کنترلی/ایموجی', () => {
  const s = 'نام\u200cدارو: استامینوفن 🎉\u0007 500mg';
  const out = tts._internal.cleanText(s);
  assert.ok(out.includes('\u200c'), 'ZWNJ باید بماند');
  assert.ok(!out.includes('🎉') && !out.includes('\u0007'));
  assert.ok(out.includes('استامینوفن'));
  assert.strictEqual(tts._internal.cleanText('   '), '');
});

/* ---------- chunkSentences ---------- */
t('chunkSentences: شکستن روی مرز جمله + سقف طول', () => {
  const chunks = tts._internal.chunkSentences('نام: استامینوفن. قدرت: پانصد میلی\u200cگرم. تعداد: بیست عدد.', 40);
  assert.ok(chunks.length >= 2, 'حداقل دو قطعه');
  chunks.forEach((c) => assert.ok(c.length <= 40 + 1));
  assert.strictEqual(tts._internal.chunkSentences('', 40).length, 0);
  const hard = tts._internal.chunkSentences('a'.repeat(100), 30);
  assert.strictEqual(hard.length, 4);
  hard.forEach((c) => assert.ok(c.length <= 30));
});

/* ---------- encodeWav ---------- */
t('encodeWav: سرصفحهٔ RIFF/WAVE معتبر (22050Hz مونو 16بیتی)', () => {
  const samples = new Float32Array([0, 0.5, -0.5, 1.0, -1.0]);
  const wav = tts._internal.encodeWav(samples, 22050);
  assert.strictEqual(wav.length, 44 + samples.length * 2);
  assert.strictEqual(wav.readUInt32LE ? null : undefined, undefined); // سازگاری
  const v = new DataView(wav.buffer, wav.byteOffset, wav.byteLength);
  assert.strictEqual(v.getUint32(0, true), 0x46464952);            // RIFF
  assert.strictEqual(v.getUint32(8, true), 0x45564157);            // WAVE
  assert.strictEqual(v.getUint32(24, true), 22050);                 // sample rate
  assert.strictEqual(v.getUint16(22, true), 1);                     // مونو
  assert.strictEqual(v.getUint16(34, true), 16);                    // 16bit
  assert.strictEqual(v.getUint32(40, true), samples.length * 2);    // data size
  assert.strictEqual(v.getInt16(44 + 2, true), 16384);              // 0.5 → ~16384
});

/* ---------- دارایی‌ها: مدل و موتور واقعاً داخل پروژه‌اند ---------- */
t('دارایی‌های TTS داخل فایل‌های پروژه باندل شده‌اند', () => {
  const root = path.join(__dirname, '..', 'mobile-app');
  const required = [
    'vendor/tts/fa_IR-amir-medium.int8.onnx',
    'vendor/tts/fa_IR-amir-medium.onnx.json',
    'vendor/tts/ort.wasm.min.js',
    'vendor/tts/ort-wasm-simd-threaded.mjs',
    'vendor/tts/ort-wasm-simd-threaded.wasm',
    'vendor/tts/piper-phonemize.js',
    'vendor/tts/piper_phonemize.wasm',
    'vendor/tts/piper_phonemize.data'
  ];
  required.forEach((rel) => {
    const p = path.join(root, rel);
    assert.ok(fs.existsSync(p), 'یافت نشد: ' + rel);
    const sz = fs.statSync(p).size;
    assert.ok(sz > 100, 'فایل خالی است: ' + rel);
  });
});

t('پیکربندی Piper: زبان فارسی + نرخ نمونهٔ 22050', () => {
  const cfg = JSON.parse(fs.readFileSync(
    path.join(__dirname, '..', 'mobile-app', 'vendor', 'tts', 'fa_IR-amir-medium.onnx.json'), 'utf8'));
  assert.strictEqual(cfg.espeak.voice, 'fa');
  assert.strictEqual(cfg.audio.sample_rate, 22050);
  assert.ok(cfg.inference && typeof cfg.inference.length_scale === 'number');
});

t('دادهٔ تریم‌شدهٔ فونِم‌ساز حاوی fa_dict و en_dict است و غول‌ها نیستند', () => {
  const glue = fs.readFileSync(
    path.join(__dirname, '..', 'mobile-app', 'vendor', 'tts', 'piper-phonemize.js'), 'utf8');
  assert.ok(glue.includes('fa_dict'), 'fa_dict در متادیتا نیست');
  assert.ok(glue.includes('en_dict'), 'en_dict در متادیتا نیست');
  assert.ok(!glue.includes('ru_dict'), 'ru_dict (۸.۵MB) باید حذف شده باشد');
  const m = glue.match(/remote_package_size:\s*(\d+)/);
  assert.ok(m, 'remote_package_size یافت نشد');
  const declared = parseInt(m[1], 10);
  const actual = fs.statSync(
    path.join(__dirname, '..', 'mobile-app', 'vendor', 'tts', 'piper_phonemize.data')).size;
  assert.strictEqual(declared, actual, 'حجم .data با متادیتای گلو نمی‌خواند');
  assert.ok(actual < 3 * 1024 * 1024, 'دادهٔ تریم‌شده باید زیر ۳MB باشد');
});

t('خط قرمز: هیچ نشانه‌ای از سرویس آنلاین در js/tts.js نباشد', () => {
  const src = fs.readFileSync(
    path.join(__dirname, '..', 'mobile-app', 'js', 'tts.js'), 'utf8');
  ['wss://', 'SpeechSynthesisUtterance', 'speechSynthesis.speak', 'edge-tts',
   'Sec-MS-GEC', 'huggingface.co', 'cdnjs.cloudflare', 'jsdelivr']
    .forEach((token) => {
      assert.ok(!src.includes(token), 'نشانهٔ ممنوع در tts.js: ' + token);
    });
});

t('bridge.py دیگر مسیر /api/tts را سرو نمی‌کند', () => {
  const src = fs.readFileSync(
    path.join(__dirname, '..', 'label_reader', 'bridge.py'), 'utf8');
  assert.ok(!src.includes('path == "/api/tts"'), 'مسیرگردان حذف نشده');
  assert.ok(!src.includes('_handle_tts'), 'هندلر TTS حذف نشده');
});

console.log('v2.12.0 tts_local: ' + count + ' آزمون پاس شد');
module.exports = { passed: count };

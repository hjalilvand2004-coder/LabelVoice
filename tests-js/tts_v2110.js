// آزمون پاریتی TTS v2.11.0 — توکن Sec-MS-GEC v2 و ابزارهای متن (JS ⇄ Python)
// مرجع پایتون: edge-tts==7.3.1 (وکتورها: scripts/tts_parity_vectors.py)
'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const LVTts = require('../mobile-app/js/tts.js');

const vectors = JSON.parse(fs.readFileSync(
  path.join(__dirname, 'tts_parity_vectors.json'), 'utf-8'));

function testTokenParity() {
  assert.strictEqual(LVTts._internal.constants.TRUSTED_TOKEN, vectors.trusted_token,
    'TrustedClientToken mismatch');
  for (const c of vectors.cases) {
    const tok = LVTts._internal.tokenAt(c.ts);
    assert.strictEqual(tok, c.token,
      `token mismatch for ts=${c.ts}\n  js : ${tok}\n  py : ${c.token}`);
  }
  console.log(`  ✓ توکن Sec-MS-GEC v2 — ${vectors.cases.length} وکتور پاریتی با پایتون`);
}

function testDigestParity() {
  for (const c of vectors.cases.slice(0, 2)) {
    const str = c.ticks_str + vectors.trusted_token;
    const data = new Uint8Array(str.length);
    for (let i = 0; i < str.length; i++) data[i] = str.charCodeAt(i) & 0xFF;
    const digest = LVTts._internal.modifiedSha256(data);
    let hex = '';
    for (const b of digest) hex += b.toString(16).padStart(2, '0').toUpperCase();
    assert.strictEqual(hex, c.digest_hex, `digest mismatch ts=${c.ts}`);
  }
  console.log('  ✓ دیجست SHA-256 اصلاح‌شده — پاریتی کامل');
}

function testCs64Parity() {
  for (const c of vectors.cases.slice(0, 2)) {
    const str = c.ticks_str + vectors.trusted_token;
    const data = new Uint8Array(str.length);
    for (let i = 0; i < str.length; i++) data[i] = str.charCodeAt(i) & 0xFF;
    const digest = LVTts._internal.modifiedSha256(data);
    const cs = LVTts._internal.cs64Digest(data, digest);
    // معادل struct.pack("<II", a, b).hex() — هر کلمه little-endian
    const hex = cs.map(v => v.toString(16).padStart(8, '0').toUpperCase())
      .map(h => h.slice(6, 8) + h.slice(4, 6) + h.slice(2, 4) + h.slice(0, 2))
      .join('');
    assert.strictEqual(hex, c.cs64_hex, `cs64 mismatch ts=${c.ts}`);
  }
  console.log('  ✓ دیجست CS64 — پاریتی کامل');
}

function testTextTools() {
  const I = LVTts._internal;
  assert.strictEqual(I.xmlEscape('a<b>&"c'), 'a&lt;b&gt;&amp;"c'); // معرف escape پایتون: فقط & < >
  assert.strictEqual(I.removeIncompatible('عا\u000bلی\u0001'), 'عا لی '); // جایگزینی با فاصله مثل پایتون
  assert.strictEqual(I.removeIncompatible('a\tb\nc\rd'), 'a\tb\nc\rd'); // Tab/LF/CR حفظ می‌شوند
  const parts = I.splitEscapedByBytes('سلام دنیا ' + 'تست '.repeat(400), 120);
  assert.ok(parts.length > 1, 'must split long text');
  for (const p of parts) {
    const n = Buffer.byteLength(p, 'utf8');
    assert.ok(n <= 120, `chunk too big: ${n}`);
  }
  // برش اجباری توکن بی‌فاصلهٔ خیلی بلند
  const one = I.splitEscapedByBytes('الف'.repeat(600), 100);
  assert.ok(one.every(p => Buffer.byteLength(p, 'utf8') <= 100));
  console.log('  ✓ ابزار متن (escape/پاک‌سازی/برش بایتی)');
}

function testUrlConstants() {
  const C = LVTts._internal.constants;
  assert.ok(C.WSS_BASE.startsWith('wss://speech.platform.bing.com/consumer/speech/synthesize/readaloud/edge/v1?TrustedClientToken='));
  assert.strictEqual(C.SEC_MS_GEC_VERSION, '2-143.0.3650.75');
  assert.strictEqual(C.WIN_EPOCH, 11644473600);
  assert.ok(LVTts.voices.includes('fa-IR-FaridNeural'));
  assert.ok(LVTts.voices.includes('fa-IR-DilaraNeural'));
  console.log('  ✓ ثابت‌های URL و صداها');
}

function main() {
  console.log('— آزمون TTS v2.11.0 (پاریتی JS ⇄ edge-tts 7.3.1) —');
  testTokenParity();
  testDigestParity();
  testCs64Parity();
  testTextTools();
  testUrlConstants();
  console.log('PASS: tts_v2110');
}

main();

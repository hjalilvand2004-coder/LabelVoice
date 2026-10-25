/* آزمون‌های v2.9.0 — یکنواخت‌سازی نور (flattenGray) در preprocess.js
 * اجرا: node tests-js/flatten_v290.js
 */
'use strict';
const fs = require('fs');
const path = require('path');

const APP = path.join(__dirname, '..', 'mobile-app');
eval(fs.readFileSync(path.join(APP, 'js', 'preprocess.js'), 'utf8'));
const LBR = globalThis.LBR;

let pass = 0, fail = 0;
function t(name, fn) {
  try { fn(); pass++; console.log('  ✅ ' + name); }
  catch (e) { fail++; console.error('  ❌ ' + name + ' — ' + e.message); }
}
function assert(cond, msg) { if (!cond) throw new Error(msg || 'assert failed'); }

const W = 240, H = 160;

// گرادیان افقی ۴۵٪ تا ۱۰۰٪ + دو سطر متن تیره
function makeGradientGray() {
  const g = new Uint8ClampedArray(W * H);
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      g[y * W + x] = Math.round(245 * (0.45 + 0.55 * x / (W - 1)));
    }
  }
  for (let y = 60; y < 76; y++) for (let x = 40; x < 200; x++) g[y * W + x] = 25;
  for (let y = 100; y < 112; y++) for (let x = 40; x < 200; x++) g[y * W + x] = 35;
  return g;
}

console.log('▼ flattenGray (v2.9.0 — یکنواخت‌سازی نور)');

t('تابع flattenGray صادر شده است', () => {
  assert(typeof LBR.preprocess.flattenGray === 'function', 'export missing');
});

t('گرادیان روشنایی حذف می‌شود (std پس‌زمینه بالا → کم)', () => {
  const g = makeGradientGray();
  const flat = LBR.preprocess.flattenGray(g, W, H);
  // پس‌زمینهٔ بالا (سطرهای 5..15 بدون متن): std ستونی
  const cols = [];
  for (let x = 0; x < W; x += 4) {
    let s = 0, n = 0;
    for (let y = 5; y < 15; y++) { s += flat[y * W + x]; n++; }
    cols.push(s / n);
  }
  const mean = cols.reduce((a, b) => a + b, 0) / cols.length;
  const std = Math.sqrt(cols.reduce((a, b) => a + (b - mean) * (b - mean), 0) / cols.length);
  const meanSrc = [], srcCols = [];
  for (let x = 0; x < W; x += 4) {
    let s = 0, n = 0;
    for (let y = 5; y < 15; y++) { s += g[y * W + x]; n++; }
    srcCols.push(s / n);
  }
  const mS = srcCols.reduce((a, b) => a + b, 0) / srcCols.length;
  const stdS = Math.sqrt(srcCols.reduce((a, b) => a + (b - mS) * (b - mS), 0) / srcCols.length);
  assert(std < stdS * 0.5, `std ${stdS.toFixed(1)} → ${std.toFixed(1)} (کاهش ناکافی)`);
  assert(mean > 220, 'پس‌زمینه پس از flatten باید روشن باشد: ' + mean.toFixed(1));
});

t('متن تیره تیره می‌ماند (کنتراست حفظ می‌شود)', () => {
  const g = makeGradientGray();
  const flat = LBR.preprocess.flattenGray(g, W, H);
  // ناحیهٔ متن سطر اول در سمت تاریک تصویر (x≈40..60)
  let textMean = 0, n = 0;
  for (let y = 60; y < 76; y++) for (let x = 40; x < 60; x++) { textMean += flat[y * W + x]; n++; }
  textMean /= n;
  assert(textMean < 140, 'متن باید تیره بماند: ' + textMean.toFixed(1));
});

t('خروجی در بازهٔ ۰..۲۵۵ و هم‌اندازه است', () => {
  const g = makeGradientGray();
  const flat = LBR.preprocess.flattenGray(g, W, H);
  assert(flat.length === W * H, 'size mismatch');
  let ok = true;
  for (let i = 0; i < flat.length; i++) if (flat[i] < 0 || flat[i] > 255) { ok = false; break; }
  assert(ok, 'out of range');
});

console.log(`\nنتیجه: ${pass} پاس، ${fail} شکست`);
process.exit(fail ? 1 : 0);

/* آزمون v2.7.0 — شفافیت پایپ‌لاین: buildVariants باید trace گام‌به‌گام بدهد
 * اجرا: node tests-js/trace_v270.js
 * canvas با stub حداقلی (مطابق رابطی که preprocess.js استفاده می‌کند).
 */
'use strict';
const fs = require('fs');
const path = require('path');

const APP = path.join(__dirname, '..', 'mobile-app');
['textnorm', 'preprocess'].forEach((f) => {
  eval(fs.readFileSync(path.join(APP, 'js', f + '.js'), 'utf8'));
});
const LBR = globalThis.LBR;

// ---------- stub حداقلی Canvas 2D ----------
function makeCtx(w, h) {
  const data = new Uint8ClampedArray(w * h * 4);
  return {
    imageSmoothingEnabled: true,
    imageSmoothingQuality: 'high',
    fillStyle: '#fff',
    drawImage: function () {},
    fillRect: function () {},
    translate: function () {},
    rotate: function () {},
    getImageData: function (x, y, ww, hh) {
      return { data: new Uint8ClampedArray(ww * hh * 4), width: ww, height: hh };
    },
    createImageData: function (ww, hh) {
      return { data: new Uint8ClampedArray(ww * hh * 4), width: ww, height: hh };
    },
    putImageData: function () {},
    // دسترسی به دادهٔ خام برای آزمون metrics (فقط در stub)
    __data: data
  };
}
function makeCanvas(w, h) {
  const ctx = makeCtx(w, h);
  return {
    width: w, height: h,
    getContext: function () { return ctx; }
  };
}

globalThis.document = {
  createElement: function (tag) {
    if (tag === 'canvas') return makeCanvas(1, 1);
    return {};
  }
};

let passed = 0, failed = 0;
const failures = [];
function test(name, fn) {
  try { fn(); passed++; console.log('  ✅ ' + name); }
  catch (e) { failed++; failures.push(name + ' — ' + e.message); console.log('  ❌ ' + name + ' — ' + e.message); }
}
function eq(a, b, msg) {
  if (a !== b) throw new Error((msg || '') + ' ожид ' + b + ' ≠ ' + a);
}
function ok(a, msg) { if (!a) throw new Error(msg || 'نادرست'); }

const SETTINGS = {
  target_min_side: 300,
  max_side_px: 2000,
  clahe_clip_limit: 2.0,
  clahe_tile_size: 8,
  use_binarized_variant: true,
  use_sharpened_variant: true,
  use_white_on_dark_variant: true,
  use_ink_isolated_variant: true
};

console.log('--- آزمون‌های trace پایپ‌لاین (v2.7.0) ---');

test('buildVariants آرایهٔ trace با ترتیب صحیح گام‌ها می‌دهد', () => {
  const src = makeCanvas(400, 300);
  const built = LBR.preprocess.buildVariants(src, 400, 300, SETTINGS);
  ok(Array.isArray(built.trace), 'trace آرایه است');
  const keys = built.trace.map((s) => s.key);
  eq(keys[0], 'original', 'گام اول نسخهٔ اصلی است');
  ['gray_clahe', 'sharpened', 'binarized', 'white_on_dark', 'ink_isolated'].forEach((k) => {
    ok(keys.indexOf(k) >= 0, 'گام ' + k + ' در trace هست');
  });
  eq(keys.length, Object.keys(built.variants).length, 'تعداد trace = تعداد واریانت‌ها');
});

test('هر گام عنوان/توضیح فارسی + بوم با ابعاد درست + معیارها دارد', () => {
  const src = makeCanvas(400, 300);
  const built = LBR.preprocess.buildVariants(src, 400, 300, SETTINGS);
  built.trace.forEach((s) => {
    ok(s.title_fa && s.title_fa.length > 5, 'عنوان فارسی: ' + s.title_fa);
    ok(s.desc_fa && s.desc_fa.length > 20, 'توضیح فارسی گام ' + s.key);
    ok(s.canvas && s.canvas.width === built.width && s.canvas.height === built.height,
      'ابعاد بوم گام ' + s.key + ' = ' + built.width + '×' + built.height);
    ok(s.metrics && typeof s.metrics.brightness === 'number' && typeof s.metrics.contrast === 'number',
      'معیارهای عددی گام ' + s.key);
    ok(s.metrics.brightness >= 0 && s.metrics.brightness <= 255, 'روشنایی در بازهٔ ۰ تا ۲۵۵');
    ok(s.metrics.contrast >= 0, 'کنتراست نامنفی');
  });
});

test('توضیح دودویی پنجرهٔ ۳۱ را ذکر می‌کند و توضیح جوهر ۲۵۵ منهای بیشینه را', () => {
  const built = LBR.preprocess.buildVariants(makeCanvas(400, 300), 400, 300, SETTINGS);
  const byKey = {};
  built.trace.forEach((s) => { byKey[s.key] = s; });
  ok(byKey.binarized.desc_fa.indexOf('۳۱') >= 0, 'ذکر پنجرهٔ ۳۱ در دودویی');
  ok(byKey.ink_isolated.desc_fa.indexOf('۲۵۵') >= 0, 'ذکر ۲۵۵ منهای بیشینه در جداسازی جوهر');
  ok((byKey.gray_clahe.title_fa + ' ' + byKey.gray_clahe.desc_fa).indexOf('CLAHE') >= 0, 'ذکر CLAHE');
});

test('با خام‌بودن گزینه‌ها فقط original + gray_clahe برمی‌گردد (بدون خرابی)', () => {
  const min = Object.assign({}, SETTINGS, {
    use_binarized_variant: false, use_sharpened_variant: false,
    use_white_on_dark_variant: false, use_ink_isolated_variant: false
  });
  const built = LBR.preprocess.buildVariants(makeCanvas(200, 150), 200, 150, min);
  eq(built.trace.length, 2, 'فقط دو گام');
  eq(built.trace[0].key, 'original');
  eq(built.trace[1].key, 'gray_clahe');
});

test('واریانت‌ها و trace به یک بوم مشترک اشاره می‌کنند (نمایش همان چیزی که OCR خوانده)', () => {
  const built = LBR.preprocess.buildVariants(makeCanvas(400, 300), 400, 300, SETTINGS);
  built.trace.forEach((s) => {
    eq(s.canvas, built.variants[s.key], 'بوم گام ' + s.key + ' همان بوم واریانت است');
  });
});

console.log('\nنتیجه: ' + passed + ' پاس، ' + failed + ' خطا');
if (failed) { failures.forEach((f) => console.log('  ✗ ' + f)); process.exit(1); }

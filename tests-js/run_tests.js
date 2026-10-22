/* آزمون‌های واحد منطق جاوااسکریپت — پورت موارد حیاتی pytest
 * اجرا: node tests-js/run_tests.js
 */
'use strict';
const fs = require('fs');
const path = require('path');

const APP = path.join(__dirname, '..', 'mobile-app');
['textnorm', 'patterns', 'guard', 'extractor', 'responder', 'pipeline'].forEach((f) => {
  // بارگذاری ماژول‌های IIFE در همین فرایند (به globalThis وصل می‌شوند)
  eval(fs.readFileSync(path.join(APP, 'js', f + '.js'), 'utf8'));
});
const LBR = globalThis.LBR;

const tn = LBR.textnorm;
const P = LBR.patterns;
const guard = LBR.guard;
const ext = LBR.extractor;
const resp = LBR.responder;
const pipe = LBR.pipeline;

const SETTINGS = {
  ocr_languages: 'fas+eng',
  tesseract_psm: 3,
  tesseract_extra_psm: 6,
  low_confidence_threshold: 0.55,
  target_min_side: 1000,
  max_side_px: 4000,
  clahe_clip_limit: 2.0,
  clahe_tile_size: 8,
  deskew_max_angle_deg: 15,
  use_binarized_variant: false,
  min_dimension_px: 300,
  blur_laplacian_threshold: 45.0,
  severe_blur_threshold: 18.0,
  glare_highlight_ratio: 0.10,
  dark_mean_brightness: 55.0
};

function makeLine(idx, text, y = 0, x = 0, conf = 0.92) {
  return {
    id: 'line_' + String(idx).padStart(3, '0'),
    text: text,
    normalized_text: tn.normalizeForMatching(text),
    source_ids: ['ocr_' + String(idx).padStart(3, '0')],
    bbox: { x: x, y: y, w: Math.max(1, 10 * text.length), h: 24 },
    confidence_mean: conf
  };
}

function mkField(key, value, unit, status, conf) {
  return {
    key: key, label_fa: ext.FIELD_LABELS_FA[key] || key, value: value, unit: unit,
    raw_text: value + ' ' + (unit || ''), source_ids: ['ocr_002'],
    confidence: conf, status: status, previous_values: [], note_fa: null
  };
}
function evidence(strengthValue, strengthUnit) {
  return { fields: { strength: { value: strengthValue || '500', unit: strengthUnit || 'mg',
    raw_text: (strengthValue || '500') + ' ' + (strengthUnit || 'mg'), note_fa: null } } };
}
// قطعه خام مثل OcrRaw واقعی: مختصات تخت برای mergePieces + bbox برای buildLines
function mkPiece(idx, text, y, x, conf, variant) {
  const xx = x === undefined ? 20 : x;
  const w = Math.max(1, 10 * text.length);
  return {
    id: '', text: text, normalized_text: tn.normalizeForMatching(text),
    x: xx, y: y, w: w, h: 24,
    bbox: { x: xx, y: y, w: w, h: 24 },
    confidence: conf === undefined ? 0.92 : conf,
    variant: variant || 'original', engine: 'fake'
  };
}

let passed = 0, failed = 0;
const failures = [];
function test(name, fn) {
  try {
    fn();
    passed++;
    console.log('  PASS  ' + name);
  } catch (e) {
    failed++;
    failures.push(name + ' → ' + e.message);
    console.log('  FAIL  ' + name + '\n        ' + e.message);
  }
}
function assertEq(actual, expected, msg) {
  const a = JSON.stringify(actual), b = JSON.stringify(expected);
  if (a !== b) throw new Error((msg || '') + ' expected=' + b + ' actual=' + a);
}
function assert(cond, msg) {
  if (!cond) throw new Error(msg || 'assertion failed');
}
function runFields(lines, productType, imageHeight) {
  return ext.extractFields(lines, productType || 'medicine', SETTINGS, imageHeight);
}
function fieldsOf(lines) { return runFields(lines).fields; }

// ---------------- نرمال‌سازی متن ----------------
console.log('— textnorm —');
test('نگاشت ي/ك عربی به فارسی', () => {
  assertEq(tn.normalizeChars('\u064a\u0643'), '\u06cc\u06a9');
});
test('یکسان‌سازی ارقام فارسی/عربی به لاتین', () => {
  assertEq(tn.normalizeDigitsAscii('\u06f5\u06f0\u06f0'), '500');
  assertEq(tn.normalizeDigitsAscii('\u0662\u0660'), '20');
  assertEq(tn.normalizeDigitsAscii('500 mg'), '500 mg');
});
test('ارقام لاتین به فارسی برای نمایش', () => {
  assertEq(tn.digitsToPersian('500'), '\u06f5\u06f0\u06f0');
  assertEq(tn.digitsToPersian('2027/06'), '\u06f2\u06f0\u06f2\u06f7/\u06f0\u06f6');
});
test('نیم‌فاصله و کشیده در مطابقه', () => {
  assertEq(tn.normalizeForMatching('\u0645\u06cc\u0644\u06cc\u200c\u06af\u0631\u0645'),
    '\u0645\u06cc\u0644\u06cc \u06af\u0631\u0645');
  assert(!tn.normalizeForMatching('abc\u0640def').includes('\u0640'));
});
test('فشرده‌سازی فاصله‌ها', () => {
  assertEq(tn.normalizeForMatching('  a   b\tc \n'), 'a b c');
});
test('بدون تصحیح معنایی 0/O و 1/I', () => {
  assertEq(tn.normalizeForMatching('O1l0'), 'O1l0');
});
test('تشخیص زبان', () => {
  assert(tn.isMostlyPersian('\u0627\u0633\u062a\u0627\u0645\u06cc\u0646\u0648\u0641\u0646'));
  assert(tn.isMostlyLatin('Paracetamol'));
  assert(!tn.isMostlyPersian('Paracetamol'));
});
test('نمایش نرمال‌شده نیم‌فاصله را حفظ می‌کند', () => {
  assert(tn.cleanedDisplayText('\u0645\u06cc\u200c\u06af\u0631\u0645').includes('\u200c'));
});

// ---------------- الگوها ----------------
console.log('— patterns —');
test('الگوی قدرت ساده و ترکیبی', () => {
  const m1 = P.RE_STRENGTH.exec('500 mg');
  assertEq([m1.groups.num, P.UNIT_CANONICAL[m1.groups.unit]], ['500', 'mg']);
  const m2 = P.RE_STRENGTH.exec('250 mg/5 mL');
  assert(m2.groups.num2 === '5', 'num2 باید 5 باشد');
});
test('الگوی تاریخ و ابهام', () => {
  assertEq(P.inferDateAmbiguity('2027', '06', null), { value: '2027/06', ambiguous: false });
  assertEq(P.inferDateAmbiguity('12', '06', '2027').ambiguous, true);
  assertEq(P.inferDateAmbiguity('27', '06', null).ambiguous, true);
});

// ---------------- استخراج فیلدها ----------------
console.log('— extractor —');
test('نمونه پاراستامول: نام/قدرت/تعداد/انقضا با شواهد', () => {
  const lines = [makeLine(1, 'Paracetamol', 30), makeLine(2, '500 mg', 100),
    makeLine(3, '20 Tablets', 170), makeLine(4, 'EXP: 2027/06', 240)];
  const { fields } = runFields(lines);
  assertEq(fields.name.value, 'Paracetamol');
  assertEq(fields.strength.value, '500');
  assertEq(fields.strength.unit, 'mg');
  assertEq(fields.count.value, '20');
  assertEq(fields.count.unit, 'tablets');
  assertEq(fields.expiry_date.value, '2027/06');
  for (const k of ['name', 'strength', 'count', 'expiry_date']) {
    assertEq(fields[k].status, 'extracted', k);
    assert(fields[k].source_ids.length > 0, k + ' باید شاهد داشته باشد');
  }
});
test('تمایز mcg از mg', () => {
  const { fields } = runFields([makeLine(1, 'Vitamin B12', 30), makeLine(2, '1000 mcg', 100)]);
  assertEq(fields.strength.unit, 'mcg');
});
test('قدرت ترکیبی 250 mg/5 mL', () => {
  const { fields } = runFields([makeLine(1, 'Amoxicillin 250 mg/5 mL', 30)]);
  assertEq(fields.name.value, 'Amoxicillin');
  assertEq(fields.strength.value, '250 mg/5 mL');
  assertEq(fields.strength.unit, null);
});
test('mL تنها = حجم بسته نه قدرت (قطعی اعلام نمی‌شود)', () => {
  const { fields } = runFields([makeLine(1, 'Mystery Syrup', 30), makeLine(2, '150 mL', 100)]);
  assertEq(fields.strength.status, 'uncertain');
  assert((fields.strength.note_fa || '').includes('حجم'));
  assertEq(fields.count.status, 'missing');
});
test('محافظ مقدار صفر (۵۰۰→۰ قطعی نمی‌شود)', () => {
  const { fields } = runFields([makeLine(1, 'Drug X', 30), makeLine(2, '0 mg', 100, 0, 0.9)]);
  assertEq(fields.strength.status, 'uncertain');
});
test('سال تنها مبهم است (EXP: 2027)', () => {
  const { fields } = runFields([makeLine(1, 'Drug X', 30), makeLine(2, 'EXP: 2027', 100)]);
  assertEq(fields.expiry_date.value, '2027');
  assertEq(fields.expiry_date.status, 'uncertain');
  assert(fields.expiry_date.note_fa, 'توضیح ابهام ثبت شود');
});
test('تناقض قدرت علامت‌گذاری می‌شود', () => {
  const { fields } = runFields([makeLine(1, '500 mg', 30), makeLine(2, '250 mg', 100)]);
  assertEq(fields.strength.status, 'conflicting');
  assert(fields.strength.note_fa.includes('500') && fields.strength.note_fa.includes('250'));
});
test('حجم بطری با قدرت ترکیبی تناقض نسازد', () => {
  const lines = [makeLine(1, 'Amoxicillin 250 mg/5 mL', 30), makeLine(2, '100 mL bottle', 100)];
  const { fields } = runFields(lines);
  assertEq(fields.strength.status, 'extracted');
  assertEq(fields.strength.value, '250 mg/5 mL');
});
test('محصول عمومی: گرم قدرت نیست، وزن خالص است', () => {
  const lines = [makeLine(1, 'Happy Cookie', 30), makeLine(2, 'Net Wt: 120 g', 100)];
  const { fields } = runFields(lines, 'general_product');
  assert(!('strength' in fields), 'قالب عمومی فیلد strength ندارد');
  assertEq(fields.net_weight.value, '120');
  assertEq(fields.net_weight.unit, 'g');
});
test('قدرت و تعداد فارسی (ارقام فارسی)', () => {
  const lines = [makeLine(1, '\u0627\u0633\u062a\u0627\u0645\u06cc\u0646\u0648\u0641\u0646', 30),
    makeLine(2, '\u06f5\u06f0\u06f0 \u0645\u06cc\u0644\u06cc\u200c\u06af\u0631\u0645', 100),
    makeLine(3, '\u06f2\u06f0 \u0642\u0631\u0635', 170)];
  const { fields } = runFields(lines);
  assertEq(fields.strength.value, '500');
  assertEq(fields.strength.unit, 'mg');
  assertEq(fields.count.value, '20');
  assertEq(fields.count.unit, 'قرص');
});
test('دستور چاپ‌شده فقط به‌عنوان متن بازخوانی می‌شود', () => {
  const lines = [makeLine(1, 'Drug X 10 mg', 30),
    makeLine(2, '\u0647\u0631 \u06f8 \u0633\u0627\u0639\u062a \u06cc\u06a9 \u0642\u0631\u0635 \u0645\u0635\u0631\u0641 \u06a9\u0646\u06cc\u062f', 100)];
  const { fields } = runFields(lines);
  assert(fields.printed_directives.status !== 'missing');
  assert(fields.printed_directives.value.includes('مصرف کنید'));
});
test('قالب دارویی: فیلدهای دارو، بدون وزن خالص', () => {
  const { fields } = runFields([makeLine(1, 'Drug X 500 mg', 30), makeLine(2, '20 Tablets', 100)]);
  assert('active_ingredient' in fields);
  assert(!('net_weight' in fields));
});
test('هشدار چندمحصولی', () => {
  const lines = [makeLine(1, 'Ibuprofen 400 mg', 30), makeLine(2, '24 Tablets', 100),
    makeLine(3, 'Aspirin 100 mg', 800), makeLine(4, '30 Tablets', 870)];
  const { warnings } = runFields(lines, 'medicine', 1000);
  assert(warnings.some((w) => w.includes('یک بسته را برش بزنید')), JSON.stringify(warnings));
});
test('بدون ساخت اطلاعات از هیچ', () => {
  const { fields } = runFields([makeLine(1, 'Drug X 500 mg', 30)]);
  assertEq(fields.count.value, null);
  assertEq(fields.count.status, 'missing');
  assertEq(fields.manufacturer.value, null);
  assertEq(fields.expiry_date.value, null);
});
test('طبقه‌بندی نوع بسته', () => {
  const med = ext.classifyProductType(['Paracetamol 500 mg', '20 Tablets']);
  assertEq(med.type, 'medicine');
  const gen = ext.classifyProductType(['بیسکویت', 'وزن خالص 120 گرم', 'ترکیبات: آرد، شکر']);
  assertEq(gen.type, 'general_product');
});

// ---------------- پاسخ قالبی و نگهبان ----------------
console.log('— responder & guard —');
test('جمله دقیق نمونه مشخصات', () => {
  const lines = [makeLine(1, 'Paracetamol', 30), makeLine(2, '500 mg', 100),
    makeLine(3, '20 Tablets', 170)];
  const response = resp.buildResponse(fieldsOf(lines), [], [], 3);
  assert(response.includes('نام درج‌شده روی بسته: Paracetamol.'), response);
  assert(response.includes('قدرت درج‌شده: \u06f5\u06f0\u06f0 \u0645\u06cc\u0644\u06cc\u200c\u06af\u0631\u0645.'), response);
  assert(response.includes('تعداد درج‌شده: \u06f2\u06f0 \u0642\u0631\u0635.'), response);
  assert(response.includes('توصیه پزشکی') && response.includes('مقدار مصرف نیستند'), response);
  assert(!response.includes('دوز'), 'مرز کلیدی: قدرت هرگز دوز نامیده نمی‌شود | ' + response);
});
test('هیچ کاربرد درمانی اضافه نمی‌شود', () => {
  const lines = [makeLine(1, 'Paracetamol', 30), makeLine(2, '500 mg', 100),
    makeLine(3, '20 Tablets', 170)];
  const response = resp.buildResponse(fieldsOf(lines), [], [], 3);
  assert(!response.includes('کاهش تب'), response);
  assert(!response.includes('کاهش درد'), response);
  assert(!response.includes('مصرف کنید'), response);
});
test('قدرت نامطمئن قطعی بیان نمی‌شود', () => {
  const fields = { strength: mkField('strength', '500', 'mg', 'uncertain', 0.3) };
  const response = resp.buildResponse(fields, [], [], 5);
  assert(response.includes('واضح خوانده نشد'), response);
  assert(response.includes('خوانش احتمالی'), response);
});
test('قدرت متناقض قطعی بیان نمی‌شود', () => {
  const f = mkField('strength', '500', 'mg', 'conflicting', 0.9);
  f.note_fa = 'مقادیر متفاوتی خوانده شد: 500، 250.';
  const response = resp.buildResponse({ strength: f }, [], [], 5);
  assert(response.includes('قطعی اعلام نمی‌شود'), response);
});
test('بدون متن → راهنمای تلاش دوباره', () => {
  assertEq(resp.buildResponse({}, [], [], 0), resp.NO_TEXT_RESPONSE_FA);
});
test('پیشوند دستور چاپ‌شده', () => {
  const lines = [makeLine(1, 'Drug X 10 mg', 30),
    makeLine(2, '\u0647\u0631 \u06f8 \u0633\u0627\u0639\u062a \u06cc\u06a9 \u0642\u0631\u0635 \u0645\u0635\u0631\u0641 \u06a9\u0646\u06cc\u062f', 100)];
  const response = resp.buildResponse(fieldsOf(lines), [], [], 2);
  assert(response.includes('متن دستور چاپ‌شده روی بسته'), response);
  assert(response.includes('توصیه شخصی به شما نیست'), response);
});
test('هشدار کیفیت در پاسخ', () => {
  const fields = fieldsOf([makeLine(1, 'Drug X 500 mg', 30)]);
  const issue = { code: 'blurry', severity: 'severe', message_fa: 'متن بسته واضح نیست.' };
  const response = resp.buildResponse(fields, [issue], [], 2);
  assert(response.includes('هشدار کیفیت تصویر'), response);
});
test('قالب قدرت ترکیبی در پاسخ', () => {
  const f = mkField('strength', '250 mg/5 mL', null, 'extracted', 0.9);
  f.label_fa = 'قدرت';
  const s = resp.formatStrength(f);
  assert(s.includes('\u0645\u06cc\u0644\u06cc\u200c\u06af\u0631\u0645'), s);
  assert(s.includes(' در '), s);
});
test('نگهبان: ادعای درمانی رد می‌شود', () => {
  const r = guard.validateAgainstEvidence('این دارو برای کاهش تب و درد استفاده می‌شود.', evidence());
  assert(!r.ok, JSON.stringify(r));
});
test('نگهبان: برنامه مصرف رد می‌شود', () => {
  const r = guard.validateAgainstEvidence('قدرت 500 mg است. هر \u06f6 ساعت یک قرص مصرف کنید.', evidence());
  assert(!r.ok, JSON.stringify(r));
});
test('نگهبان: عدد خارج از شواهد رد می‌شود', () => {
  const r = guard.validateAgainstEvidence('قدرت درج‌شده: 600 mg.', evidence('500'));
  assert(!r.ok, JSON.stringify(r));
  const r2 = guard.validateAgainstEvidence('قدرت درج‌شده: \u06f5\u06f0\u06f0 میلی\u200cگرم.', evidence('500'));
  assert(r2.ok, JSON.stringify(r2));
});
test('نگهبان: «دوز مصرف» ممنوع است', () => {
  const r = guard.validateAgainstEvidence('دوز مصرف این دارو 500 mg است.', evidence());
  assert(!r.ok, JSON.stringify(r));
});
test('نگهبان: بازنویسی وفادار پذیرفته می‌شود', () => {
  const r = guard.validateAgainstEvidence(
    'نام درج‌شده روی بسته: Paracetamol. قدرت درج‌شده: \u06f5\u06f0\u06f0 میلی\u200cگرم.', evidence());
  assert(r.ok, JSON.stringify(r));
});
test('نگهبان: دستور چاپ‌شده فقط داخل گیومه', () => {
  const text = 'متن دستور چاپ‌شده روی بسته: «هر \u06f8 ساعت یک قرص مصرف کنید». این صرفاً بازخوانی متن است.';
  assert(guard.validateText(text).ok, JSON.stringify(guard.validateText(text)));
});
test('خودآزمایی قالب: پاسخ کامل از نگهبان عبور می‌کند', () => {
  const lines = [makeLine(1, 'Paracetamol', 30), makeLine(2, '500 mg', 100),
    makeLine(3, '20 Tablets', 170), makeLine(4, 'EXP: 2027/06', 240)];
  const response = resp.buildResponse(fieldsOf(lines), [], [], 4);
  const check = guard.validateText(response);
  assert(check.ok, JSON.stringify(check.violations) + ' | ' + response);
});

// ---------------- خط پردازش ----------------
console.log('— pipeline —');
test('بازچینی منطقی سطرهای فارسی (RTL)', () => {
  // واژه‌های فارسی به ترتیب بصری (چپ→راست ذخیره شده) باید بازچینی شوند
  const pieces = [mkPiece(1, 'قرص', 30, 20), mkPiece(2, '\u0645\u06cc\u0644\u06cc\u200c\u06af\u0631\u0645', 30, 140),
    mkPiece(3, '\u06f5\u06f0\u06f0', 30, 260)];
  const lines = pipe.buildLines(pieces);
  assertEq(lines.length, 1);
  assert(lines[0].text.startsWith('\u06f5\u06f0\u06f0'), lines[0].text);
  assert(lines[0].text.endsWith('قرص'), lines[0].text);
});
test('ادغام فازی خوانش‌های مشابه دو PSM', () => {
  const group = [mkPiece(1, 'Paracetamol', 30, 20, 0.90),
    mkPiece(2, 'Paracetam0l', 30, 20, 0.95, 'gray_clahe')];
  const out = pipe.dedupeSimilarPieces(group);
  assertEq(out.length, 1);
  assertEq(out[0].confidence, 0.95, 'اطمینان بالاتر حفظ شود');
});
test('قطعه کوتاهِ زیرمجموعه حذف می‌شود', () => {
  // مطابق قاعده پایتون: طول نگه‌داشته‌شده ≥ 4 و زیرمجموعه کوتاه ≤ 3
  const group = [mkPiece(1, 'AB12', 30, 20), mkPiece(2, '2', 30, 22)];
  const out = pipe.dedupeSimilarPieces(group);
  assertEq(out.length, 1);
});
test('ارقام کوتاه متفاوت ادغام نمی‌شوند (5 و 6)', () => {
  const group = [mkPiece(1, '5', 30, 20), mkPiece(2, '6', 30, 20)];
  const out = pipe.dedupeSimilarPieces(group);
  assertEq(out.length, 2);
});
test('حذف تکراری بین نسخه‌ها با IoU', () => {
  const raw = [mkPiece(1, '500 mg', 30, 20), mkPiece(2, '500 mg', 30, 22, 0.95, 'gray_clahe')];
  const pieces = pipe.mergePieces(raw);
  assertEq(pieces.length, 1);
  assertEq(pieces[0].confidence, 0.95);
});
test('اصلاح دستی کاربر با حفظ منشأ', () => {
  const result = pipe.buildResultFromPieces(
    [mkPiece(1, 'Paracetamol', 30), mkPiece(2, '500', 100), mkPiece(3, 'mg', 100, 120)],
    SETTINGS, 600, 400, {}, {});
  pipe.applyUserCorrections(result, { strength: '\u06f5\u06f0\u06f0' });
  const f = result.fields.strength;
  assertEq(f.status, 'user_corrected');
  assertEq(f.previous_values[0], '500');
  assertEq(f.confidence, 1.0);
  assert(result.response_fa.includes('\u0627\u0635\u0644\u0627\u062d\u200c\u0634\u062f\u0647 \u062a\u0648\u0633\u0637 \u0634\u0645\u0627'), result.response_fa);
});
test('خروجی خط کامل: نگهبان و پاسخ', () => {
  const pieces = [mkPiece(1, 'Paracetamol', 30), mkPiece(2, '500', 100),
    mkPiece(3, 'mg', 100, 120), mkPiece(4, '20', 170), mkPiece(5, 'Tablets', 170, 120)];
  const result = pipe.buildResultFromPieces(pieces, SETTINGS, 600, 400, {}, {});
  assertEq(result.product_type, 'medicine');
  assert(result.guard_self_check.ok, JSON.stringify(result.guard_self_check));
  assert(result.response_fa.includes('Paracetamol'), result.response_fa);
  assert(!result.response_fa.includes('دوز'), result.response_fa);
});
test('کیفیت تصویر: تاری شدید تشخیص داده می‌شود', () => {
  // تصویر یکدست → واریانس لاپلاسین ≈ 0 → تاری شدید
  const w = 200, h = 200;
  const gray = new Uint8ClampedArray(w * h).fill(128);
  const q = pipe.assessQuality(gray, w, h, SETTINGS);
  assert(q.issues.some((i) => i.code === 'blurry' && i.severity === 'severe'), JSON.stringify(q.issues));
});

console.log('\nنتیجه: ' + passed + ' پاس، ' + failed + ' شکست');
if (failed) {
  console.log('\nجزئیات شکست‌ها:');
  failures.forEach((f) => console.log('  ✗ ' + f));
  process.exit(1);
}

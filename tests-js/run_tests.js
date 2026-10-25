/* آزمون‌های واحد منطق جاوااسکریپت — پورت موارد حیاتی pytest
 * اجرا: node tests-js/run_tests.js
 */
'use strict';
const fs = require('fs');
const path = require('path');

const APP = path.join(__dirname, '..', 'mobile-app');
['textnorm', 'patterns', 'guard', 'extractor', 'responder', 'pipeline', 'boxdetect'].forEach((f) => {
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
  // v1.2.0: مقدمه نوع محصول + شمارش فیلدها + سلب مسئولیت جدید
  assert(response.includes('این محصول بسته\u200cبندی\u200cشده است و \u06f4 فیلد'), response);
  assert(response.includes('توصیه پزشکی') && response.includes('مقدار مصرف نیست'), response);
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
// ---------------- v1.6.0: اعلام مرحله‌به‌مرحله (onStage) ----------------
test('اعلام مراحل ۳ و ۴ با onStage (پاریتی با stage_callback دسکتاپ)', () => {
  const pieces = [mkPiece(1, 'Paracetamol', 30), mkPiece(2, '500', 100),
    mkPiece(3, 'mg', 100, 120), mkPiece(4, '20', 170), mkPiece(5, 'Tablets', 170, 120)];
  const events = [];
  pipe.buildResultFromPieces(pieces, SETTINGS, 600, 400, {}, {
    onStage: (key, payload) => events.push([key, payload])
  });
  assertEq(events.map((e) => e[0]).join(','), 'fields,response');
  const fieldsP = events[0][1];
  assertEq(fieldsP.evidence_coverage, 100);
  assertEq(fieldsP.product_type_fa, 'دارو');
  assert((fieldsP.status_counts.extracted || 0) >= 3, JSON.stringify(fieldsP.status_counts));
  assert(fieldsP.duration_ms !== undefined && fieldsP.duration_ms !== null);
  const respP = events[1][1];
  assertEq(respP.guard_ok, true);
  assertEq(respP.llm_used, false);
  assert(respP.length > 0 && respP.preview.length > 0);
  // بدون onStage هم باید سالم کار کند (سازگاری رو به عقب)
  const r2 = pipe.buildResultFromPieces(pieces, SETTINGS, 600, 400, {}, {});
  assert(r2.response_fa.includes('Paracetamol'), r2.response_fa);
});

test('کیفیت تصویر: تاری شدید تشخیص داده می‌شود', () => {
  // تصویر یکدست → واریانس لاپلاسین ≈ 0 → تاری شدید
  const w = 200, h = 200;
  const gray = new Uint8ClampedArray(w * h).fill(128);
  const q = pipe.assessQuality(gray, w, h, SETTINGS);
  assert(q.issues.some((i) => i.code === 'blurry' && i.severity === 'severe'), JSON.stringify(q.issues));
});

// ---------------- v1.2.0: تشخیص بسته، امتیاز جهت، تیزکردن ----------------
console.log('— boxdetect & scoreOcrYield —');

// ساخت تصویر مصنوعی: پس‌زمینه یکدست + بلوک مستطیلی «جعبه» پر از متن
function makeBoxScene(w, h, bx, by, bw, bh) {
  const gray = new Uint8ClampedArray(w * h).fill(230); // پس‌زمینه روشن یکدست
  for (let y = by; y < by + bh; y++) {
    for (let x = bx; x < bx + bw; x++) {
      // لبه‌های جعبه + خطوط متنی داخل آن (نوارهای افقی تیره)
      const onBorder = (x === bx || x === bx + bw - 1 || y === by || y === by + bh - 1);
      const isTextBar = (y > by + 4 && y < by + bh - 4 && (y % 6 < 2) && (x % 3 !== 0));
      gray[y * w + x] = (onBorder || isTextBar) ? 30 : 235;
    }
  }
  return gray;
}

test('boxdetect: جعبه وسط قاب پیدا و برش درست است', () => {
  const w = 400, h = 300;
  const gray = makeBoxScene(w, h, 80, 60, 240, 180);
  const det = LBR.boxdetect.detectLabelRegion(gray, w, h);
  assert(det.found, JSON.stringify(det));
  // برش باید نزدیک مرزهای واقعی جعبه (با حاشیه) باشد
  const b = det.box;
  assert(b.x <= 80 && b.y <= 60, JSON.stringify(b));
  assert(b.x + b.w >= 320 && b.y + b.h >= 240, JSON.stringify(b));
  // برش نباید کل قاب را بپوشاند
  assert(b.w < w * 0.95 || b.h < h * 0.95, JSON.stringify(b));
});

test('boxdetect: قاب کاملاً پر از متن → برش نکن', () => {
  const w = 300, h = 300;
  const gray = makeBoxScene(w, h, 0, 0, w, h);
  const det = LBR.boxdetect.detectLabelRegion(gray, w, h);
  assert(!det.found, 'fills_whole_frame باید رد شود: ' + JSON.stringify(det));
  assertEq(det.reason, 'fills_whole_frame');
});

test('boxdetect: پس‌زمینه خالی بدون محتوا → برش نکن', () => {
  const w = 300, h = 300;
  const gray = new Uint8ClampedArray(w * h).fill(200);
  const det = LBR.boxdetect.detectLabelRegion(gray, w, h);
  assert(!det.found, JSON.stringify(det));
});

test('boxdetect: تصویر خیلی کوچک → رد', () => {
  const gray = new Uint8ClampedArray(30 * 30).fill(128);
  const det = LBR.boxdetect.detectLabelRegion(gray, 30, 30);
  assertEq(det.reason, 'image_too_small');
});

test('scoreOcrYield: خوانش پرمحتوا نمره بالاتر از خوانش تهی دارد', () => {
  const rich = [mkPiece(1, 'Paracetamol', 90), mkPiece(2, '500', 95),
    mkPiece(3, 'mg', 95, 120), mkPiece(4, '20', 90), mkPiece(5, 'Tablets', 92, 120),
    mkPiece(6, 'Exp', 90), mkPiece(7, '2027/06', 88)];
  const empty = [mkPiece(1, 'x', 10)];
  const yr = pipe.scoreOcrYield(rich);
  const ye = pipe.scoreOcrYield(empty);
  assert(yr.score > ye.score, JSON.stringify({ rich: yr, empty: ye }));
  assert(yr.score > 60, JSON.stringify(yr)); // جایزه الگوها اعمال شده
  assertEq(yr.pieces, 7);
});

test('scoreOcrYield: متن چرخیده (بی‌معنا) نمره الگو نمی‌گیرد', () => {
  const rotated = [mkPiece(1, 'lawomraparatec', 80), mkPiece(2, '059', 80),
    mkPiece(3, 'gm', 80, 100)];
  const y = pipe.scoreOcrYield(rotated);
  assert(y.score < 60, JSON.stringify(y));
});


// ---------- v1.7.0: دروازه نام، گیت قطعه، ادغام بهترین-اول ----------
console.log('— v1.7.0 کیفیت OCR —');

test('plausibleName: خوانش آشغال کاربر رد می‌شود', () => {
  assertEq(ext.plausibleName('RIE [SE ۱ ES {= ray WE'), false);
  assertEq(ext.plausibleName('@ » °'), false);
  assertEq(ext.plausibleName("__import__('os').system('echo hacked')"), false);
});

test('plausibleName: نام واقعی قبول می‌شود', () => {
  assertEq(ext.plausibleName('MEDICINE'), true);
  assertEq(ext.plausibleName('استامینوفن'), true);
});

test('filterPieces: نماد محض و کادر-غول‌پیکر حذف می‌شوند', () => {
  const raws = [
    mkPiece(1, '@', 0, 0, 0.9),
    mkPiece(2, 'MEDICINE', 30, 0, 0.96),
    mkPiece(3, '3', 60, 0, 0.56),
  ];
  raws[2].w = 431; raws[2].h = 394; // کادر غول‌پیکر
  const kept = pipe.filterPieces(raws, 1000 * 1000, SETTINGS);
  assertEq(kept.map((p) => p.text), ['MEDICINE']);
});

test('filterPieces: واحد کم‌اطمینان mg حذف نمی‌شود', () => {
  const kept = pipe.filterPieces([mkPiece(1, 'mg', 0, 0, 0.30)], 1000000, SETTINGS);
  assertEq(kept.length, 1);
});

test('mergePiecesBestFirst: خوانش جزئی CINE داخل MEDICINE ادغام می‌شود', () => {
  const a = mkPiece(1, 'MEDICINE', 247, 348, 0.96, 'gray_clahe');
  a.w = 418; a.h = 125;
  const b = mkPiece(2, 'CINE', 247, 575, 0.71, 'binarized');
  b.w = 190; b.h = 141;
  const pieces = pipe.mergePiecesBestFirst({ gray_clahe: [a], binarized: [b] });
  assertEq(pieces.map((p) => p.text), ['MEDICINE']);
});

test('mergePiecesBestFirst: DA با conf بالاتر متن BOX را بازنویسی نمی‌کند', () => {
  const box = mkPiece(1, 'BOX', 372, 499, 0.88, 'white_on_dark');
  box.w = 126; box.h = 65;
  const da = mkPiece(2, 'DA', 375, 576, 0.92, 'binarized');
  da.w = 50; da.h = 53;
  const pieces = pipe.mergePiecesBestFirst({ white_on_dark: [box], binarized: [da] });
  assertEq(pieces[0].text, 'BOX');
});

test('mergePiecesBestFirst: MEDICINES کم‌اطمینان با MEDICINE واقعی جانشین می‌شود', () => {
  const bad = mkPiece(1, 'MEDICINES', 189, 350, 0.42, 'white_on_dark');
  bad.w = 458; bad.h = 183;
  const good = mkPiece(2, 'MEDICINE', 247, 348, 0.96, 'gray_clahe');
  good.w = 418; good.h = 125;
  const pieces = pipe.mergePiecesBestFirst({ white_on_dark: [bad], gray_clahe: [good] });
  assertEq(pieces.map((p) => p.text), ['MEDICINE']);
});

test('sameRegion: کلمات همسایه با کادر همپوشان یکی نمی‌شوند', () => {
  const a = { x: 20, y: 30, w: 110, h: 24 };
  const b = { x: 140, y: 30, w: 80, h: 24 };
  assertEq(pipe.sameRegion(a, b, 'system(\'echo', 'hacked\')'), false);
});

test('assessQuality: عکس محصول روی میز روشن هشدار شستگی نمی‌گیرد', () => {
  // پس‌زمینه روشن + جعبه تیره = کنتراست بالا → نه bright
  const w = 60, h = 60;
  const gray = new Uint8ClampedArray(w * h).fill(215);
  for (let y = 15; y < 45; y++) for (let x = 15; x < 45; x++) gray[y * w + x] = 90;
  const issues = pipe.assessQuality(gray, w, h, SETTINGS).issues;
  assertEq(issues.some((i) => i.code === 'bright'), false);
});



// ---------------------------------------------------------------------------
// v2.10.0 — پاریتی با tests/test_dedupe_v210.py (F1 + F2)
// ---------------------------------------------------------------------------
function mkPieceV210(text, x, y, w, h, conf = 0.9, support = 1) {
  return { id: '', text, normalized_text: text, bbox: { x, y, w, h },
    confidence: conf, variant: 'original', engine: 'fake', support };
}

test('v2.10 pureNumber: «۵۰» عدد است، «mg» نیست', () => {
  assertEq(pipe.pureNumber('50'), true);
  assertEq(pipe.pureNumber('0.5'), true);
  assertEq(pipe.pureNumber('1,000'), true);
  assertEq(pipe.pureNumber('mg'), false);
});

test('v2.10 dedupeSimilarPieces: «50» با «500» ادغام نمی‌شود (بدون هندسه)', () => {
  const out = pipe.dedupeSimilarPieces([
    mkPieceV210('50', 20, 100, 40, 24, 0.9),
    mkPieceV210('500', 200, 100, 70, 24, 0.5)
  ]);
  const texts = new Set(out.map((p) => p.text));
  assert(texts.has('50') && texts.has('500'), JSON.stringify(texts));
});

test('v2.10 dedupeSimilarPieces: خوانش جزئی با احتوای کادر ادغام می‌شود', () => {
  const out = pipe.dedupeSimilarPieces([
    mkPieceV210('500', 20, 100, 70, 24, 0.7),
    mkPieceV210('50', 20, 100, 45, 20, 0.6)
  ]);
  assertEq(out.length, 1, JSON.stringify(out.map((p) => p.text)));
});

test('v2.10 collapseLocationDuplicates: دوقلوی سرگردان ادغام می‌شود', () => {
  const pieces = [
    mkPieceV210('Keeping', 100, 100, 70, 20, 0.88),
    mkPieceV210('Keeping', 174, 101, 68, 20, 0.72),
    mkPieceV210('Bones', 260, 100, 60, 20, 0.9)
  ];
  const removed = pipe.collapseLocationDuplicates(pieces, {});
  assertEq(removed, 1);
  assertEq(pieces.filter((p) => p.text === 'Keeping').length, 1);
  assert(pieces.some((p) => p.text === 'Bones'));
});

test('v2.10 collapseLocationDuplicates: تکرار واقعی با فاصلهٔ واژگانی می‌ماند', () => {
  const pieces = [
    mkPieceV210('Bones', 100, 100, 60, 20, 0.9, 2),
    mkPieceV210('Bones', 260, 100, 60, 20, 0.9, 2)
  ];
  const removed = pipe.collapseLocationDuplicates(pieces, {});
  assertEq(removed, 0);
  assertEq(pieces.length, 2);
});

test('v2.10 collapseLocationDuplicates: سطر نهایی واژهٔ تکراری ندارد', () => {
  const pieces = [
    mkPieceV210('Keeping', 100, 100, 70, 20, 0.88),
    mkPieceV210('Keeping', 174, 101, 68, 20, 0.72),
    mkPieceV210('Bones', 260, 100, 60, 20, 0.9),
    mkPieceV210('Strong', 330, 100, 62, 20, 0.85)
  ];
  pipe.collapseLocationDuplicates(pieces, {});
  pipe.assignIds(pieces);
  const lines = pipe.buildLines(pieces);
  assertEq(lines.length, 1);
  const words = lines[0].text.split(/\s+/);
  assertEq(JSON.stringify(words), JSON.stringify(['Keeping', 'Bones', 'Strong']));
});

// ---------- v2.11.0: آزمون پاریتی TTS (توکن Sec-MS-GEC v2 و ابزار متن) ----------
try {
  require('./tts_v2110.js');
  passed++;
} catch (e) {
  failed++;
  failures.push('tts_v2110: ' + (e && e.message ? e.message : e));
}

console.log('\nنتیجه: ' + passed + ' پاس، ' + failed + ' شکست');
if (failed) {
  console.log('\nجزئیات شکست‌ها:');
  failures.forEach((f) => console.log('  ✗ ' + f));
  process.exit(1);
}

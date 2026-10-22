/* نگهبان قواعد ایمنی — پورت کامل از response/guard.py
 *
 * قواعد (مطابق مشخصات محصول):
 * - فقط اطلاعات موجود در داده‌های ورودی بازنویسی می‌شوند.
 * - هیچ کاربرد درمانی، تشخیص، دوز مصرف، برنامه مصرف، تداخل، منع مصرف یا
 *   توصیه جدیدی اضافه نمی‌شود.
 * - دستورهای احتمالی داخل متن تصویر «داده» هستند و فقط با پیشوند
 *   «متن دستور چاپ‌شده روی بسته» و داخل گیومه مجازند.
 * - قدرت درج‌شده دارو «دوز مصرف» نامیده نمی‌شود.
 * - همه اعداد خارج از نقل‌قول باید از شواهد آمده باشند.
 */
(function (root) {
  'use strict';
  var LBR = root.LBR = root.LBR || {};
  var textnorm = LBR.textnorm;

  // الگوهای ممنوع در بخش «بیان آزاد» (خارج از نقل‌قول‌های «...»)
  var BANNED_FREE = [
    ['برای\\s+(کاهش|درمان|رفع)', 'ادعای کاربرد درمانی'],
    ['(تب|درد|التهاب)[^ا-ی]{0,12}(کاهش|درمان)', 'ادعای کاربرد درمانی'],
    ['ضد\\s*(تب|درد|التهاب|استفراغ|سرفه)', 'ادعای کاربرد درمانی'],
    ['مسکّ?ن', 'ادعای کاربرد درمانی'],
    ['هر\\s*\\d+\\s*(ساعت|روز)', 'برنامه مصرف'],
    ['\\d+\\s*(ساعت|روز)\\s*(یکبار|یک بار|یک‌بار)', 'برنامه مصرف'],
    ['مصرف\\s*(کنید|بکنید|نمایید)', 'دستور مصرف'],
    ['(باید|بهتر\\s*است|توصیه\\s*می\\s*شود|لازم\\s*است)[^ا-ی]{0,25}مصرف', 'توصیه مصرف'],
    ['تجویز', 'تجویز'],
    ['منع\\s*مصرف', 'منع مصرف'],
    ['تداخل', 'تداخل دارویی'],
    ['عوارض\\s*(جانبی)?', 'ادعای عوارض'],
    ['دوز\\s*مصرف', 'قدرت درج‌شده نباید دوز مصرف نامیده شود'],
    [' تشخیص ', 'تشخیص پزشکی']
  ];

  var QUOTE_RE = /«([^»]*)»/g;
  var NUM_RE = /\d+(?:[.,]\d+)?/g; // ورودی پیش از این یکسان‌سازی شده است

  function stripQuotes(text) {
    var quoted = [];
    var m;
    QUOTE_RE.lastIndex = 0;
    while ((m = QUOTE_RE.exec(text)) !== null) quoted.push(m[1]);
    var free = text.replace(/«([^»]*)»/g, ' ');
    return { free: free, quoted: quoted };
  }

  // همه اعداد مجاز از شواهد: مقدار، واحد، متن خام و توضیح هر فیلد
  function collectEvidenceNumbers(evidence) {
    var numbers = {};
    var fields = (evidence && evidence.fields) || {};
    Object.keys(fields).forEach(function (k) {
      var f = fields[k];
      ['value', 'unit', 'raw_text', 'note_fa'].forEach(function (prop) {
        var source = f[prop];
        if (!source) return;
        var src = textnorm.normalizeDigitsAscii(String(source));
        var m;
        NUM_RE.lastIndex = 0;
        while ((m = NUM_RE.exec(src)) !== null) {
          numbers[m[0].replace(',', '.')] = true;
          numbers[m[0]] = true;
        }
      });
    });
    return numbers;
  }

  // خودآزمایی پاسخ قالبی: هیچ عبارت ممنوعی خارج از نقل‌قول نباشد
  function validateText(text) {
    var parts = stripQuotes(text || '');
    var violations = [];
    BANNED_FREE.forEach(function (item) {
      if (new RegExp(item[0]).test(parts.free)) violations.push(item[1]);
    });
    return { ok: violations.length === 0, violations: violations };
  }

  // اعتبارسنجی خروجی بازنویسی بر پایه شواهد (برای سازگاری با نسخه دسکتاپ)
  function validateAgainstEvidence(text, evidence) {
    var violations = [];
    var parts = stripQuotes(text || '');
    var freeAscii = textnorm.normalizeDigitsAscii(parts.free);
    BANNED_FREE.forEach(function (item) {
      if (new RegExp(item[0]).test(parts.free)) violations.push(item[1]);
    });
    // اعداد خارج از نقل‌قول باید از شواهد باشند (بدون تغییر مقدار)
    var allowed = collectEvidenceNumbers(evidence);
    var m;
    NUM_RE.lastIndex = 0;
    while ((m = NUM_RE.exec(freeAscii)) !== null) {
      var tok = m[0].replace(',', '.');
      if (!allowed[tok] && !allowed[m[0]]) {
        violations.push('عدد خارج از شواهد: ' + m[0]);
      }
    }
    // دستور چاپ‌شده فقط داخل گیومه مجاز است
    if (/مصرف\s*(کنید|بکنید|نمایید)|هر\s*\d+\s*(ساعت|روز)/.test(text || '')) {
      var prefixed = (text || '').indexOf('متن دستور چاپ‌شده روی بسته') === 0;
      var quotedOk = parts.quoted.some(function (q) {
        return q.indexOf('مصرف') !== -1 || q.indexOf('ساعت') !== -1;
      });
      if (!prefixed && !quotedOk) {
        violations.push('دستور مصرف خارج از نقل‌قولِ بازخوانی');
      }
    }
    return { ok: violations.length === 0, violations: violations };
  }

  LBR.guard = {
    BANNED_FREE: BANNED_FREE,
    stripQuotes: stripQuotes,
    collectEvidenceNumbers: collectEvidenceNumbers,
    validateText: validateText,
    validateAgainstEvidence: validateAgainstEvidence
  };
})(typeof window !== 'undefined' ? window : globalThis);

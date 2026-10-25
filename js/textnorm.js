/* نرمال‌سازی متن فارسی/انگلیسی — پورت کامل از label_reader/textnorm.py
 *
 * مرزهای مهم (همان نسخه دسکتاپ):
 * - فقط اصلاح‌های نویسه‌ای مجاز است: «ي→ی»، «ك→ک»، یکسان‌سازی ارقام.
 * - نام دارو یا برند به‌صورت خودکار تصحیح نمی‌شود.
 * - ابهام‌های 0/O، 1/I و mg/mcg با حدس پنهان برطرف نمی‌شود.
 * - متن خام جدا نگه داشته می‌شود؛ این ماژول فقط برای «مطابقه» به کار می‌رود.
 */
(function (root) {
  'use strict';
  var LBR = root.LBR = root.LBR || {};

  // نگاشت نویسه‌های عربی به فارسی
  var CHAR_MAP = {
    '\u064a': '\u06cc', // ي -> ی
    '\u0649': '\u06cc', // ى -> ی
    '\u0643': '\u06a9', // ك -> ک
    '\u0629': '\u0647', // ة -> ه
    '\u0623': '\u0627', // أ -> ا
    '\u0625': '\u0627', // إ -> ا
    '\u0622': '\u0627', // آ -> ا (فقط برای مطابقه؛ نمایش خام جدا است)
    '\u0640': ''        // کشیده (tatweel) حذف
  };

  var PERSIAN_DIGITS = '\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9';
  var ARABIC_DIGITS = '\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669';

  var TO_ASCII = {};
  var i;
  for (i = 0; i < 10; i++) {
    TO_ASCII[PERSIAN_DIGITS[i]] = String(i);
    TO_ASCII[ARABIC_DIGITS[i]] = String(i);
  }
  var TO_PERSIAN = {};
  for (i = 0; i < 10; i++) TO_PERSIAN[String(i)] = PERSIAN_DIGITS[i];

  var ZWNJ = '\u200c', ZWJ = '\u200d', RLM = '\u200f', LRM = '\u200e';

  function translateChars(text, map) {
    var out = '';
    for (var k = 0; k < text.length; k++) {
      var ch = text[k];
      out += (Object.prototype.hasOwnProperty.call(map, ch) ? map[ch] : ch);
    }
    return out;
  }

  function normalizeChars(text) {
    if (!text) return text;
    return translateChars(text, CHAR_MAP);
  }

  function normalizeDigitsAscii(text) {
    if (!text) return text;
    return translateChars(text, TO_ASCII);
  }

  function digitsToPersian(text) {
    if (!text) return text;
    return translateChars(text, TO_PERSIAN);
  }

  function normalizeForMatching(text) {
    if (!text) return text;
    var t = String(text).normalize('NFC');
    t = normalizeChars(t);
    t = normalizeDigitsAscii(t);
    t = t.split(ZWNJ).join(' ').split(ZWJ).join(' ')
         .split(RLM).join(' ').split(LRM).join(' ');
    t = t.replace(/\s+/g, ' ');
    return t.trim();
  }

  function cleanedDisplayText(text) {
    if (!text) return text;
    var t = String(text).normalize('NFC');
    t = normalizeChars(t);
    t = t.split(ZWJ).join('').split(RLM).join(' ').split(LRM).join(' ');
    t = t.replace(/\s+/g, ' ');
    return t.trim();
  }

  var LATIN_RE = /[\u0000-\u024f]/;
  var PERSIAN_RE = /[\u0600-\u06ff]/;
  var LETTER_RE = /\p{L}/u;

  function isMostlyLatin(text) {
    var letters = 0, latin = 0, ch;
    for (var k = 0; k < text.length; k++) {
      ch = text[k];
      if (LETTER_RE.test(ch)) {
        letters++;
        if (LATIN_RE.test(ch)) latin++;
      }
    }
    if (!letters) return false;
    return latin / letters > 0.5;
  }

  function isMostlyPersian(text) {
    var letters = 0, fa = 0, ch;
    for (var k = 0; k < text.length; k++) {
      ch = text[k];
      if (LETTER_RE.test(ch)) {
        letters++;
        if (PERSIAN_RE.test(ch)) fa++;
      }
    }
    if (!letters) return false;
    return fa / letters > 0.5;
  }

  LBR.textnorm = {
    CHAR_MAP: CHAR_MAP,
    ZWNJ: ZWNJ,
    normalizeChars: normalizeChars,
    normalizeDigitsAscii: normalizeDigitsAscii,
    digitsToPersian: digitsToPersian,
    normalizeForMatching: normalizeForMatching,
    cleanedDisplayText: cleanedDisplayText,
    isMostlyLatin: isMostlyLatin,
    isMostlyPersian: isMostlyPersian
  };
})(typeof window !== 'undefined' ? window : globalThis);

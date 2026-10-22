/* تولید پاسخ فارسی قالبی — پورت کامل از response/builder.py
 *
 * مرزهای کلیدی:
 * - قدرت درج‌شده هرگز «دوز مصرف» نامیده نمی‌شود.
 * - هیچ کاربرد درمانی، توصیه یا برنامه مصرفی اضافه نمی‌شود.
 * - اطلاعات نامطمئن قطعی بیان نمی‌شوند.
 * - نام لاتین بدون تغییر حفظ می‌شود.
 */
(function (root) {
  'use strict';
  var LBR = root.LBR = root.LBR || {};
  var tn = LBR.textnorm;

  var NO_TEXT_RESPONSE_FA =
    'هیچ متن قابل خواندنی در این تصویر شناسایی نشد. ' +
    'لطفاً دوربین را ثابت نگه دارید، متن بسته را کامل در کادر قرار دهید، ' +
    'نور را بهتر کنید و از انعکاس نور جلوگیری کنید؛ سپس دوباره تلاش کنید.';

  var DISCLAIMER_FA =
    'این اطلاعات از متن قابل خواندن بسته استخراج شده‌اند و توصیه پزشکی ' +
    'یا تعیین مقدار مصرف نیستند.';

  var UNIT_FA = {
    'mg': 'میلی‌گرم', 'mcg': 'میکروگرم', 'g': 'گرم', 'mL': 'میلی‌لیتر',
    'L': 'لیتر', '%': 'درصد', 'IU': 'واحد بین‌المللی'
  };

  var COUNT_UNIT_FA = {
    'tablets': 'قرص', 'capsules': 'کپسول', 'suppositories': 'شیاف',
    'sachets': 'ساشه', 'vials': 'ویال', 'ampoules': 'آمپول', 'drops': 'قطره',
    'قرص': 'قرص', 'کپسول': 'کپسول', 'عدد': 'عدد', 'ساشه': 'ساشه',
    'ویال': 'ویال', 'آمپول': 'آمپول', 'شیاف': 'شیاف', 'قطره': 'قطره'
  };

  function isPresent(field) {
    return ['extracted', 'uncertain', 'conflicting', 'user_corrected']
      .indexOf(field.status) !== -1 && !!field.value;
  }

  // قدرت درج‌شده؛ تفاوت «۵۰۰ میلی‌گرم» و «۲۵۰ میلی‌گرم در ۵ میلی‌لیتر» حفظ می‌شود
  function formatStrength(field) {
    var v = (field.value || '').trim();
    if (field.unit) {
      return tn.digitsToPersian(v) + ' ' + (UNIT_FA[field.unit] || field.unit);
    }
    var parts = v.split(/\s+/);
    if ((parts.length === 4 && parts[1] === '/') ||
      v.indexOf(' / ') !== -1 ||
      (v.indexOf('/') !== -1 && v.indexOf(' ') !== -1)) {
      // قالب "250 mg/5 mL"
      try {
        var num1 = parts[0];
        var unit1 = parts[1].split('/')[0];
        var rest = v.split('/', 2)[1].trim();
        var restParts = rest.split(/\s+/);
        var num2 = restParts[0], unit2 = restParts[1];
        return tn.digitsToPersian(num1) + ' ' + (UNIT_FA[unit1] || unit1) +
          ' در ' + tn.digitsToPersian(num2) + ' ' + (UNIT_FA[unit2] || unit2);
      } catch (e) { /* قالب پیش‌بینی‌نشده → مقدار خام */ }
    }
    return tn.digitsToPersian(v);
  }

  function formatCount(field) {
    var unit = COUNT_UNIT_FA[field.unit || ''] || field.unit || '';
    return (tn.digitsToPersian(field.value) + ' ' + unit).trim();
  }

  function formatValue(field) {
    return tn.digitsToPersian(field.value || '');
  }

  function fieldSentence(field) {
    if (!isPresent(field)) return null;
    var label = field.label_fa;
    var display;
    if (field.key === 'strength') display = formatStrength(field);
    else if (field.key === 'count') display = formatCount(field);
    else if (field.key === 'name') display = field.value; // نام لاتین حفظ می‌شود
    else if (field.key === 'active_ingredient') display = field.value;
    else display = formatValue(field);

    if (field.status === 'conflicting') {
      return (label + ': دو یا چند مقدار متفاوت خوانده شد و مقدار قطعی اعلام ' +
        'نمی‌شود (' + display + ' یکی از خوانش‌ها است). ' + (field.note_fa || '')).trim();
    }
    if (field.status === 'uncertain') {
      if (['strength', 'count', 'expiry_date', 'production_date'].indexOf(field.key) !== -1) {
        return label + ': مقدار به‌طور واضح خوانده نشد؛ خوانش احتمالی «' + display +
          '» است و به‌عنوان مقدار قطعی خوانده نمی‌شود.';
      }
      return label + ': «' + display + '» (با اطمینان پایین OCR).';
    }
    if (field.status === 'user_corrected') {
      return label + ': ' + display + ' (اصلاح‌شده توسط شما).';
    }
    if (field.key === 'name') return label + ': ' + display + '.';
    if (['storage', 'warnings', 'ingredients', 'manufacturer', 'printed_directives']
      .indexOf(field.key) !== -1) {
      return label + ': «' + display + '».';
    }
    return label + ': ' + display + '.';
  }

  function qualitySentence(issues) {
    var severe = (issues || []).filter(function (i) {
      return (i.severity === 'warning' || i.severity === 'severe') && i.code !== 'ok';
    });
    if (!severe.length) return null;
    var msgs = severe.map(function (i) { return i.message_fa; }).join(' ');
    return 'هشدار کیفیت تصویر: ' + msgs;
  }

  // پاسخ فارسی قالبی وفادار به شواهد
  function buildResponse(fields, qualityIssues, extractionWarnings, ocrPieceCount) {
    if (ocrPieceCount === 0) return NO_TEXT_RESPONSE_FA;

    var fieldList = Object.keys(fields).map(function (k) { return fields[k]; });
    var presentAny = fieldList.some(isPresent);
    if (!presentAny) {
      return NO_TEXT_RESPONSE_FA.split('، سپس')[0] + '. ' + DISCLAIMER_FA;
    }

    var sentences = [];
    var q = qualitySentence(qualityIssues);
    if (q) sentences.push(q);

    var order = ['name', 'active_ingredient', 'strength', 'count', 'dosage_form',
      'net_weight', 'ingredients', 'manufacturer', 'batch',
      'production_date', 'expiry_date', 'storage', 'warnings'];
    order.forEach(function (key) {
      var f = fields[key];
      if (!f) return;
      if (key === 'storage' && !isPresent(f)) return;
      var s = fieldSentence(f);
      if (s) sentences.push(s);
    });

    var directives = fields.printed_directives;
    if (directives && isPresent(directives)) {
      sentences.push('متن دستور چاپ‌شده روی بسته: «' + directives.value +
        '». این صرفاً بازخوانی متن چاپ‌شده است و توصیه شخصی به شما نیست.');
    }

    (extractionWarnings || []).forEach(function (w) { sentences.push(w); });

    var missingKeysNote = [];
    ['strength', 'count'].forEach(function (key) {
      var f = fields[key];
      if (f && f.status === 'missing') missingKeysNote.push(f.label_fa);
    });
    if (missingKeysNote.length && ocrPieceCount > 0) {
      sentences.push('برای ' + missingKeysNote.join(' و ') +
        ' مقدار واضحی روی برچسب خوانده نشد؛ مقدار غایب از هیچ منبع دیگری تکمیل نمی‌شود.');
    }

    sentences.push(DISCLAIMER_FA);
    return sentences.join(' ');
  }

  LBR.responder = {
    NO_TEXT_RESPONSE_FA: NO_TEXT_RESPONSE_FA,
    DISCLAIMER_FA: DISCLAIMER_FA,
    isPresent: isPresent,
    formatStrength: formatStrength,
    formatCount: formatCount,
    buildResponse: buildResponse
  };
})(typeof window !== 'undefined' ? window : globalThis);

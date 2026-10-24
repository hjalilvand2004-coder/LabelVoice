/* الگوهای قابل آزمون استخراج فیلدها — پورت کامل از extraction/patterns.py
 *
 * همه الگوها روی «متن نرمال‌شده برای مطابقه» اجرا می‌شوند (ارقام لاتین،
 * ي/ی و ك/ک یکسان، نیم‌فاصله به فاصله). هیچ حدسی برای رفع ابهام
 * 0/O، 1/I یا mg/mcg زده نمی‌شود.
 */
(function (root) {
  'use strict';
  var LBR = root.LBR = root.LBR || {};

  var RE_NUM = '\\d+(?:[.,]\\d+)?';

  // واحدها: لاتین + فارسی (بعد از نرمال‌سازی، نیم‌فاصله فاصله است)
  var UNIT_TOKENS = [
    'mg\\.', 'mg', 'mcg', 'µg', 'μg', 'ug', 'ml', 'iu', 'g', 'l', '%',
    'میلی گرم', 'میل گرم', 'میکروگرم', 'میکرو گرم', 'گرم', 'میلی لیتر',
    'درصد'
  ];

  function escapeRe(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }
  var UNIT_ALT = UNIT_TOKENS.map(function (u) {
    return (u === '%') ? '%' : escapeRe(u);
  }).join('|');
  var UNIT_GROUP = '(?<' + 'unit>' + UNIT_ALT + ')';

  // الگوی قدرت؛ نسخه ترکیبی مثل 250 mg/5 mL هم پوشش داده می‌شود
  var RE_STRENGTH = new RegExp(
    '(?<' + 'num>' + RE_NUM + ')\\s*' + UNIT_GROUP +
    '(?:\\s*/\\s*(?<' + 'num2>' + RE_NUM + ')\\s*(?<' + 'unit2>' + UNIT_ALT + '))?(?![A-Za-z])',
    'i');

  var RE_COUNT = new RegExp(
    '(?<' + 'num>\\d+)\\s*(?<' + 'noun>tablets?|tabs|capsules?|caps|suppositor\\w*|' +
    'sachets?|vials?|ampoules?|amps?|drops|قرص|کپسول|عدد|ساشه|ویال|آمپول|شیاف|قطره)',
    'i');

  var RE_COUNT_REV = new RegExp(
    '(?<' + 'noun>قرص|کپسول|ساشه|ویال|آمپول|شیاف|قطره|عدد)\\s*(?<' + 'num>\\d+)',
    'i');

  var RE_DATE_VALUE = new RegExp(
    '(?<!\\d)(?<' + 'd1>\\d{1,4})[/\\-.](?<' + 'd2>\\d{1,2})(?:[/\\-.](?<' + 'd3>\\d{2,4}))?(?!\\d)');

  var RE_YEAR_ONLY = /(?<![\d/])(\d{4})(?![\d/])/;

  var RE_EXPIRY_LABEL = new RegExp(
    'exp(?:iry)?\\.?(?:\\s*date)?|best\\s*before|use\\s*by|see\\s*(?:base|bottle)|' +
    'تاریخ\\s*انقضا|انقضا|سرسید', 'i');

  var RE_PRODUCTION_LABEL = new RegExp(
    'mfg|mfd|m\\.?f\\.?g|man(?:ufactur\\w*)?|prod(?:uction|\\.)?|' +
    'تاریخ\\s*تولید|تولید', 'i');

  var RE_BATCH_LABEL = new RegExp(
    'batch|lot(?:\\s*no)?|b\\.?no\\.?|b/n|ch\\.?/?b|سری\\s*ساخت|شماره\\s*سری|سری',
    'i');

  var RE_BATCH_VALUE = /(?<val>[A-Za-z0-9][A-Za-z0-9/\-.]{2,24})/;

  var RE_WARNING_KEYWORD = new RegExp(
    'دور از دسترس|کودکان|طبق دستور پزشک|باردار|شیرده|احتیاط|keep\\s*out\\s*of\\s*reach|' +
    'keep\\s+away\\s+from\\s+children|out\\s+of\\s+the\\s+reach|warning|caution',
    'i');

  // دستورهای چاپ‌شده روی بسته (فقط به‌عنوان «متن چاپ‌شده» بازخوانی می‌شوند)
  var RE_DIRECTIVE_KEYWORD = new RegExp(
    'مصرف کنید|خورده شود|هر\\s*\\d+\\s*(ساعت|روز)|روزانه\\s*\\d+|\\d+\\s*بار\\s*(در|در)\\s*روز|' +
    'بعد\\s*از\\s*غذا|قبل\\s*از\\s*غذا|با\\s*آب|take\\s+\\d+|every\\s+\\d+\\s*(hours?|days?)|' +
    'daily|orally|after\\s+meal|before\\s+meal|with\\s+water|with\\s+food',
    'i');

  var RE_INGREDIENT_KEYWORD = new RegExp(
    'ماده\\s*م[وؤ]ثره|م[وؤ]ثره|ترکیب|حاوی|active\\s+ingredient|contains|composition',
    'i');

  var RE_MANUFACTURER_KEYWORD = new RegExp(
    'company|corporation|\\bcorp\\b|\\bco\\.|pharma\\w*|laborator\\w*|industr\\w*|' +
    'gmbh|ltd|\\binc\\b|' +
    'شرکت|داروسازی|سازنده|تولید\\s*کننده|تولیدکننده',
    'i');

  var RE_STORAGE_KEYWORD = new RegExp(
    'نگهداری|دمای\\s*اتاق|دور\\s*از\\s*نور|یخچال|store|storage|keep\\s+below|' +
    'below\\s+\\d+\\s*°?c|protect\\s+from\\s+light',
    'i');

  var RE_DOSAGE_FORM = new RegExp(
    'tablets?|tabs|capsules?|caps|syrup|suspension|solution|injection|cream|' +
    'ointment|drops|suppositor\\w*|sachet|vial|ampoule|قرص|کپسول|شربت|سوسپانسیون|' +
    'محلول|آمپول|کرم|پماد|قطره|شیاف|ساشه',
    'i');

  var RE_NET_WEIGHT_KEYWORD = new RegExp(
    'net\\s*(?:wt|weight)|وزن\\s*خالص|حجم\\s*خالص|خالص|bottle|tube', 'i');

  // نقشه یکسان‌سازی املا واحد برای نگهداشت بدون تغییر معنایی
  var UNIT_CANONICAL = {
    'mg.': 'mg', 'mg': 'mg', 'میلی گرم': 'mg', 'میل گرم': 'mg',
    'mcg': 'mcg', 'µg': 'mcg', 'μg': 'mcg', 'ug': 'mcg',
    'میکروگرم': 'mcg', 'میکرو گرم': 'mcg',
    'g': 'g', 'گرم': 'g',
    'ml': 'mL', 'میلی لیتر': 'mL',
    'l': 'L',
    '%': '%', 'درصد': '%',
    'iu': 'IU'
  };

  var COUNT_NOUN_CANONICAL = {
    'tablet': 'tablets', 'tablets': 'tablets', 'tabs': 'tablets',
    'capsule': 'capsules', 'capsules': 'capsules', 'caps': 'capsules',
    'suppositories': 'suppositories', 'suppository': 'suppositories',
    'sachet': 'sachets', 'sachets': 'sachets',
    'vial': 'vials', 'vials': 'vials',
    'ampoule': 'ampoules', 'ampoules': 'ampoules', 'amps': 'ampoules',
    'drop': 'drops', 'drops': 'drops',
    'قرص': 'قرص', 'کپسول': 'کپسول', 'عدد': 'عدد', 'ساشه': 'ساشه',
    'ویال': 'ویال', 'آمپول': 'آمپول', 'شیاف': 'شیاف', 'قطره': 'قطره'
  };

  var DOSAGE_FORM_FA = {
    'tablets': 'قرص', 'tablets.': 'قرص', 'capsules': 'کپسول', 'syrup': 'شربت',
    'suspension': 'سوسپانسیون', 'solution': 'محلول', 'injection': 'تزریقی',
    'cream': 'کرم', 'ointment': 'پماد', 'drops': 'قطره',
    'suppositories': 'شیاف', 'sachet': 'ساشه', 'vial': 'ویال',
    'ampoule': 'آمپول', 'قرص': 'قرص', 'کپسول': 'کپسول', 'شربت': 'شربت',
    'سوسپانسیون': 'سوسپانسیون', 'محلول': 'محلول', 'آمپول': 'آمپول',
    'کرم': 'کرم', 'پماد': 'پماد', 'قطره': 'قطره', 'شیاف': 'شیاف',
    'ساشه': 'ساشه'
  };

  function matchAll(re, text) {
    var out = [];
    var g = new RegExp(re.source, re.flags.includes('g') ? re.flags : re.flags + 'g');
    var m;
    while ((m = g.exec(text)) !== null) {
      out.push(m);
      if (m.index === g.lastIndex) g.lastIndex++;
    }
    return out;
  }

  function searchAt(re, text, fromIndex) {
    if (fromIndex > 0) {
      var sub = text.slice(fromIndex);
      var m = re.exec(sub);
      if (m) {
        m.index = fromIndex + m.index;
        return m;
      }
      return null;
    }
    return re.exec(text);
  }

  // بازگشت {value, ambiguous} — تاریخ مبهم بدون شواهد قطعی نمی‌شود
  function inferDateAmbiguity(d1, d2, d3) {
    if (d1.length === 4) { // YYYY/…
      var val = d1 + '/' + d2 + (d3 ? '/' + d3 : '');
      return { value: val, ambiguous: false };
    }
    if (d3 !== undefined && d3 !== null) { // DD/MM/YYYY یا MM/DD/YYYY → ترتیب قطعی نیست
      return { value: d1 + '/' + d2 + '/' + d3, ambiguous: true };
    }
    // دو قطعه بدون سال چهاررقمی: مبهم (سال دو رقمی یا ماه/روز)
    return { value: d1 + '/' + d2, ambiguous: true };
  }

  LBR.patterns = {
    RE_NUM: RE_NUM,
    RE_STRENGTH: RE_STRENGTH,
    RE_COUNT: RE_COUNT,
    RE_COUNT_REV: RE_COUNT_REV,
    RE_DATE_VALUE: RE_DATE_VALUE,
    RE_YEAR_ONLY: RE_YEAR_ONLY,
    RE_EXPIRY_LABEL: RE_EXPIRY_LABEL,
    RE_PRODUCTION_LABEL: RE_PRODUCTION_LABEL,
    RE_BATCH_LABEL: RE_BATCH_LABEL,
    RE_BATCH_VALUE: RE_BATCH_VALUE,
    RE_WARNING_KEYWORD: RE_WARNING_KEYWORD,
    RE_DIRECTIVE_KEYWORD: RE_DIRECTIVE_KEYWORD,
    RE_INGREDIENT_KEYWORD: RE_INGREDIENT_KEYWORD,
    RE_MANUFACTURER_KEYWORD: RE_MANUFACTURER_KEYWORD,
    RE_STORAGE_KEYWORD: RE_STORAGE_KEYWORD,
    RE_DOSAGE_FORM: RE_DOSAGE_FORM,
    RE_NET_WEIGHT_KEYWORD: RE_NET_WEIGHT_KEYWORD,
    UNIT_CANONICAL: UNIT_CANONICAL,
    COUNT_NOUN_CANONICAL: COUNT_NOUN_CANONICAL,
    DOSAGE_FORM_FA: DOSAGE_FORM_FA,
    matchAll: matchAll,
    searchAt: searchAt,
    inferDateAmbiguity: inferDateAmbiguity
  };
})(typeof window !== 'undefined' ? window : globalThis);

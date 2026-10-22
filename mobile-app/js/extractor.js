/* استخراج فیلدهای ساختاریافته از سطرهای OCR — پورت کامل از extraction/*
 *
 * قواعد حیاتی (همان نسخه دسکتاپ):
 * - نبود فیلد → null (status=missing)؛ اطلاعات غایب تکمیل نمی‌شود.
 * - هر فیلد به شناسه قطعه‌های OCR (source_ids) متصل است.
 * - قدرت دارو از برنامه مصرف جدا نگه داشته می‌شود و «دوز مصرف» نامیده نمی‌شود.
 * - فیلدهای متناقض علامت‌گذاری می‌شوند، نه اینکه یکی بی‌دلیل انتخاب شود.
 */
(function (root) {
  'use strict';
  var LBR = root.LBR = root.LBR || {};
  var tn = LBR.textnorm;
  var P = LBR.patterns;

  var FIELD_LABELS_FA = {
    name: 'نام درج‌شده روی بسته',
    active_ingredient: 'ماده مؤثره درج‌شده',
    strength: 'قدرت درج‌شده',
    dosage_form: 'شکل دارویی درج‌شده',
    count: 'تعداد درج‌شده',
    net_weight: 'وزن یا حجم خالص',
    ingredients: 'ترکیبات درج‌شده',
    manufacturer: 'سازنده درج‌شده',
    batch: 'شماره سری ساخت',
    production_date: 'تاریخ تولید',
    expiry_date: 'تاریخ انقضا',
    storage: 'شرایط نگهداری',
    warnings: 'هشدارهای چاپ‌شده روی بسته',
    printed_directives: 'متن دستور چاپ‌شده روی بسته'
  };

  var MEDICINE_KEYS = ['name', 'active_ingredient', 'strength', 'dosage_form',
    'count', 'manufacturer', 'batch', 'production_date', 'expiry_date',
    'storage', 'warnings', 'printed_directives'];
  var GENERAL_KEYS = ['name', 'net_weight', 'count', 'ingredients', 'manufacturer',
    'production_date', 'expiry_date', 'storage', 'warnings',
    'printed_directives'];

  var ALPHA_MIN = 3;

  // ---------- طبقه‌بندی نوع بسته ----------
  var MEDICINE_KEYWORDS = [
    'قرص', 'کپسول', 'میلی گرم', 'میکروگرم', 'دارو', 'ماده موثره', 'موثره',
    'شربت', 'سوسپانسیون', 'آمپول', 'ویال', 'شیاف', 'قطره چشم', 'ساشه دارویی',
    'tablets', 'tablet', 'capsules', 'capsule', 'syrup', 'suspension',
    'injection', 'suppository', 'ointment', 'active ingredient', 'dose',
    'medicine', 'pharmaceutical'
  ];
  // نشانه‌های قوی دارویی با مرز واژه (mg در وسط کلمات دیگر نیست)
  var MEDICINE_STRONG_RE = /\bmg\b|\bmcg\b|\btablets?\b|\bcapsules?\b|\bml\b/i;

  var GENERAL_KEYWORDS = [
    'وزن خالص', 'حجم خالص', 'خالص', 'ترکیبات', 'مواد تشکیل دهنده', 'محصول',
    'net wt', 'net weight', 'ingredients', 'product', 'biscuit', 'chocolate',
    'شامپو', 'صابون', 'کیک', 'بیسکویت', 'شکلات', 'نوشیدنی', 'juice', 'shampoo'
  ];

  // طبقه‌بندی فقط برای انتخاب قالب فیلد است؛ تأیید هویت/اصالت محصول نیست
  function classifyProductType(linesText) {
    var joined = linesText.join(' | ');
    var medicineHits = 0;
    MEDICINE_KEYWORDS.forEach(function (kw) { if (joined.indexOf(kw) !== -1) medicineHits++; });
    if (MEDICINE_STRONG_RE.test(joined)) medicineHits += 2;
    var generalHits = 0;
    GENERAL_KEYWORDS.forEach(function (kw) { if (joined.indexOf(kw) !== -1) generalHits++; });

    if (medicineHits >= 2 && medicineHits >= generalHits) {
      return {
        type: 'medicine',
        note: 'بر اساس واژه‌های دارویی روی برچسب (قرص، میلی‌گرم و مانند آن).'
      };
    }
    if (generalHits >= 2 && generalHits > medicineHits) {
      return {
        type: 'general_product',
        note: 'بر اساس واژه‌های محصول عمومی روی برچسب (وزن خالص، ترکیبات و مانند آن).'
      };
    }
    return {
      type: 'unknown',
      note: 'نشانه کافی برای طبقه‌بندی یافت نشد؛ قالب عمومی استفاده می‌شود.'
    };
  }

  // ---------- ابزارهای مشترک ----------
  function hasAlpha(text) {
    var n = 0;
    for (var k = 0; k < text.length; k++) {
      if (/\p{L}/u.test(text[k])) n++;
    }
    return n >= ALPHA_MIN;
  }

  function mkRecord(key, status, opts) {
    opts = opts || {};
    return {
      key: key,
      label_fa: FIELD_LABELS_FA[key],
      value: opts.value !== undefined ? opts.value : null,
      unit: opts.unit !== undefined ? opts.unit : null,
      raw_text: opts.raw_text !== undefined ? opts.raw_text : null,
      source_ids: opts.source_ids || [],
      confidence: opts.confidence !== undefined ? opts.confidence : null,
      status: status,
      previous_values: [],
      note_fa: opts.note_fa !== undefined ? opts.note_fa : null
    };
  }

  function missing(key) { return mkRecord(key, 'missing'); }

  function confOf(line) {
    return (line.confidence_mean === null || line.confidence_mean === undefined)
      ? 0.5 : line.confidence_mean;
  }

  // ---------- حل جمع نامزدها با سیاست محافظه‌کارانه ----------
  // بازگشت: {best, status, distinct} — وضعیت: missing|extracted|uncertain|conflicting
  function resolveCandidates(candidates, lowConfidenceThreshold) {
    if (!candidates.length) return { best: null, status: 'missing', distinct: [] };
    var distinct = [];
    var seen = {};
    var sorted = candidates.slice().sort(function (a, b) {
      var ca = (a.confidence === null || a.confidence === undefined) ? 0.5 : a.confidence;
      var cb = (b.confidence === null || b.confidence === undefined) ? 0.5 : b.confidence;
      return cb - ca;
    });
    sorted.forEach(function (c) {
      var key = c.value_norm + '\u0000' + (c.unit || '');
      if (!seen[key]) {
        seen[key] = true;
        distinct.push(c);
      }
    });
    if (distinct.length > 1) {
      return {
        best: distinct[0],
        status: 'conflicting',
        distinct: distinct.map(function (c) { return c.value_norm; })
      };
    }
    var best = distinct[0];
    var conf = (best.confidence === null || best.confidence === undefined) ? 0.5 : best.confidence;
    if (conf < lowConfidenceThreshold) {
      return { best: best, status: 'uncertain', distinct: [best.value_norm] };
    }
    return { best: best, status: 'extracted', distinct: [best.value_norm] };
  }

  function textCandidateFromStrength(match, line, idx) {
    var unitToken = match.groups.unit.toLowerCase().replace(/\.$/, '');
    var unit = P.UNIT_CANONICAL[unitToken];
    if (unit === undefined) return null;
    var num = match.groups.num;
    if (match.groups.num2 !== undefined) {
      var unit2Token = match.groups.unit2.toLowerCase().replace(/\.$/, '');
      var unit2 = P.UNIT_CANONICAL[unit2Token];
      var value = num + ' ' + unit + '/' + match.groups.num2 + ' ' + unit2;
      return {
        value_norm: value, unit: null, raw_text: match[0],
        source_ids: line.source_ids.slice(),
        confidence: confOf(line), line_index: idx,
        x: line.bbox.x, y: line.bbox.y
      };
    }
    return {
      value_norm: num, unit: unit, raw_text: match[0],
      source_ids: line.source_ids.slice(),
      confidence: confOf(line), line_index: idx,
      x: line.bbox.x, y: line.bbox.y
    };
  }

  function countCandidate(match, line, idx) {
    var noun = P.COUNT_NOUN_CANONICAL[match.groups.noun.toLowerCase()] || match.groups.noun;
    return {
      value_norm: match.groups.num, unit: noun, raw_text: match[0],
      source_ids: line.source_ids.slice(),
      confidence: confOf(line), line_index: idx,
      x: line.bbox.x, y: line.bbox.y
    };
  }

  function dateCandidate(value, ambiguous, raw, line, idx, extraLine) {
    var ids = line.source_ids.slice();
    if (extraLine) ids = ids.concat(extraLine.source_ids.slice());
    var conf = extraLine ? Math.min(confOf(line), confOf(extraLine)) : confOf(line);
    return {
      value_norm: value + (ambiguous ? '?' : ''), unit: null, raw_text: raw,
      source_ids: ids, confidence: conf, line_index: idx,
      x: line.bbox.x, y: line.bbox.y
    };
  }

  function findLabeledDate(lines, labelRe) {
    var out = [];
    lines.forEach(function (line, idx) {
      var lm = labelRe.exec(line.normalized_text);
      if (!lm) return;
      var after = line.normalized_text.slice(lm.index + lm[0].length);
      var vm = P.RE_DATE_VALUE.exec(after) || P.RE_DATE_VALUE.exec(line.normalized_text);
      if (vm) {
        var inf = P.inferDateAmbiguity(vm.groups.d1, vm.groups.d2, vm.groups.d3);
        out.push(dateCandidate(inf.value, inf.ambiguous, vm[0], line, idx, null));
        return;
      }
      // سال تنها (مثل EXP: 2027) — مبهم تلقی می‌شود
      var remainder = line.normalized_text.slice(lm.index + lm[0].length);
      var ym = P.RE_YEAR_ONLY.exec(remainder) || P.RE_YEAR_ONLY.exec(line.normalized_text);
      if (ym) {
        out.push(dateCandidate(ym[1], true, ym[1], line, idx, null));
        return;
      }
      // برچسب در یک سطر و مقدار در سطر بعدی
      if (idx + 1 < lines.length) {
        var nxt = lines[idx + 1];
        var vm2 = P.RE_DATE_VALUE.exec(nxt.normalized_text);
        if (vm2 && vm2.groups.d1.length >= 2) {
          var inf2 = P.inferDateAmbiguity(vm2.groups.d1, vm2.groups.d2, vm2.groups.d3);
          out.push(dateCandidate(inf2.value, inf2.ambiguous, vm2[0], line, idx, nxt));
        }
      }
    });
    return out;
  }

  // بازگشت: [رکورد فیلد, مجموعه شاخص سطرهای مصرف‌شده]
  function freeTextField(key, lines, keywordRe, settings) {
    var hits = [];
    lines.forEach(function (ln, i) {
      if (keywordRe.test(ln.normalized_text)) hits.push(i);
    });
    keywordRe.lastIndex = 0;
    if (!hits.length) return [missing(key), new Set()];
    var seen = {};
    var values = [], sourceIds = [], confs = [];
    hits.slice().sort(function (a, b) {
      return (lines[a].bbox.y - lines[b].bbox.y) || (lines[a].bbox.x - lines[b].bbox.x);
    }).forEach(function (i) {
      var val = tn.cleanedDisplayText(lines[i].text);
      if (val && !seen[val]) {
        seen[val] = true;
        values.push(val);
        sourceIds = sourceIds.concat(lines[i].source_ids);
        confs.push(confOf(lines[i]));
      }
    });
    var conf = Math.min.apply(null, confs);
    var status = conf >= settings.low_confidence_threshold ? 'extracted' : 'uncertain';
    var note = (key === 'printed_directives')
      ? 'این متن عیناً از برچسب بازخوانی شده است.' : null;
    return [mkRecord(key, status, {
      value: values.join('؛ '), unit: null,
      raw_text: values.join(' / '), source_ids: sourceIds,
      confidence: Math.round(conf * 100) / 100, note_fa: note
    }), new Set(hits)];
  }

  function nameCandidates(consumed, lines) {
    var out = [];
    lines.forEach(function (line, idx) {
      if (consumed.has(idx) || !hasAlpha(line.normalized_text)) return;
      if (line.normalized_text.length > 80) return;
      out.push(idx);
    });
    out.sort(function (a, b) {
      return (lines[a].bbox.y - lines[b].bbox.y) || (lines[a].bbox.x - lines[b].bbox.x);
    });
    return out;
  }

  function dateRecord(key, cands, settings) {
    var res = resolveCandidates(cands, settings.low_confidence_threshold);
    if (!res.best) return missing(key);
    var best = res.best;
    var ambiguous = best.value_norm.slice(-1) === '?';
    var value = best.value_norm.replace(/\?+$/, '');
    if (res.status === 'conflicting') {
      return mkRecord(key, 'conflicting', {
        value: value, unit: null, raw_text: best.raw_text,
        source_ids: best.source_ids, confidence: best.confidence,
        note_fa: 'تاریخ‌های متفاوتی خوانده شد: ' + res.distinct.join('، ') + '.'
      });
    }
    if (ambiguous) {
      return mkRecord(key, 'uncertain', {
        value: value, unit: null, raw_text: best.raw_text,
        source_ids: best.source_ids, confidence: best.confidence,
        note_fa: 'تاریخ به‌صورت مبهم درج شده است (سال یا ترتیب روز/ماه قطعی نیست) ' +
          'و بدون شواهد به تاریخ قطعی تبدیل نشد.'
      });
    }
    var statusEnum = res.status === 'extracted' ? 'extracted' : 'uncertain';
    return mkRecord(key, statusEnum, {
      value: value, unit: null, raw_text: best.raw_text,
      source_ids: best.source_ids, confidence: best.confidence,
      note_fa: statusEnum === 'uncertain' ? 'اطمینان OCR پایین است.' : null
    });
  }

  // ---------- استخراج اصلی ----------
  // بازگشت: {fields, warnings} — fields: دیکشنری فیلدها به ترتیب قالب محصول
  function extractFields(lines, productType, settings, imageHeight) {
    var extractionWarnings = [];
    var consumed = new Set();

    var strengthCands = [], countCands = [];
    lines.forEach(function (line, idx) {
      var text = line.normalized_text;
      P.matchAll(P.RE_STRENGTH, text).forEach(function (m) {
        var cand = textCandidateFromStrength(m, line, idx);
        if (!cand) return;
        // «۱۰۰ mL» تنها (حجم بطری) قدرت دارو نیست؛ تنزیل می‌شود تا
        // با قدرت واقعی مثل «250 mg/5 mL» تناقض نسازد.
        if (cand.unit === 'mL' && cand.value_norm.indexOf(' ') === -1) {
          cand.confidence = (cand.confidence === null || cand.confidence === undefined
            ? 0.5 : cand.confidence) * 0.35;
        }
        strengthCands.push(cand);
        consumed.add(idx);
      });
      P.matchAll(P.RE_COUNT, text).forEach(function (m) {
        countCands.push(countCandidate(m, line, idx));
        consumed.add(idx);
      });
      P.matchAll(P.RE_COUNT_REV, text).forEach(function (m) {
        countCands.push(countCandidate(m, line, idx));
        consumed.add(idx);
      });
    });

    // وقتی کاندید حاوی mg وجود دارد، کاندیدهای mL تنها (حجم بطری) حذف می‌شوند
    var hasMgCandidate = strengthCands.some(function (c) {
      return c.unit === 'mg' || c.value_norm.indexOf('mg') !== -1;
    });
    if (hasMgCandidate) {
      strengthCands = strengthCands.filter(function (c) {
        return !(c.unit === 'mL' && c.value_norm.indexOf(' ') === -1);
      });
    }
    // محصول عمومی: «گرم/درصد» بدون هیچ mg/mcg، وزن خالص است نه قدرت دارو
    if (productType === 'general_product' && !hasMgCandidate) strengthCands = [];

    var expiryCands = findLabeledDate(lines, P.RE_EXPIRY_LABEL);
    var prodCands = findLabeledDate(lines, P.RE_PRODUCTION_LABEL);
    expiryCands.concat(prodCands).forEach(function (c) { consumed.add(c.line_index); });

    var batchCands = [];
    lines.forEach(function (line, idx) {
      var m = P.RE_BATCH_LABEL.exec(line.normalized_text);
      P.RE_BATCH_LABEL.lastIndex = 0;
      if (!m) return;
      var vm = P.RE_BATCH_VALUE.exec(line.normalized_text.slice(m.index + m[0].length));
      if (!vm) return;
      consumed.add(idx);
      batchCands.push({
        value_norm: vm.groups.val, unit: null, raw_text: vm[0],
        source_ids: line.source_ids.slice(), confidence: confOf(line),
        line_index: idx, x: line.bbox.x, y: line.bbox.y
      });
    });

    function resolveField(key, cands) {
      var res = resolveCandidates(cands, settings.low_confidence_threshold);
      if (!res.best) return missing(key);
      var best = res.best;
      // محافظ خوانش ناقص عدد: «۰» برای قدرت/تعداد معنادار نیست و
      // احتمالاً نتیجه ناخوانایی بخشی از رقم است (مثل ۵۰۰ → ۰).
      if ((key === 'strength' || key === 'count') && best.value_norm) {
        var numVal = parseFloat(best.value_norm.replace(',', '.'));
        if (!isNaN(numVal) && numVal === 0.0) {
          return mkRecord(key, 'uncertain', {
            value: best.value_norm, unit: best.unit, raw_text: best.raw_text,
            source_ids: best.source_ids,
            confidence: Math.min(best.confidence === null || best.confidence === undefined
              ? 0.5 : best.confidence, 0.3),
            note_fa: 'عدد به‌طور کامل خوانده نشد و ممکن است ناقص باشد؛ ' +
              'به‌عنوان مقدار قطعی خوانده نمی‌شود.'
          });
        }
      }
      // «mL تنها» بدون هیچ mg: احتمالاً حجم بسته است، نه قدرت دارو
      if (key === 'strength' && best.unit === 'mL' &&
        !cands.some(function (c) {
          return c.unit === 'mg' || c.value_norm.indexOf('mg') !== -1;
        })) {
        return mkRecord(key, 'uncertain', {
          value: best.value_norm, unit: best.unit, raw_text: best.raw_text,
          source_ids: best.source_ids, confidence: best.confidence,
          note_fa: 'واحد mL به‌تنهایی ممکن است حجم بسته باشد نه قدرت دارو؛ ' +
            'به‌عنوان قدرت قطعی خوانده نمی‌شود.'
        });
      }
      if (res.status === 'conflicting') {
        return mkRecord(key, 'conflicting', {
          value: best.value_norm, unit: best.unit, raw_text: best.raw_text,
          source_ids: best.source_ids, confidence: best.confidence,
          note_fa: 'مقادیر متفاوتی خوانده شد: ' + res.distinct.join('، ') +
            '. لطفاً ناحیه مربوط را واضح‌تر بگیرید یا مقدار درست را اصلاح کنید.'
        });
      }
      var statusEnum = res.status === 'extracted' ? 'extracted' : 'uncertain';
      return mkRecord(key, statusEnum, {
        value: best.value_norm, unit: best.unit, raw_text: best.raw_text,
        source_ids: best.source_ids, confidence: best.confidence,
        note_fa: statusEnum === 'uncertain'
          ? 'اطمینان OCR پایین است؛ مقدار ممکن است نادرست خوانده شده باشد.' : null
      });
    }

    var fields = {};
    fields.strength = resolveField('strength', strengthCands);
    fields.count = resolveField('count', countCands);

    var refH = imageHeight || (lines.length
      ? Math.max.apply(null, lines.map(function (l) { return l.bbox.y + l.bbox.h; }))
      : 1);
    if (fields.strength.status === 'conflicting' && strengthCands.length >= 2) {
      var ys = strengthCands.map(function (c) { return c.y; });
      if (Math.max.apply(null, ys) - Math.min.apply(null, ys) > 0.5 * refH) {
        extractionWarnings.push(
          'چند ناحیه متنی مستقل در تصویر دیده می‌شود؛ برای نتیجه دقیق، ' +
          'لطفاً یک بسته را برش بزنید یا فقط یک بسته را عکس بگیرید. ' +
          'اطلاعات چند بسته در یک خروجی ادغام نمی‌شود.');
      }
    }

    fields.expiry_date = dateRecord('expiry_date', expiryCands, settings);
    fields.production_date = dateRecord('production_date', prodCands, settings);
    fields.batch = resolveField('batch', batchCands);

    var tmp;
    tmp = freeTextField('storage', lines, P.RE_STORAGE_KEYWORD, settings);
    fields.storage = tmp[0];
    tmp[1].forEach(function (i) { consumed.add(i); });

    tmp = freeTextField('warnings', lines, P.RE_WARNING_KEYWORD, settings);
    fields.warnings = tmp[0];
    tmp[1].forEach(function (i) { consumed.add(i); });

    tmp = freeTextField('printed_directives', lines, P.RE_DIRECTIVE_KEYWORD, settings);
    fields.printed_directives = tmp[0];
    tmp[1].forEach(function (i) { consumed.add(i); });

    tmp = freeTextField('manufacturer', lines, P.RE_MANUFACTURER_KEYWORD, settings);
    fields.manufacturer = tmp[0];
    tmp[1].forEach(function (i) { consumed.add(i); });

    [expiryCands, prodCands, batchCands].forEach(function (candList) {
      if (candList.length) consumed.add(candList[0].line_index);
    });

    // ماده مؤثره: فقط اگر صریحاً کنار واژه کلیدی درج شده باشد
    fields.active_ingredient = missing('active_ingredient');
    for (var idx2 = 0; idx2 < lines.length; idx2++) {
      var line2 = lines[idx2];
      var im = P.RE_INGREDIENT_KEYWORD.exec(line2.normalized_text);
      P.RE_INGREDIENT_KEYWORD.lastIndex = 0;
      if (!im) continue;
      var afterText = line2.normalized_text.slice(im.index + im[0].length);
      var st = P.RE_STRENGTH.exec(afterText);
      var val, candUnit = null;
      if (st) {
        var cand = textCandidateFromStrength(st, line2, idx2);
        var head = afterText.slice(0, st.index).replace(/^[:=\-،,\s]+|[:=\-،,\s]+$/g, '');
        val = tn.cleanedDisplayText(head || st[0]);
        candUnit = cand ? cand.unit : null;
      } else {
        val = tn.cleanedDisplayText(line2.text);
      }
      var conf2 = confOf(line2);
      fields.active_ingredient = mkRecord('active_ingredient',
        conf2 >= settings.low_confidence_threshold ? 'extracted' : 'uncertain', {
        value: val || null, unit: candUnit, raw_text: line2.text,
        source_ids: line2.source_ids.slice(),
        confidence: Math.round(conf2 * 100) / 100
      });
      consumed.add(idx2);
      break;
    }

    // شکل دارویی
    fields.dosage_form = missing('dosage_form');
    if (fields.count.unit) {
      var form = P.DOSAGE_FORM_FA[fields.count.unit];
      if (form) {
        fields.dosage_form = mkRecord('dosage_form', 'extracted', {
          value: form, unit: null, raw_text: fields.count.raw_text,
          source_ids: fields.count.source_ids.slice(),
          confidence: fields.count.confidence
        });
      }
    }
    if (fields.dosage_form.status === 'missing') {
      for (var idx3 = 0; idx3 < lines.length; idx3++) {
        var dm = P.RE_DOSAGE_FORM.exec(lines[idx3].normalized_text);
        P.RE_DOSAGE_FORM.lastIndex = 0;
        if (!dm) continue;
        var form2 = P.DOSAGE_FORM_FA[dm[0].toLowerCase()];
        if (form2) {
          var conf3 = confOf(lines[idx3]);
          fields.dosage_form = mkRecord('dosage_form',
            conf3 >= settings.low_confidence_threshold ? 'extracted' : 'uncertain', {
            value: form2, unit: null, raw_text: lines[idx3].text,
            source_ids: lines[idx3].source_ids.slice(),
            confidence: Math.round(conf3 * 100) / 100
          });
          break;
        }
      }
    }

    // فیلدهای عمومی
    fields.net_weight = missing('net_weight');
    for (var idx4 = 0; idx4 < lines.length; idx4++) {
      var line4 = lines[idx4];
      var nm = P.RE_NET_WEIGHT_KEYWORD.exec(line4.normalized_text);
      P.RE_NET_WEIGHT_KEYWORD.lastIndex = 0;
      if (!nm) continue;
      var st4 = P.searchAt(P.RE_STRENGTH, line4.normalized_text, nm.index + nm[0].length) ||
        P.RE_STRENGTH.exec(line4.normalized_text);
      if (st4) {
        var cand4 = textCandidateFromStrength(st4, line4, idx4);
        if (cand4) {
          var conf4 = confOf(line4);
          fields.net_weight = mkRecord('net_weight',
            conf4 >= settings.low_confidence_threshold ? 'extracted' : 'uncertain', {
            value: cand4.value_norm, unit: cand4.unit, raw_text: st4[0],
            source_ids: line4.source_ids.slice(),
            confidence: Math.round(conf4 * 100) / 100
          });
          consumed.add(idx4);
          break;
        }
      }
    }

    tmp = freeTextField('ingredients', lines, P.RE_INGREDIENT_KEYWORD, settings);
    fields.ingredients = tmp[0];
    tmp[1].forEach(function (i) { consumed.add(i); });

    // نام: ابتدا سطر بالایی اگر «نام + قدرت» را با هم دارد؛ سپس کاندیدهای آزاد
    fields.name = missing('name');
    var nameSet = false;
    if (lines.length) {
      var top = 0;
      lines.forEach(function (l, i) {
        if ((l.bbox.y < lines[top].bbox.y) ||
          (l.bbox.y === lines[top].bbox.y && l.bbox.x < lines[top].bbox.x)) top = i;
      });
      var tm = P.RE_STRENGTH.exec(lines[top].normalized_text);
      if (tm) {
        var remainder = lines[top].normalized_text.slice(0, tm.index)
          .replace(/^[:\-.،,\s]+|[:\-.،,\s]+$/g, '');
        var alphaCount = 0;
        for (var c = 0; c < remainder.length; c++) {
          if (/\p{L}/u.test(remainder[c])) alphaCount++;
        }
        if (alphaCount >= ALPHA_MIN) {
          var confT = confOf(lines[top]);
          fields.name = mkRecord('name',
            confT >= settings.low_confidence_threshold ? 'extracted' : 'uncertain', {
            value: tn.cleanedDisplayText(remainder), unit: null,
            raw_text: lines[top].text, source_ids: lines[top].source_ids.slice(),
            confidence: Math.round(confT * 100) / 100
          });
          consumed.add(top);
          nameSet = true;
        }
      }
    }
    var nameIdxList = nameSet ? [] : nameCandidates(consumed, lines);
    if (nameIdxList.length) {
      var idxN = nameIdxList[0];
      var lineN = lines[idxN];
      var confN = confOf(lineN);
      fields.name = mkRecord('name',
        confN >= settings.low_confidence_threshold ? 'extracted' : 'uncertain', {
        value: tn.cleanedDisplayText(lineN.text), unit: null,
        raw_text: lineN.text, source_ids: lineN.source_ids.slice(),
        confidence: Math.round(confN * 100) / 100
      });
      consumed.add(idxN);
      // چندمحصولی: نام دوم در بخش پایین «تصویر» → درخواست برش یک بسته
      for (var o = 1; o < nameIdxList.length; o++) {
        if (lines[nameIdxList[o]].bbox.y > 0.55 * refH) {
          extractionWarnings.push(
            'چند ناحیه متنی مستقل در تصویر دیده می‌شود؛ برای نتیجه دقیق، ' +
            'لطفاً یک بسته را برش بزنید یا فقط یک بسته را عکس بگیرید. ' +
            'اطلاعات چند بسته در یک خروجی ادغام نمی‌شود.');
          break;
        }
      }
    }

    // قالب فیلدها بر اساس نوع بسته (فیلدهای خارج از قالب نمایش داده نمی‌شوند)
    var keys = productType === 'medicine' ? MEDICINE_KEYS : GENERAL_KEYS;
    var ordered = {};
    keys.forEach(function (k) { ordered[k] = fields[k] || missing(k); });
    return { fields: ordered, warnings: extractionWarnings };
  }

  LBR.extractor = {
    FIELD_LABELS_FA: FIELD_LABELS_FA,
    MEDICINE_KEYS: MEDICINE_KEYS,
    GENERAL_KEYS: GENERAL_KEYS,
    classifyProductType: classifyProductType,
    resolveCandidates: resolveCandidates,
    extractFields: extractFields
  };
})(typeof window !== 'undefined' ? window : globalThis);

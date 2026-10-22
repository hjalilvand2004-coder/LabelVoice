/* خط پردازش اصلی (بخش همگام/خالص) — پورت کامل از pipeline.py و quality.py
 *
 * اجزا (پیش‌پردازش، OCR، استخراج، تولید پاسخ) مستقل و قابل تعویض‌اند.
 * هیچ متن/تصویری جایی غیر از نتیجه کاربر ذخیره نمی‌شود (حریم خصوصی).
 */
(function (root) {
  'use strict';
  var LBR = root.LBR = root.LBR || {};
  var tn = LBR.textnorm;
  var extractor = LBR.extractor;
  var responder = LBR.responder;
  var guard = LBR.guard;

  var MULTI_PRODUCT_NOTE_FA =
    'در تصاویر چندمحصولی، لطفاً یک بسته را برش بزنید یا انتخاب کنید؛ ' +
    'اطلاعات چند بسته در یک خروجی ادغام نمی‌شود.';

  // ---------- شباهت گشتالتی (معادل difflib.SequenceMatcher.ratio) ----------
  function similarityRatio(a, b) {
    if (!a.length && !b.length) return 1.0;
    if (!a.length || !b.length) return 0.0;
    // نمای نگاشت نویسه‌های b
    var b2j = {};
    for (var j = 0; j < b.length; j++) {
      var ch = b[j];
      (b2j[ch] = b2j[ch] || []).push(j);
    }
    var matches = 0;
    var queue = [[0, a.length, 0, b.length]];
    while (queue.length) {
      var seg = queue.pop();
      var alo = seg[0], ahi = seg[1], blo = seg[2], bhi = seg[3];
      // یافتن بلوک تطابق طولانی (همان find_longest_match)
      var besti = alo, bestj = blo, bestsize = 0;
      var j2len = new Map();
      for (var i = alo; i < ahi; i++) {
        var newj2len = new Map();
        var js = b2j[a[i]] || [];
        for (var k = 0; k < js.length; k++) {
          var jj = js[k];
          if (jj < blo) continue;
          if (jj >= bhi) break;
          var size = (j2len.get(jj - 1) || 0) + 1;
          newj2len.set(jj, size);
          if (size > bestsize) {
            besti = i - size + 1;
            bestj = jj - size + 1;
            bestsize = size;
          }
        }
        j2len = newj2len;
      }
      if (bestsize) {
        matches += bestsize;
        if (alo < besti && blo < bestj) queue.push([alo, besti, blo, bestj]);
        if (besti + bestsize < ahi && bestj + bestsize < bhi) {
          queue.push([besti + bestsize, ahi, bestj + bestsize, bhi]);
        }
      }
    }
    return (2 * matches) / (a.length + b.length);
  }

  // ---------- کیفیت تصویر (هیوریستیک؛ معادل quality.py) ----------
  var BLUR_GUIDANCE_FA =
    'متن بسته واضح نیست. لطفاً دوربین را ثابت نگه دارید، نور را بهتر کنید ' +
    'و از انعکاس نور روی بسته جلوگیری کنید.';

  // gray: Uint8ClampedArray با طول w*h
  function assessQuality(gray, w, h, settings) {
    var n = w * h;
    var sum = 0, bright = 0, washed = 0, k;
    for (k = 0; k < n; k++) {
      var v = gray[k];
      sum += v;
      if (v > 248) bright++;
      if (v >= 190 && v <= 246) washed++;
    }
    var meanBrightness = sum / n;
    var highlightRatio = bright / n;
    var washedRatio = washed / n;

    // واریانس لاپلاسین (کرنل 3x3 استاندارد) — معادل cv2.Laplacian().var()
    var lapSum = 0, lapSq = 0, count = 0;
    for (var y = 1; y < h - 1; y++) {
      for (var x = 1; x < w - 1; x++) {
        var idx = y * w + x;
        var lap = 4 * gray[idx] - gray[idx - 1] - gray[idx + 1] -
          gray[idx - w] - gray[idx + w];
        lapSum += lap;
        lapSq += lap * lap;
        count++;
      }
    }
    var lapVar = count ? (lapSq / count - (lapSum / count) * (lapSum / count)) : 0;

    var issues = [];
    if (lapVar < settings.severe_blur_threshold) {
      issues.push({ code: 'blurry', severity: 'severe', message_fa: BLUR_GUIDANCE_FA });
    } else if (lapVar < settings.blur_laplacian_threshold) {
      issues.push({
        code: 'blurry', severity: 'warning',
        message_fa: 'تصویر کمی تار است؛ ' + BLUR_GUIDANCE_FA
      });
    }
    if (meanBrightness < settings.dark_mean_brightness) {
      issues.push({
        code: 'dark', severity: 'warning',
        message_fa: 'نور تصویر کم است. لطفاً در محیط روشن‌تر از بسته عکس بگیرید.'
      });
    }
    if (washedRatio > 0.55) {
      issues.push({
        code: 'bright', severity: 'warning',
        message_fa: 'تصویر بیش از حد روشن/شسته‌شده است؛ نور مستقیم روی بسته نیفتد.'
      });
    }
    if (highlightRatio > settings.glare_highlight_ratio &&
      meanBrightness > 80 && meanBrightness < 235) {
      issues.push({
        code: 'glare', severity: 'warning',
        message_fa: 'احتمال انعکاس نور روی بسته وجود دارد. زاویه دوربین یا منبع نور را تغییر دهید.'
      });
    }
    if (Math.min(w, h) < settings.min_dimension_px) {
      issues.push({
        code: 'low_resolution', severity: 'warning',
        message_fa: 'رزولوشن تصویر پایین است. لطفاً از نزدیک‌تر و بدون زوم دیجیتال عکس بگیرید.'
      });
    }
    if (!issues.length) {
      issues.push({
        code: 'ok', severity: 'info',
        message_fa: 'کیفیت تصویر برای خواندن برچسب مناسب به نظر می‌رسد.'
      });
    }
    return {
      metrics: {
        width: w, height: h,
        laplacian_var: Math.round(lapVar * 100) / 100,
        mean_brightness: Math.round(meanBrightness * 100) / 100,
        highlight_ratio: Math.round(highlightRatio * 10000) / 10000
      },
      issues: issues
    };
  }

  // ---------- ادغام و شناسه‌گذاری قطعه‌ها ----------
  function iou(a, b) {
    var ax2 = a.x + a.w, ay2 = a.y + a.h;
    var bx2 = b.x + b.w, by2 = b.y + b.h;
    var ix = Math.max(0, Math.min(ax2, bx2) - Math.max(a.x, b.x));
    var iy = Math.max(0, Math.min(ay2, by2) - Math.max(a.y, b.y));
    var inter = ix * iy;
    var union = a.w * a.h + b.w * b.h - inter;
    return union > 0 ? inter / union : 0.0;
  }

  // حذف قطعه‌های تکراری بین نسخه‌ها (IoU بالا + متن یکسان)
  function mergePieces(raw) {
    var pieces = [];
    raw.forEach(function (rp) {
      var bb = { x: rp.x, y: rp.y, w: rp.w, h: rp.h };
      var norm = tn.normalizeForMatching(rp.text);
      var duplicate = null;
      for (var k = 0; k < pieces.length; k++) {
        var existing = pieces[k];
        var sameText = existing.normalized_text.toLowerCase() === norm.toLowerCase();
        if (sameText && iou(existing.bbox, bb) > 0.55) {
          if (duplicate === null) duplicate = existing;
          else if ((existing.confidence || 0) > (duplicate.confidence || 0)) duplicate = existing;
        }
      }
      if (duplicate !== null) {
        if ((rp.confidence || 0) > (duplicate.confidence || 0)) {
          duplicate.confidence = rp.confidence;
          duplicate.variant = rp.variant;
        }
        return;
      }
      pieces.push({
        id: '', text: rp.text, normalized_text: norm, bbox: bb,
        confidence: rp.confidence, variant: rp.variant, engine: rp.engine
      });
    });
    return pieces;
  }

  function assignIds(pieces) {
    pieces.sort(function (a, b) {
      return ((a.bbox.y + (a.bbox.h >> 1)) - (b.bbox.y + (b.bbox.h >> 1))) ||
        (a.bbox.x - b.bbox.x);
    });
    pieces.forEach(function (p, i) {
      var n = String(i + 1);
      p.id = 'ocr_' + ('000' + n).slice(-3);
    });
    return pieces;
  }

  // حذف خوانش‌های فازی مشابه در یک سطر (مثلاً دو psm)؛ حفظ اطمینان بالاتر.
  // فاصله امن: شباهت ≥ 0.8 فقط برای قطعه‌های طول ≥ 3 اعمال می‌شود تا
  // ارقام/حروف کوتاه متفاوت (مثل 5 و 6) اشتباهی ادغام نشوند.
  function dedupeSimilarPieces(group) {
    var out = [];
    group.forEach(function (piece) {
      var replaced = false;
      for (var i = 0; i < out.length; i++) {
        var kept = out[i];
        var a = kept.normalized_text.trim().toLowerCase();
        var b = piece.normalized_text.trim().toLowerCase();
        if (a === b) {
          if ((piece.confidence || 0) > (kept.confidence || 0)) out[i] = piece;
          replaced = true;
          break;
        }
        // قطعه کوتاهِ زیرمجموعه (مثل «2» داخل «B12») حذف می‌شود
        if (b.length <= 3 && a.length >= 4 && a.indexOf(b) !== -1) {
          replaced = true;
          break;
        }
        if (a.length <= 3 && b.length >= 3 && b.indexOf(a) !== -1) {
          out[i] = piece;
          replaced = true;
          break;
        }
        if (a.length >= 3 && b.length >= 3 &&
          similarityRatio(a, b) >= 0.8) {
          if ((piece.confidence || 0) > (kept.confidence || 0)) out[i] = piece;
          replaced = true;
          break;
        }
      }
      if (!replaced) out.push(piece);
    });
    return out;
  }

  // سطرهای منطقی ساخته‌شده از قطعات OCR
  function buildLines(pieces) {
    if (!pieces.length) return [];
    var heights = pieces.map(function (p) { return p.bbox.h; }).sort(function (a, b) { return a - b; });
    var medianH = heights[heights.length >> 1];
    var tol = Math.max(8, Math.floor(medianH * 0.7));
    var ordered = pieces.slice().sort(function (a, b) {
      return ((a.bbox.y + (a.bbox.h >> 1)) - (b.bbox.y + (b.bbox.h >> 1))) ||
        (a.bbox.x - b.bbox.x);
    });
    var groups = [[ordered[0]]];
    for (var k = 1; k < ordered.length; k++) {
      var piece = ordered[k];
      var prev = groups[groups.length - 1][groups[groups.length - 1].length - 1];
      if (Math.abs((piece.bbox.y + (piece.bbox.h >> 1)) -
        (prev.bbox.y + (prev.bbox.h >> 1))) <= tol) {
        groups[groups.length - 1].push(piece);
      } else {
        groups.push([piece]);
      }
    }
    var lines = [];
    groups.forEach(function (group0, gi) {
      var group = dedupeSimilarPieces(group0);
      group.sort(function (a, b) { return a.bbox.x - b.bbox.x; });
      // سطرهای فارسی (RTL) به ترتیب منطقی راست‌به‌چپ بازچینی می‌شوند
      var joined = group.map(function (p) { return p.text; }).join(' ');
      if (tn.isMostlyPersian(joined)) group = group.slice().reverse();
      var text = group.map(function (p) { return p.text; }).join(' ').trim();
      var norm = tn.normalizeForMatching(text);
      var x0 = Math.min.apply(null, group.map(function (p) { return p.bbox.x; }));
      var y0 = Math.min.apply(null, group.map(function (p) { return p.bbox.y; }));
      var x1 = Math.max.apply(null, group.map(function (p) { return p.bbox.x + p.bbox.w; }));
      var y1 = Math.max.apply(null, group.map(function (p) { return p.bbox.y + p.bbox.h; }));
      var confs = group
        .filter(function (p) { return p.confidence !== null && p.confidence !== undefined; })
        .map(function (p) { return p.confidence; });
      lines.push({
        id: 'line_' + ('000' + (gi + 1)).slice(-3),
        text: text,
        normalized_text: norm,
        source_ids: group.map(function (p) { return p.id; }),
        bbox: { x: x0, y: y0, w: Math.max(1, x1 - x0), h: Math.max(1, y1 - y0) },
        confidence_mean: confs.length
          ? Math.round((confs.reduce(function (s, c) { return s + c; }, 0) / confs.length) * 1000) / 1000
          : null
      });
    });
    return lines;
  }

  // ---------- امتیازدهی بازده OCR برای انتخاب بهترین جهت/برش ----------
  // نمره = تعداد قطعه + میانگین اطمینان × ۵۰ + جایزه الگوهای فیلد (قدرت/تعداد/سری)
  function scoreOcrYield(rawPieces) {
    var n = rawPieces.length;
    var confSum = 0, confN = 0, chars = 0;
    var texts = [];
    rawPieces.forEach(function (p) {
      if (p.confidence !== null && p.confidence !== undefined) {
        confSum += p.confidence; confN++;
      }
      chars += (p.text || '').length;
      texts.push(p.text || '');
    });
    var meanConf = confN ? confSum / confN : 0;
    var score = n + meanConf * 50 + chars * 0.02;
    var norm = texts.join(' ');
    if (tn.normalizeForMatching) norm = tn.normalizeForMatching(norm);
    if (LBR.patterns) {
      if (LBR.patterns.RE_STRENGTH.test(norm)) score += 15;
      if (LBR.patterns.RE_COUNT.test(norm) || LBR.patterns.RE_COUNT_REV.test(norm)) score += 6;
      if (LBR.patterns.RE_BATCH_LABEL.test(norm)) score += 3;
      if (LBR.patterns.RE_EXPIRY_LABEL.test(norm)) score += 4;
      if (LBR.patterns.RE_DOSAGE_FORM.test(norm)) score += 2;
    }
    return {
      pieces: n,
      mean_conf: Math.round(meanConf * 1000) / 1000,
      chars: chars,
      score: Math.round(score * 100) / 100
    };
  }

  // ---------- ساخت نتیجه کامل از قطعات خام (پس از OCR) ----------
  function buildResultFromPieces(rawPieces, settings, imageW, imageH, durations, extra) {
    extra = extra || {};
    var pieces = assignIds(mergePieces(rawPieces));
    var rawLines = buildLines(pieces);
    var cls = extractor.classifyProductType(rawLines.map(function (l) { return l.normalized_text; }));
    var ex = extractor.extractFields(rawLines, cls.type, settings, imageH);
    var responseFa = responder.buildResponse(ex.fields, extra.qualityIssues || [], ex.warnings, pieces.length, cls.type);
    var selfCheck = guard.validateText(responseFa);
    if (!selfCheck.ok) {
      // حکمتی برای خطای سازنده؛ پاسخ امن حداقلی جایگزین می‌شود
      responseFa = 'پاسخ تولیدشده از قواعد ایمنی عبور نکرد؛ لطفاً تصویر واضح‌تری ارائه دهید. ' +
        responder.buildResponse({}, extra.qualityIssues || [], [], 0);
    }
    var notes = [
      'طبقه‌بندی نوع بسته فقط برای انتخاب قالب فیلدهاست و تأیید هویت یا ' +
      'اصالت محصول محسوب نمی‌شود.',
      cls.note,
      'خواندن شماره بارکد به‌تنهایی شناسایی معتبر محصول نیست (بارکدخوان ' +
      'در این نسخه وجود ندارد).'
    ];
    return {
      product_type: cls.type,
      product_type_note_fa: cls.note,
      ocr_pieces: pieces,
      raw_lines: rawLines,
      fields: ex.fields,
      quality_issues: extra.qualityIssues || [],
      quality_metrics: extra.qualityMetrics || null,
      response_fa: responseFa,
      guard_self_check: selfCheck,
      metadata: {
        engine: 'tesseract.js-wasm',
        languages: extra.languages || 'fas+eng',
        variants_used: extra.variantsUsed || ['original'],
        image_width: imageW,
        image_height: imageH,
        deskew_applied: !!extra.deskewApplied,
        deskew_angle_deg: extra.deskewAngle !== undefined ? extra.deskewAngle : null,
        crop_applied: !!extra.cropApplied,
        crop_box: extra.cropBox || null,
        crop_note_fa: extra.cropApplied ?
          'جعبه/ناحیه اصلی به‌طور خودکار شناسایی و پس‌زمینه حذف شد.' : null,
        orientation_attempts: extra.orientationAttempts || 1,
        orientation_note_fa: extra.orientationNoteFa || null,
        durations_ms: durations || {},
        warnings_fa: extra.warningsFa || [],
        notes_fa: notes,
        timestamp_utc: new Date().toISOString().replace(/\.\d+Z$/, 'Z'),
        app_version: '1.2.0-mobile'
      }
    };
  }

  // ---------- اصلاح دستی کاربر ----------
  function applyUserCorrections(result, corrections) {
    Object.keys(corrections).forEach(function (key) {
      var field = result.fields[key];
      if (!field) return;
      var newValue = (corrections[key] || '').trim();
      if (!newValue || newValue === field.value) return;
      var previous = field.value;
      field.previous_values = (previous ? [previous] : []).concat(field.previous_values || []);
      field.value = newValue;
      field.status = 'user_corrected';
      field.confidence = 1.0;
      field.note_fa = 'مقدار توسط کاربر اصلاح شد؛ مقدار قبلی حفظ شده است.';
    });
    // بازتولید پاسخ از فیلدهای اصلاح‌شده
    var response = responder.buildResponse(result.fields, result.quality_issues, [], result.ocr_pieces.length);
    var check = guard.validateText(response);
    if (!check.ok) {
      response = 'پاسخ اصلاح‌شده از قواعد ایمنی عبور نکرد؛ لطفاً مقدار واردشده را بررسی کنید.';
    }
    result.response_fa = response;
    result.metadata.warnings_fa.push(
      'پاسخ پس از اصلاح دستی بازتولید شد؛ فیلدهای اصلاح‌شده با وضعیت ' +
      'user_corrected و منشأ قبلی ثبت شدند.');
    return result;
  }

  LBR.pipeline = {
    MULTI_PRODUCT_NOTE_FA: MULTI_PRODUCT_NOTE_FA,
    similarityRatio: similarityRatio,
    assessQuality: assessQuality,
    iou: iou,
    mergePieces: mergePieces,
    assignIds: assignIds,
    dedupeSimilarPieces: dedupeSimilarPieces,
    buildLines: buildLines,
    scoreOcrYield: scoreOcrYield,
    buildResultFromPieces: buildResultFromPieces,
    applyUserCorrections: applyUserCorrections
  };
})(typeof window !== 'undefined' ? window : globalThis);

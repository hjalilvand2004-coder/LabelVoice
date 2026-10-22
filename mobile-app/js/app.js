/* کنترل‌گر رابط کاربری برچسب‌خوان موبایل
 * جریان: ورود تصویر → اعتبارسنجی → کیفیت → پیش‌پردازش → OCR → استخراج → پاسخ
 * هیچ داده‌ای از این صفحه به هیچ سروری ارسال نمی‌شود.
 */
(function () {
  'use strict';
  var LBR = window.LBR;
  var $ = function (id) { return document.getElementById(id); };

  var DEFAULT_SETTINGS = {
    ocr_languages: 'fas+eng',
    tesseract_psm: 3,
    tesseract_extra_psm: 6,
    low_confidence_threshold: 0.55,
    target_min_side: 1200,
    max_side_px: 2600,
    clahe_clip_limit: 2.0,
    clahe_tile_size: 8,
    deskew_max_angle_deg: 15,
    use_binarized_variant: true,
    use_sharpened_variant: true,
    use_sparse_psm: true,
    auto_orientation_retry: true,
    max_file_mb: 10,
    max_pixels: 30000000,
    min_dimension_px: 300,
    blur_laplacian_threshold: 45,
    severe_blur_threshold: 18,
    glare_highlight_ratio: 0.10,
    dark_mean_brightness: 55
  };

  var state = {
    imageSource: null,   // HTMLImageElement یا ImageBitmap
    imageW: 0,
    imageH: 0,
    result: null,
    busy: false
  };

  // ---------- ابزارهای UI ----------
  function show(el) { el.classList.remove('hidden'); }
  function hide(el) { el.classList.add('hidden'); }

  function setError(msg) {
    var box = $('error-box');
    if (msg) { box.textContent = msg; show(box); } else { hide(box); }
  }

  var STATUS_FA = {
    extracted: 'خوانده‌شده',
    uncertain: 'نامطمئن',
    missing: 'ناموجود',
    conflicting: 'متناقض',
    user_corrected: 'اصلاح‌شده توسط شما'
  };

  var OCR_STATUS_FA = {
    'loading tesseract core': 'بارگیری موتور OCR…',
    'initializing tesseract': 'راه‌اندازی موتور OCR…',
    'loading language traineddata': 'بارگیری داده زبان (فقط بار اول)…',
    'loaded language traineddata': 'داده زبان بارگیری شد.',
    'initializing api': 'آماده‌سازی موتور…',
    'initialized api': 'موتور آماده شد.',
    'recognizing text': 'خواندن متن…'
  };

  // ---------- ورود تصویر ----------
  function magicBytesOk(bytes) {
    // بررسی امضای فایل: PNG / JPEG / WebP (معادل validation.py)
    if (bytes.length > 8 && bytes[0] === 0x89 && bytes[1] === 0x50 &&
      bytes[2] === 0x4e && bytes[3] === 0x47) return true;
    if (bytes.length > 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return true;
    if (bytes.length > 12 && bytes[8] === 0x57 && bytes[9] === 0x45 &&
      bytes[10] === 0x42 && bytes[11] === 0x50) return true;
    return false;
  }

  function handleFile(file) {
    setError('');
    if (!file) return;
    if (file.size > DEFAULT_SETTINGS.max_file_mb * 1024 * 1024) {
      setError('حجم فایل بیشتر از ' + DEFAULT_SETTINGS.max_file_mb + ' مگابایت است.');
      return;
    }
    var reader = new FileReader();
    reader.onload = function () {
      var bytes = new Uint8Array(reader.result);
      if (!magicBytesOk(bytes)) {
        setError('فقط تصویر PNG، JPEG یا WebP پذیرفته می‌شود.');
        return;
      }
      loadAndPreview(file);
    };
    reader.onerror = function () { setError('خواندن فایل ناموفق بود.'); };
    reader.readAsArrayBuffer(file.slice(0, 32));
    function loadAndPreview(blob) {
      LBR.preprocess.loadImage(blob).then(function (img) {
        var w = img.naturalWidth || img.width;
        var h = img.naturalHeight || img.height;
        if (Math.min(w, h) < 150) {
          setError('ابعاد تصویر خیلی کوچک است؛ از نزدیک‌تر عکس بگیرید.');
          return;
        }
        if (w * h > DEFAULT_SETTINGS.max_pixels) {
          setError('ابعاد تصویر بیش از حد بزرگ است.');
          return;
        }
        state.imageSource = img;
        state.imageW = w;
        state.imageH = h;
        drawPreview();
        assessAndShowQuality();
        $('btn-analyze').disabled = false;
        hide($('result-section'));
      }).catch(function (e) {
        setError(e.message || 'بارگذاری تصویر ناموفق بود.');
      });
    }
  }

  function loadSample(sample) {
    setError('');
    LBR.preprocess.loadImage('data:' + sample.mime + ';base64,' + sample.data)
      .then(function (img) {
        state.imageSource = img;
        state.imageW = img.naturalWidth;
        state.imageH = img.naturalHeight;
        drawPreview();
        assessAndShowQuality();
        $('btn-analyze').disabled = false;
        hide($('result-section'));
      })
      .catch(function (e) { setError(e.message || 'بارگذاری نمونه ناموفق بود.'); });
  }

  // ---------- دوربین زنده ----------
  function openLiveCamera() {
    setError('');
    if (!LBR.camera.isSupported()) {
      // جایگزین: ورودی فایل با capture=environment (دوربین سیستم)
      setError('این مرورگر دوربین زنده ندارد؛ دوربین سیستم باز می‌شود.');
      $('file-camera').click();
      return;
    }
    LBR.camera.open({
      facing: 'environment',
      onCapture: function (canvas, flags) {
        LBR.camera.close();
        applyCapturedCanvas(canvas, flags);
      },
      onClose: function () { /* هیچ */ }
    }).catch(function () {
      // پیام خطا داخل اورلی نمایش داده شده است؛ کاربر می‌تواند فایل انتخاب کند
    });
  }

  function applyCapturedCanvas(canvas, flags) {
    state.imageSource = canvas;
    state.imageW = canvas.width;
    state.imageH = canvas.height;
    drawPreview();
    assessAndShowQuality();
    $('btn-analyze').disabled = false;
    hide($('result-section'));
    // عکس گرفته شد → پردازش خودکار (تجربه «نشانه بگیر و بخوان»)
    analyze();
  }

  function drawPreview() {
    var canvas = $('preview-canvas');
    var maxSide = 900;
    var scale = Math.min(1, maxSide / Math.max(state.imageW, state.imageH));
    canvas.width = Math.round(state.imageW * scale);
    canvas.height = Math.round(state.imageH * scale);
    var ctx = canvas.getContext('2d');
    ctx.drawImage(state.imageSource, 0, 0, canvas.width, canvas.height);
    show($('preview-wrap'));
  }

  function assessAndShowQuality() {
    var pre = LBR.preprocess.drawScaled(state.imageSource, state.imageW, state.imageH, DEFAULT_SETTINGS);
    var res = LBR.pipeline.assessQuality(pre.grayData, pre.w, pre.h, DEFAULT_SETTINGS);
    var box = $('quality-box');
    box.innerHTML = '';
    res.issues.forEach(function (issue) {
      var chip = document.createElement('span');
      chip.className = 'quality-chip ' + issue.severity;
      chip.textContent = issue.message_fa;
      box.appendChild(chip);
    });
    show(box);
  }

  function clearImage() {
    state.imageSource = null;
    state.result = null;
    hide($('preview-wrap'));
    hide($('quality-box'));
    hide($('result-section'));
    $('btn-analyze').disabled = true;
    setError('');
  }

  // ---------- تحلیل ----------
  function setProgress(pct, text) {
    show($('progress-box'));
    $('progress-fill').style.width = Math.max(0, Math.min(100, pct)) + '%';
    $('progress-text').textContent = text || '';
  }

  function ocrProgress(m) {
    var fa = OCR_STATUS_FA[m.status] || m.status;
    var pct = 10;
    if (m.status === 'recognizing text' && m.progress !== null) pct = 25 + m.progress * 70;
    else if (m.status === 'loading language traineddata') pct = 10 + (m.progress || 0) * 12;
    else if (m.status === 'loading tesseract core') pct = 3;
    else if (m.status === 'initializing tesseract' || m.status === 'initializing api') pct = 20;
    setProgress(pct, fa);
  }

  // اجرای یک گذر کامل OCR روی یک بوم (نسخه‌ها + دو PSM + گذرهای کمکی)
  // توجه: buildVariants همگام است و شیء ساده برمی‌گرداند؛ فقط OCR وعده‌دار است.
  function runPass(baseCanvas, settings, langQuality) {
    var built = LBR.preprocess.buildVariants(
      baseCanvas, baseCanvas.width, baseCanvas.height, settings);
    return LBR.ocr.runOcr(built.variants, settings, langQuality, ocrProgress)
      .then(function (r) { return { pieces: r.rawPieces, built: built }; });
  }

  // خوانش کم‌بازده؟ (اندک، کم‌اطمینان، یا بدون هیچ فیلد شناخته‌شده)
  function isWeakYield(yieldScore) {
    return yieldScore.pieces < 12 || yieldScore.mean_conf < 0.5;
  }

  function analyze() {
    if (state.busy || !state.imageSource) return;
    state.busy = true;
    $('btn-analyze').disabled = true;
    setError('');
    var t0 = performance.now();
    var durations = {};

    // تنظیمات فعال از رابط
    var settings = Object.assign({}, DEFAULT_SETTINGS);
    settings.use_binarized_variant = $('opt-binarized').checked;
    if (!$('opt-deskew').checked) settings.deskew_max_angle_deg = 0;
    var langQuality = $('opt-lang-quality').value;

    var qualityIssues = [], qualityMetrics = null;
    var deskewApplied = false, deskewAngle = 0.0;
    var cropApplied = false, cropBox = null;

    Promise.resolve()
      .then(function () {
        // ۱) ارزیابی اولیه و صاف‌کردن چرخش کم‌زاویه
        setProgress(2, 'ارزیابی کیفیت تصویر…');
        var pre = LBR.preprocess.drawScaled(state.imageSource, state.imageW, state.imageH, settings);
        if (settings.deskew_max_angle_deg > 0) {
          setProgress(4, 'بررسی چرخش تصویر…');
          var dk = LBR.preprocess.autoDeskew(pre.canvas, settings);
          deskewApplied = dk.angle !== 0;
          deskewAngle = dk.angle;
          return dk.canvas;
        }
        return pre.canvas;
      })
      .then(function (baseCanvas) {
        // ۲) تشخیص بسته/جعبه و برش پس‌زمینه (کاهش نویز OCR)
        setProgress(6, 'تشخیص ناحیه بسته…');
        var w = baseCanvas.width, h = baseCanvas.height;
        var bctx = baseCanvas.getContext('2d', { willReadFrequently: true });
        var gray = LBR.preprocess.toGrayData(bctx, w, h);
        var det = LBR.boxdetect.detectLabelRegion(gray, w, h);
        if (det.found) {
          baseCanvas = LBR.preprocess.cropCanvas(baseCanvas, det.box);
          cropApplied = true;
          cropBox = det.box;
        }
        return baseCanvas;
      })
      .then(function (baseCanvas) {
        // ۳) کیفیت روی همان تصویری که OCR می‌شود (پس از برش)
        setProgress(8, 'ارزیابی کیفیت تصویر…');
        var w = baseCanvas.width, h = baseCanvas.height;
        var bctx = baseCanvas.getContext('2d', { willReadFrequently: true });
        var gray = LBR.preprocess.toGrayData(bctx, w, h);
        var q = LBR.pipeline.assessQuality(gray, w, h, settings);
        qualityIssues = q.issues;
        qualityMetrics = q.metrics;
        return baseCanvas;
      })
      .then(function (baseCanvas) {
        // ۴) گذر اصلی OCR
        setProgress(10, 'خواندن متن…');
        durations.preprocess_ms = Math.round(performance.now() - t0);
        return runPass(baseCanvas, settings, langQuality)
          .then(function (pass1) {
            var y1 = LBR.pipeline.scoreOcrYield(pass1.pieces);
            if (!settings.auto_orientation_retry || !isWeakYield(y1)) {
              return { pieces: pass1.pieces, built: pass1.built, attempts: 1, note: null };
            }
            // ۵) خوانش ضعیف → آزمون چرخش ۹۰ درجه (بسته‌های عکاسی‌شده از پهلو)
            setProgress(40, 'خوانش کم‌بازده بود؛ آزمایش جهت‌های دیگر…');
            var cw = LBR.preprocess.rotate90(baseCanvas, 1);
            return runPass(cw, settings, langQuality).then(function (pass2) {
              var y2 = LBR.pipeline.scoreOcrYield(pass2.pieces);
              if (y2.score <= y1.score + 8) {
                // چرخش ساعتگرد بهتر نشد؛ پادساعتگرد را هم امتحان کن
                setProgress(60, 'آزمایش جهت مخالف…');
                var ccw = LBR.preprocess.rotate90(baseCanvas, -1);
                return runPass(ccw, settings, langQuality).then(function (pass3) {
                  var y3 = LBR.pipeline.scoreOcrYield(pass3.pieces);
                  var best = y1; var pick = 1; var pieces = pass1.pieces;
                  if (y2.score > best.score) { best = y2; pick = 2; pieces = pass2.pieces; }
                  if (y3.score > best.score) { best = y3; pick = 3; pieces = pass3.pieces; }
                  return {
                    pieces: pieces, built: pass1.built, attempts: 3,
                    note: 'تصویر در ' + (pick === 1 ? 'جهت اصلی' :
                      (pick === 2 ? 'چرخش ۹۰ درجه ساعتگرد' : 'چرخش ۹۰ درجه پادساعتگرد')) +
                      ' بهتر خوانده شد (امتیاز ' + best.score + ' در برابر ' + y1.score + ').'
                  };
                });
              }
              return {
                pieces: pass2.pieces, built: pass1.built, attempts: 2,
                note: 'تصویر در چرخش ۹۰ درجه ساعتگرد بهتر خوانده شد ' +
                  '(امتیاز ' + y2.score + ' در برابر ' + y1.score + ').'
              };
            });
          });
      })
      .then(function (winner) {
        durations.ocr_ms = Math.round(performance.now() - t0) - (durations.preprocess_ms || 0);
        // ۶) استخراج + پاسخ از بهترین خوانش
        setProgress(96, 'استخراج فیلدها و تولید پاسخ…');
        var result = LBR.pipeline.buildResultFromPieces(
          winner.pieces, settings, winner.built.width, winner.built.height, durations, {
            qualityIssues: qualityIssues,
            qualityMetrics: qualityMetrics,
            languages: settings.ocr_languages,
            variantsUsed: Object.keys(winner.built.variants),
            deskewApplied: deskewApplied,
            deskewAngle: deskewAngle,
            cropApplied: cropApplied,
            cropBox: cropBox,
            orientationAttempts: winner.attempts,
            orientationNoteFa: winner.note
          });
        durations.total_ms = Math.round(performance.now() - t0);
        state.result = result;
        setProgress(100, 'انجام شد.');
        renderResult();
      })
      .catch(function (e) {
        console.error(e);
        setError('خطا در پردازش: ' + (e && e.message ? e.message : e) +
          (location.protocol === 'file:'
            ? ' — در حالت بدون سرور، بار اول به اینترنت نیاز است.'
            : ''));
      })
      .then(function () {
        state.busy = false;
        $('btn-analyze').disabled = false;
        setTimeout(function () { hide($('progress-box')); }, 1200);
      });
  }

  // ---------- نمایش نتیجه ----------
  function usedPieceIds(result) {
    var used = new Set();
    Object.keys(result.fields).forEach(function (k) {
      (result.fields[k].source_ids || []).forEach(function (id) { used.add(id); });
    });
    return used;
  }

  function renderResult() {
    var result = state.result;
    if (!result) return;
    show($('result-section'));

    // پاسخ
    $('response-text').textContent = result.response_fa;

    // یادداشت خط لوله (برش خودکار / جهت خوانش)
    var meta = result.metadata || {};
    var noteBits = [];
    if (meta.crop_applied) noteBits.push('جعبه شناسایی شد و پس‌زمینه حذف شد.');
    if (meta.orientation_note_fa) noteBits.push(meta.orientation_note_fa);
    var noteEl = $('pipeline-note');
    if (noteBits.length) { noteEl.textContent = noteBits.join(' '); show(noteEl); }
    else hide(noteEl);

    // فیلدها
    var list = $('fields-list');
    list.innerHTML = '';
    Object.keys(result.fields).forEach(function (key) {
      list.appendChild(renderField(result, result.fields[key]));
    });

    // شواهد
    var used = usedPieceIds(result);
    var evList = $('evidence-list');
    evList.innerHTML = '';
    result.raw_lines.forEach(function (line) {
      var li = document.createElement('li');
      li.id = 'ev-' + line.id;
      if (line.source_ids.some(function (id) { return used.has(id); })) {
        li.className = 'used';
      }
      var conf = line.confidence_mean === null ? '' :
        ' <span class="line-conf">(' + Math.round(line.confidence_mean * 100) + '٪)</span>';
      li.innerHTML = '<span class="line-id">' + line.id + '</span>' +
        escapeHtml(line.text) + conf;
      evList.appendChild(li);
    });
    $('evidence-summary').textContent =
      'نمایش شواهد (' + result.raw_lines.length + ' سطر، ' + result.ocr_pieces.length + ' قطعه)';

    // JSON
    $('json-pre').textContent = JSON.stringify(resultToJson(result), null, 2);

    // دکمه اشتراک در صورت پشتیبانی
    if (navigator.share) show($('btn-share'));

    $('result-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function renderField(result, field) {
    var card = document.createElement('div');
    card.className = 'field-card';
    var head = document.createElement('div');
    head.className = 'field-head';
    var label = document.createElement('span');
    label.className = 'field-label';
    label.textContent = field.label_fa;
    var chip = document.createElement('span');
    chip.className = 'status-chip status-' + field.status;
    chip.textContent = STATUS_FA[field.status] || field.status;
    head.appendChild(label);
    head.appendChild(chip);
    card.appendChild(head);

    if (field.value) {
      var val = document.createElement('div');
      val.className = 'field-value';
      val.textContent = field.value + (field.unit && field.key !== 'strength' ? ' (' + field.unit + ')' : '');
      card.appendChild(val);
    } else {
      var none = document.createElement('div');
      none.className = 'field-value';
      none.style.color = 'var(--text-soft)';
      none.textContent = '— روی برچسب خوانده نشد و از منبع دیگری تکمیل نمی‌شود';
      card.appendChild(none);
    }
    if (field.note_fa) {
      var note = document.createElement('div');
      note.className = 'field-note';
      note.textContent = field.note_fa;
      card.appendChild(note);
    }
    if (field.source_ids && field.source_ids.length) {
      var ev = document.createElement('div');
      ev.className = 'field-evidence';
      ev.textContent = 'شواهد: ' + field.source_ids.join('، ');
      card.appendChild(ev);
    }
    if (field.previous_values && field.previous_values.length) {
      var pv = document.createElement('div');
      pv.className = 'field-evidence';
      pv.textContent = 'مقادیر قبلی: ' + field.previous_values.join('، ');
      card.appendChild(pv);
    }

    // ویرایش دستی (اصلاح کاربر با حفظ منشأ)
    var editRow = document.createElement('div');
    editRow.className = 'field-edit';
    var input = document.createElement('input');
    input.type = 'text';
    input.placeholder = 'اصلاح این مقدار…';
    input.value = field.value || '';
    input.setAttribute('aria-label', 'اصلاح ' + field.label_fa);
    var save = document.createElement('button');
    save.type = 'button';
    save.className = 'btn btn-secondary btn-small';
    save.textContent = 'ثبت';
    save.addEventListener('click', function () {
      applyCorrection(field.key, input.value);
    });
    editRow.appendChild(input);
    editRow.appendChild(save);
    card.appendChild(editRow);
    return card;
  }

  function applyCorrection(key, newValue) {
    var result = state.result;
    if (!result) return;
    var corrections = {};
    corrections[key] = newValue;
    LBR.pipeline.applyUserCorrections(result, corrections);
    // بازسازی پاسخ و فیلد ویرایش‌شده
    $('response-text').textContent = result.response_fa;
    var list = $('fields-list');
    list.innerHTML = '';
    Object.keys(result.fields).forEach(function (k) {
      list.appendChild(renderField(result, result.fields[k]));
    });
    $('json-pre').textContent = JSON.stringify(resultToJson(result), null, 2);
  }

  // خروجی JSON با همان ساختار نسخه دسکتاپ
  function resultToJson(result) {
    var out = {
      product_type: result.product_type,
      product_type_note_fa: result.product_type_note_fa,
      ocr_pieces: result.ocr_pieces.map(function (p) {
        return {
          id: p.id, text: p.text, normalized_text: p.normalized_text,
          bbox: p.bbox, confidence: p.confidence,
          variant: p.variant, engine: p.engine
        };
      }),
      raw_lines: result.raw_lines,
      fields: result.fields,
      quality_issues: result.quality_issues,
      quality_metrics: result.quality_metrics,
      response_fa: result.response_fa,
      metadata: result.metadata
    };
    return out;
  }

  // ---------- عملکردهای پاسخ ----------
  function speakResponse() {
    var note = $('tts-note');
    if (!('speechSynthesis' in window)) {
      note.textContent = 'مرورگر شما از پخش صوتی پشتیبانی نمی‌کند.';
      return;
    }
    var text = state.result ? state.result.response_fa : '';
    if (!text) return;
    var voices = window.speechSynthesis.getVoices();
    var faVoice = null;
    for (var i = 0; i < voices.length; i++) {
      if (voices[i].lang && voices[i].lang.toLowerCase().indexOf('fa') === 0) {
        faVoice = voices[i];
        break;
      }
    }
    var u = new SpeechSynthesisUtterance(text);
    if (faVoice) {
      u.voice = faVoice;
      u.lang = faVoice.lang;
      note.textContent = 'پخش با صدای فارسی دستگاه («' + faVoice.name + '»). هیچ داده‌ای ارسال نمی‌شود.';
    } else {
      u.lang = 'fa-IR';
      note.textContent = 'صدای فارسی روی این دستگاه نصب نیست؛ تلاش با صدای پیش‌فرض. ' +
        'برای صدای فارسی، بسته صوتی فارسی سیستم را نصب کنید. هیچ داده‌ای ارسال نمی‌شود.';
    }
    u.rate = 0.95;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(u);
  }

  function copyResponse() {
    var text = state.result ? state.result.response_fa : '';
    if (!text) return;
    var done = function () {
      var b = $('btn-copy');
      var old = b.textContent;
      b.textContent = 'کپی شد ✓';
      setTimeout(function () { b.textContent = old; }, 1500);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text, done); });
    } else {
      fallbackCopy(text, done);
    }
  }

  function fallbackCopy(text, done) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); done(); } catch (e) { /* نادیده */ }
    document.body.removeChild(ta);
  }

  function shareResponse() {
    var text = state.result ? state.result.response_fa : '';
    if (!text || !navigator.share) return;
    navigator.share({ title: 'برچسب‌خوان هوشمند', text: text }).catch(function () { /* لغو */ });
  }

  function downloadJson() {
    var result = state.result;
    if (!result) return;
    var json = JSON.stringify(resultToJson(result), null, 2);
    var blob = new Blob([json], { type: 'application/json' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'label-result-' + new Date().toISOString().replace(/[:.]/g, '-') + '.json';
    document.body.appendChild(a);
    a.click();
    setTimeout(function () {
      URL.revokeObjectURL(a.href);
      document.body.removeChild(a);
    }, 500);
  }

  // ---------- راه‌اندازی ----------
  function init() {
    // ثبت Service Worker فقط در حالت http(s) (در file:// بی‌معناست)
    if ('serviceWorker' in navigator && location.protocol !== 'file:') {
      navigator.serviceWorker.register('./sw.js').catch(function () { /* نادیده */ });
    }

    // یادداشت حالت اجرا
    var modeNote = $('mode-note');
    if (location.protocol === 'file:') {
      modeNote.textContent = 'حالت بدون سرور: موتور OCR و داده زبان از CDN بارگیری می‌شود ' +
        '(نیازمند اینترنت در بار اول). برای اجرای کاملاً آفلاین، برنامه را با لانچر (شروع) باز کنید.';
    } else {
      modeNote.textContent = 'حالت کامل: همه اجزا (موتور OCR، داده زبان، فونت) به‌صورت محلی ' +
        'بارگیری می‌شوند؛ پس از بار اول، کاملاً آفلاین کار می‌کند.';
    }

    // نمونه‌ها
    var chips = $('sample-chips');
    (window.LBR_SAMPLES || []).forEach(function (sample) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'sample-chip';
      b.textContent = sample.title;
      b.addEventListener('click', function () { loadSample(sample); });
      chips.appendChild(b);
    });

    // رویدادها
    $('btn-camera-live').addEventListener('click', openLiveCamera);
    $('file-camera').addEventListener('change', function (e) {
      handleFile(e.target.files && e.target.files[0]);
    });
    $('file-picker').addEventListener('change', function (e) {
      handleFile(e.target.files && e.target.files[0]);
    });
    $('btn-clear').addEventListener('click', clearImage);
    $('btn-analyze').addEventListener('click', analyze);
    $('btn-tts').addEventListener('click', speakResponse);
    $('btn-copy').addEventListener('click', copyResponse);
    $('btn-share').addEventListener('click', shareResponse);
    $('btn-json').addEventListener('click', downloadJson);

    // پیش‌بارگیری صداهای دستگاه
    if ('speechSynthesis' in window) {
      window.speechSynthesis.getVoices();
      if (typeof window.speechSynthesis.onvoiceschanged === 'undefined') {
        window.speechSynthesis.onvoiceschanged = function () { /* نادیده */ };
      }
    }

    // پیش‌بارگیری موتور OCR پس از بار اول صفحه (پس‌زمینه، بدون رابط)
    setTimeout(function () {
      if (state.busy) return;
      LBR.ocr.getWorker(DEFAULT_SETTINGS, 'integer').catch(function () { /* نادیده */ });
    }, 2500);

    // آزادسازی دوربین هنگام ترک صفحه
    window.addEventListener('pagehide', function () { LBR.camera.close(); });
    document.addEventListener('visibilitychange', function () {
      if (document.visibilityState === 'hidden') LBR.camera.close();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

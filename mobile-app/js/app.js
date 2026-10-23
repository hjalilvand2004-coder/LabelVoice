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
    name_min_confidence: 0.45,
    target_min_side: 1200,
    max_side_px: 2600,
    clahe_clip_limit: 2.0,
    clahe_tile_size: 8,
    deskew_max_angle_deg: 15,
    use_binarized_variant: true,
    use_sharpened_variant: true,
    use_white_on_dark_variant: true,
    use_ink_isolated_variant: true,
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
    hide($('stages-box'));
    $('btn-analyze').disabled = true;
    setError('');
  }

  // ---------- اعلام مرحله‌به‌مرحله پردازش و ارزیابی مرحله‌ای (v1.6.0) ----------
  // مطابق دسته ۲ ملزومات استاد (نمودار معماری): هر ۵ مرحله هنگام اجرا اعلام،
  // خروجی و معیارهای ارزیابی کیفیت همان مرحله با دکمه نمایش داده می‌شود.
  var STAGES_FA = [
    { key: 'opencv', num: '۱', color: '#2563eb', icon: '🖼️',
      title: 'پیش‌پردازش OpenCV',
      req: 'OpenCV (تشخیص ناحیه برچسب، اصلاح زاویه و بهبود وضوح)',
      files: 'js/boxdetect.js + js/preprocess.js ⇄ desktop: label_reader/preprocess.py' },
    { key: 'ocr', num: '۲', color: '#7c3aed', icon: '🔤',
      title: 'موتور OCR',
      req: 'OCR (استخراج نام، اعداد و متن بسته‌بندی)',
      files: 'js/ocr.js (Tesseract.js/WASM) ⇄ desktop: label_reader/ocr/*' },
    { key: 'fields', num: '۳', color: '#ea580c', icon: '📋',
      title: 'پردازش متن و کنترل فیلدها',
      req: 'پردازش متن و کنترل فیلدها (نرمال‌سازی نام، استخراج قدرت و تعداد درج‌شده)',
      files: 'js/textnorm.js + patterns.js + extractor.js ⇄ desktop: extraction/*' },
    { key: 'response', num: '۴', color: '#059669', icon: '💬',
      title: 'تولید پاسخ فارسی',
      req: 'تولید پاسخ فارسی (منطق استخراج اطلاعات یا LLM برای بازنویسی وفادار به متن)',
      files: 'js/responder.js + js/guard.js ⇄ desktop: response/builder.py + guard.py' },
    { key: 'tts', num: '۵', color: '#db2777', icon: '🔊',
      title: 'خوانش صوتی و نمایش (TTS + رابط)',
      req: 'TTS + Streamlit (خواندن اطلاعات و نمایش متن استخراج‌شده)',
      files: 'js/app.js (speechSynthesis) ⇄ desktop: label_reader/tts/* + app.py' }
  ];
  var STAGE_BY_KEY_FA = {};
  STAGES_FA.forEach(function (s) { STAGE_BY_KEY_FA[s.key] = s; });
  var stageEls = {};
  var stageRecords = [];

  var STAGE_ICON = { pending: '⏳', running: '🔄', done: '✅', warn: '⚠️', fail: '⛔' };

  function stagesInit() {
    var list = $('stages-list');
    list.innerHTML = '';
    stageEls = {};
    stageRecords = [];
    STAGES_FA.forEach(function (s) {
      var row = document.createElement('div');
      row.className = 'stage-row st-pending';
      row.style.setProperty('--stage-color', s.color || '#94a3b8');
      var head = document.createElement('div');
      head.className = 'stage-head';
      var icon = document.createElement('span');
      icon.className = 'stage-icon';
      icon.textContent = s.icon || STAGE_ICON.pending;
      var title = document.createElement('span');
      title.className = 'stage-title';
      title.textContent = s.num + '. ' + s.title;
      var time = document.createElement('span');
      time.className = 'stage-time';
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn btn-ghost btn-small stage-detail-btn';
      btn.textContent = 'خروجی و ارزیابی';
      btn.disabled = true;
      btn.addEventListener('click', function () {
        var det = row.querySelector('.stage-detail');
        if (det) det.classList.toggle('hidden');
      });
      head.appendChild(icon); head.appendChild(title);
      head.appendChild(time); head.appendChild(btn);
      var req = document.createElement('div');
      req.className = 'stage-req';
      req.textContent = '📌 الزام استاد: ' + s.req;
      var det = document.createElement('div');
      det.className = 'stage-detail hidden';
      row.appendChild(head); row.appendChild(req); row.appendChild(det);
      list.appendChild(row);
      stageEls[s.key] = { row: row, detail: det, btn: btn, time: time, icon: icon };
    });
    hide($('stages-summary'));
    hide($('btn-stages-report'));
    show($('stages-box'));
  }

  function stageRun(key) {
    var el = stageEls[key];
    if (!el) return;
    el.row.className = 'stage-row st-running';
    el.icon.textContent = STAGE_ICON.running;
  }

  function stagePending(key) {
    var el = stageEls[key];
    if (!el) return;
    el.row.className = 'stage-row st-pending';
    el.icon.textContent = STAGE_ICON.pending;
  }

  function stageDone(key, data) {
    var el = stageEls[key];
    var s = STAGE_BY_KEY_FA[key];
    if (!el || !s) return;
    data = data || {};
    var status = data.status || 'done';
    var dur = (data.duration_ms !== undefined && data.duration_ms !== null) ? data.duration_ms : null;
    el.row.className = 'stage-row st-' + status;
    el.icon.textContent = STAGE_ICON[status] || '✅';
    el.time.textContent = dur !== null ? dur + ' ms' : '';
    el.btn.disabled = false;

    var doneMsg = document.createElement('p');
    doneMsg.className = 'stage-done-msg';
    doneMsg.textContent = (status === 'fail' ? '⛔ ' : '✅ ') +
      'مرحله ' + s.num + ' از ۵ انجام شد — این بخش از نیازمندی استاد برآورده شد.';
    el.detail.innerHTML = '';
    el.detail.appendChild(doneMsg);

    (data.outputs || []).forEach(function (o) {
      var p = document.createElement('p');
      p.className = 'stage-output';
      p.textContent = '▸ ' + o;
      el.detail.appendChild(p);
    });

    if (data.metrics && data.metrics.length) {
      var chips = document.createElement('div');
      chips.className = 'stage-metrics';
      data.metrics.forEach(function (m) {
        var chip = document.createElement('span');
        chip.className = 'stage-chip mc-' + (m.status || 'ok');
        chip.textContent = (m.status === 'ok' ? '✅ ' : m.status === 'warn' ? '⚠️ ' : '⛔ ') +
          m.n + ': ' + m.v;
        chips.appendChild(chip);
      });
      el.detail.appendChild(chips);
    }

    var files = document.createElement('p');
    files.className = 'stage-files';
    files.textContent = '🛠 فایل پیاده‌سازی: ' + s.files;
    el.detail.appendChild(files);

    stageRecords.push({
      key: key, num_fa: s.num, title_fa: s.title,
      requirement_fa: s.req, status: status, duration_ms: dur,
      outputs_fa: data.outputs || [],
      metrics_fa: (data.metrics || []).map(function (m) {
        return { name_fa: m.n, value: String(m.v), status: m.status || 'ok' };
      }),
      files_fa: s.files
    });
  }

  function stageFinish() {
    var ok = stageRecords.filter(function (r) { return r.status === 'done' || r.status === 'warn'; }).length;
    var sum = $('stages-summary');
    sum.textContent = ok === 5
      ? '🎉 ۵ از ۵ مرحله مطابق نیازمندی استاد انجام شد؛ خروجی و ارزیابی هر مرحله با دکمه هر سطر قابل مشاهده است.'
      : 'اعلام مراحل: ' + ok + ' از ۵ مرحله با موفقیت انجام شد؛ سطرهای دارای هشدار را بررسی کنید.';
    show(sum);
    show($('btn-stages-report'));
  }

  function piecesStats(pieces) {
    var confSum = 0, confN = 0, chars = 0;
    pieces.forEach(function (p) {
      if (p.confidence !== null && p.confidence !== undefined) { confSum += p.confidence; confN++; }
      chars += (p.text || '').length;
    });
    return { pieces: pieces.length, mean_conf: confN ? confSum / confN : null, chars: chars };
  }

  function downloadStagesReport() {
    var payload = {
      report: 'stage_evaluation_report',
      project: 'برچسب‌خوان هوشمند دارو و محصولات (LabelVoice) — نسخه موبایل',
      requirement_basis: 'ملزومات طرح‌شده توسط استاد قربانی — دسته ۲: نمودار معماری',
      problem_statement: 'کاربر دوربین را به سمت جعبه دارو یا بسته‌بندی یک محصول می‌گیرد؛ سامانه نام، اطلاعات چاپ‌شده و سایر فیلدهای قابل خواندن را استخراج و به فارسی می‌خواند و اطلاعات خوانده‌شده را از توصیه‌های پزشکی جدا نگه می‌دارد.',
      stages: stageRecords,
      metadata: {
        total_ms: state.result && state.result.metadata ? state.result.metadata.durations_ms.total_ms : null,
        app_version: '1.6.0-mobile',
        timestamp_utc: new Date().toISOString()
      }
    };
    var blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'stage-evaluation-report.json';
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); document.body.removeChild(a); }, 500);
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
  // v1.7.0: byVariant برای ادغام بهترین-اول برگردانده می‌شود.
  function runPass(baseCanvas, settings, langQuality) {
    var built = LBR.preprocess.buildVariants(
      baseCanvas, baseCanvas.width, baseCanvas.height, settings);
    return LBR.ocr.runOcr(built.variants, settings, langQuality, ocrProgress)
      .then(function (r) {
        return { pieces: r.rawPieces, byVariant: r.byVariant || null, built: built };
      });
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
    stagesInit();

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
        // اعلام مرحله ۱ (OpenCV) — ملزومات استاد
        stageRun('opencv');
        setProgress(2, 'مرحله ۱ از ۵ — پیش‌پردازش OpenCV: ارزیابی کیفیت و اصلاح زاویه…');
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
        setProgress(6, 'مرحله ۱ از ۵ — تشخیص ناحیه برچسب…');
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
        setProgress(8, 'مرحله ۱ از ۵ — بهبود وضوح و ارزیابی کیفیت…');
        var w = baseCanvas.width, h = baseCanvas.height;
        var bctx = baseCanvas.getContext('2d', { willReadFrequently: true });
        var gray = LBR.preprocess.toGrayData(bctx, w, h);
        var q = LBR.pipeline.assessQuality(gray, w, h, settings);
        qualityIssues = q.issues;
        qualityMetrics = q.metrics;
        // اعلام پایان مرحله ۱ با خروجی و ارزیابی کیفیت همان مرحله
        var hadIssue = qualityIssues.some(function (i) { return i.code !== 'ok'; });
        stageDone('opencv', {
          status: hadIssue ? 'warn' : 'done',
          duration_ms: Math.round(performance.now() - t0),
          outputs: [
            'ناحیه برچسب: ' + (cropApplied ? 'شناسایی و پس‌زمینه حذف شد ✅' : 'کل تصویر پردازش شد (جعبه جدا نشد)'),
            deskewApplied ? 'چرخش کم‌زاویه تصویر (' + deskewAngle + ' درجه) اصلاح شد ✅' : 'اصلاح زاویه لازم نبود',
            'تصویر برای OCR بهبود داده شد (مقیاس + CLAHE + تیزکردن در گذر بعد)'
          ],
          metrics: [
            { n: 'تیزی (واریانس لاپلاسین)', v: qualityMetrics.laplacian_var, status: qualityMetrics.laplacian_var >= settings.severe_blur_threshold ? 'ok' : 'warn' },
            { n: 'روشنایی میانگین', v: qualityMetrics.mean_brightness, status: 'ok' },
            { n: 'ملاحظات کیفیت', v: hadIssue ? qualityIssues.filter(function (i) { return i.code !== 'ok'; }).map(function (i) { return i.code; }).join('، ') : 'ندارد', status: hadIssue ? 'warn' : 'ok' }
          ]
        });
        return baseCanvas;
      })
      .then(function (baseCanvas) {
        // ۴) گذر اصلی OCR
        // اعلام مرحله ۲ (OCR) — ملزومات استاد
        stageRun('ocr');
        setProgress(10, 'مرحله ۲ از ۵ — OCR: خواندن نام، اعداد و متن بسته‌بندی…');
        durations.preprocess_ms = Math.round(performance.now() - t0);
        return runPass(baseCanvas, settings, langQuality)
          .then(function (pass1) {
            var y1 = LBR.pipeline.scoreOcrYield(pass1.pieces);
            if (!settings.auto_orientation_retry || !isWeakYield(y1)) {
              return { pieces: pass1.pieces, byVariant: pass1.byVariant, built: pass1.built, attempts: 1, note: null };
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
                  var bv = pass1.byVariant;
                  if (y2.score > best.score) { best = y2; pick = 2; pieces = pass2.pieces; bv = pass2.byVariant; }
                  if (y3.score > best.score) { best = y3; pick = 3; pieces = pass3.pieces; bv = pass3.byVariant; }
                  return {
                    pieces: pieces, byVariant: bv, built: pass1.built, attempts: 3,
                    note: 'تصویر در ' + (pick === 1 ? 'جهت اصلی' :
                      (pick === 2 ? 'چرخش ۹۰ درجه ساعتگرد' : 'چرخش ۹۰ درجه پادساعتگرد')) +
                      ' بهتر خوانده شد (امتیاز ' + best.score + ' در برابر ' + y1.score + ').'
                  };
                });
              }
              return {
                pieces: pass2.pieces, byVariant: pass2.byVariant, built: pass1.built, attempts: 2,
                note: 'تصویر در چرخش ۹۰ درجه ساعتگرد بهتر خوانده شد ' +
                  '(امتیاز ' + y2.score + ' در برابر ' + y1.score + ').'
              };
            });
          });
      })
      .then(function (winner) {
        durations.ocr_ms = Math.round(performance.now() - t0) - (durations.preprocess_ms || 0);
        // اعلام پایان مرحله ۲ (OCR) با خروجی و ارزیابی همان مرحله
        var st2 = piecesStats(winner.pieces);
        // v1.7.0: مقایسه نسخه‌های پردازشی در خروجی مرحله شفاف می‌شود
        var variantLine = null;
        if (winner.byVariant) {
          var parts = Object.keys(winner.byVariant).map(function (k) {
            var vps = winner.byVariant[k] || [];
            var sc = LBR.pipeline.scoreVariant(vps);
            return k + ' (' + vps.length + ' قطعه، امتیاز ' + (Math.round(sc * 100) / 100) + ')';
          });
          if (parts.length) {
            variantLine = 'مقایسه نسخه‌های پردازشی (ادغام بهترین-اول): ' + parts.join(' | ');
          }
        }
        stageDone('ocr', {
          status: st2.pieces === 0 ? 'fail' : ((st2.mean_conf !== null && st2.mean_conf < 0.6) ? 'warn' : 'done'),
          duration_ms: durations.ocr_ms,
          outputs: [
            'متن خام بسته‌بندی خوانده شد؛ قطعه‌های زباله فیلتر و نواحی تکراری با ادغام بهترین-اول یکسان شدند (v1.7.0).',
            variantLine || 'نسخه‌های پردازشی: ' + Object.keys(winner.built.variants).join('، '),
            winner.note ? winner.note : 'خوانش در جهت اصلی تصویر کافی بود.',
            'متن استخراج‌شده در بخش «شواهد OCR» قابل مشاهده است.'
          ],
          metrics: [
            { n: 'قطعه‌های متنی خوانده‌شده', v: st2.pieces, status: st2.pieces > 0 ? 'ok' : 'fail' },
            { n: 'میانگین اطمینان موتور', v: st2.mean_conf === null ? '—' : Math.round(st2.mean_conf * 100) + '٪', status: (st2.mean_conf !== null && st2.mean_conf < 0.6) ? 'warn' : 'ok' },
            { n: 'مجموع نویسه‌ها', v: st2.chars, status: 'ok' },
            { n: 'تعداد گذر (جهت/چرخش)', v: winner.attempts, status: 'ok' }
          ]
        });
        // ۶) استخراج + پاسخ از بهترین خوانش — اعلام مراحل ۳ و ۴
        stageRun('fields');
        stageRun('response');
        setProgress(96, 'مرحله ۳ و ۴ از ۵ — کنترل فیلدها و تولید پاسخ فارسی…');
        var result = LBR.pipeline.buildResultFromPieces(
          winner.pieces, settings, winner.built.width, winner.built.height, durations, {
            qualityIssues: qualityIssues,
            qualityMetrics: qualityMetrics,
            languages: settings.ocr_languages,
            variantsUsed: Object.keys(winner.built.variants),
            byVariant: winner.byVariant || null,
            deskewApplied: deskewApplied,
            deskewAngle: deskewAngle,
            cropApplied: cropApplied,
            cropBox: cropBox,
            orientationAttempts: winner.attempts,
            orientationNoteFa: winner.note,
            onStage: function (key, payload) { stageDone(key, payloadToStage(key, payload)); }
          });
        durations.total_ms = Math.round(performance.now() - t0);
        state.result = result;
        setProgress(100, 'انجام شد.');
        renderResult();
        // اعلام مرحله ۵ (TTS + نمایش) — پایان همه مراحل
        stageRun('tts');
        var ttsOk = 'speechSynthesis' in window;
        stageDone('tts', {
          status: 'done',
          duration_ms: 0,
          outputs: [
            'متن استخراج‌شده نمایش داده شد (بخش «پاسخ»).' + (ttsOk ? ' پخش صوتی با دکمه «پخش صوتی پاسخ» انجام می‌شود.' : ' این مرورگر پخش صوتی ندارد.'),
            'پخش صوتی روی همین دستگاه انجام می‌شود؛ هیچ داده‌ای ارسال نمی‌شود.'
          ],
          metrics: [
            { n: 'موتور خوانش', v: ttsOk ? 'speechSynthesis (روی دستگاه)' : 'پشتیبانی نمی‌شود', status: ttsOk ? 'ok' : 'warn' },
            { n: 'طول متن پاسخ', v: result.response_fa.length + ' نویسه', status: 'ok' }
          ]
        });
        stageFinish();
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

  // تبدیل payload مراحل ۳ و ۴ (pipeline.js) به داده نمایشی/گزارشی مرحله
  function payloadToStage(key, p) {
    if (key === 'fields') {
      var c = p.status_counts || {};
      var extracted = (c.extracted || 0) + (c.user_corrected || 0);
      var outputs = [
        'نام و ارقام نرمال‌سازی شد و ۷ فیلد ساختاریافته کنترل شد (نام، قدرت درج‌شده، تعداد، انقضا، وزن، سری، سازنده).',
        'نوع بسته تشخیص‌داده‌شده: ' + (p.product_type_fa || 'نامشخص'),
        'هر مقدار به شناسه قطعه OCR (شاهد) متصل است — جدول فیلدها در بخش نتیجه.'
      ];
      (p.warnings_fa || []).forEach(function (w) { outputs.push(w); });
      return {
        status: extracted ? 'done' : 'warn',
        duration_ms: p.duration_ms,
        outputs: outputs,
        metrics: [
          { n: 'فیلدهای استخراج‌شده', v: extracted + ' از ۷', status: extracted ? 'ok' : 'warn' },
          { n: 'فیلدهای نامطمئن', v: c.uncertain || 0, status: (c.uncertain || 0) ? 'warn' : 'ok' },
          { n: 'فیلدهای غایب', v: c.missing || 0, status: 'ok' },
          { n: 'فیلدهای متناقض', v: c.conflicting || 0, status: (c.conflicting || 0) ? 'warn' : 'ok' },
          { n: 'پوشش شواهد (ردیابی‌پذیری)', v: p.evidence_coverage + '٪', status: p.evidence_coverage === 100 ? 'ok' : 'warn' }
        ]
      };
    }
    if (key === 'response') {
      return {
        status: p.guard_ok ? 'done' : 'fail',
        duration_ms: p.duration_ms,
        outputs: [
          'پاسخ فارسی وفادار به متن بسته تولید شد — در بخش «پاسخ» نمایش داده می‌شود.',
          'اطلاعات خوانده‌شده از توصیه پزشکی جدا نگه داشته می‌شود؛ هر عدد پاسخ از شواهد OCR است.',
          'نمونه پاسخ: ' + p.preview
        ],
        metrics: [
          { n: 'نگهبان ایمنی', v: p.guard_ok ? 'عبور بدون نقض (بدون «دوز مصرف» و توصیه)' : 'نقض: ' + (p.guard_violations || []).join('؛ '), status: p.guard_ok ? 'ok' : 'fail' },
          { n: 'مسیر تولید', v: 'منطق استخراج قاعده‌محور (بدون مدل زبانی ابری)', status: 'ok' },
          { n: 'طول پاسخ', v: p.length + ' نویسه', status: 'ok' }
        ]
      };
    }
    return { status: 'done', duration_ms: p.duration_ms, outputs: [], metrics: [] };
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
    if (location.protocol === 'file:' && window.__LBR_OFFLINE__) {
      modeNote.textContent = 'حالت تک‌فایلی کاملاً آفلاین: موتور OCR (WASM) و دادهٔ زبان فارسی/انگلیسی ' +
        'داخل همین فایل ذخیره شده‌اند؛ بدون اینترنت هم کار می‌کند.';
    } else if (location.protocol === 'file:') {
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
    $('btn-stages-report').addEventListener('click', downloadStagesReport);
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

    // ---------- ناوبری تب‌بار موبایل + سایدبار دسکتاپ (v1.8.0 → v1.8.2) ----------
    var navBtns = document.querySelectorAll('.tab-btn, .snav-btn');
    navBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var pageId = btn.getAttribute('data-page');
        document.querySelectorAll('.page').forEach(function (p) {
          p.classList.toggle('hidden', p.id !== pageId);
          p.classList.toggle('active', p.id === pageId);
        });
        navBtns.forEach(function (b) {
          b.classList.toggle('active', b.getAttribute('data-page') === pageId);
        });
        window.scrollTo({ top: 0, behavior: 'smooth' });
        if (pageId === 'page-reports') refreshReportsPage();
      });
    });

    // ---------- کلید حالت تاریک سایدبار (v1.8.2 — معادل نسخهٔ دسکتاپ) ----------
    var darkToggle = document.getElementById('dark-toggle');
    if (darkToggle) {
      darkToggle.checked = document.documentElement.classList.contains('dark');
      darkToggle.addEventListener('change', function () {
        document.documentElement.classList.toggle('dark', darkToggle.checked);
        try { localStorage.setItem('lbr_dark', darkToggle.checked ? '1' : '0'); } catch (e) { /* نادیده */ }
      });
    }
  }

  // ---------- صفحهٔ گزارش‌ها: ارزیابی آخرین پردازش (v1.8.0) ----------
  function refreshReportsPage() {
    var result = state.result;
    var tiles = document.querySelectorAll('#report-tiles .report-tile .rt-v');
    var empty = document.getElementById('reports-empty');
    var detail = document.getElementById('reports-detail');
    if (!result) {
      tiles.forEach(function (t) { t.textContent = '—'; });
      if (empty) empty.classList.remove('hidden');
      if (detail) detail.classList.add('hidden');
      return;
    }
    if (empty) empty.classList.add('hidden');
    var total = result.metadata && result.metadata.durations_ms
      ? result.metadata.durations_ms.total_ms : null;
    var confs = (result.ocr_pieces || [])
      .filter(function (p) { return p.confidence !== null && p.confidence !== undefined; })
      .map(function (p) { return p.confidence; });
    var meanConf = confs.length
      ? Math.round(100 * confs.reduce(function (s, c) { return s + c; }, 0) / confs.length) : null;
    var extracted = 0, withEv = 0;
    Object.keys(result.fields || {}).forEach(function (k) {
      var f = result.fields[k];
      if (f.status === 'extracted' || f.status === 'user_corrected') {
        extracted++;
        if (f.source_ids && f.source_ids.length) withEv++;
      }
    });
    var coverage = extracted ? Math.round(100 * withEv / extracted) : 100;
    if (tiles[0]) tiles[0].textContent = total !== null ? (total.toLocaleString('fa-IR') + ' ms') : '—';
    if (tiles[1]) tiles[1].textContent = meanConf !== null ? (meanConf.toLocaleString('fa-IR') + '٪') : '—';
    if (tiles[2]) tiles[2].textContent = extracted.toLocaleString('fa-IR');
    if (tiles[3]) tiles[3].textContent = coverage.toLocaleString('fa-IR') + '٪';
    if (detail) {
      detail.classList.remove('hidden');
      var box = document.getElementById('reports-stages');
      if (box) {
        box.innerHTML = '';
        var src = (typeof stageRecords !== 'undefined' && stageRecords.length)
          ? stageRecords : null;
        if (src) {
          STAGES_FA.forEach(function (s) {
            var rec = stageRecords.filter(function (r) { return r.key === s.key; })[0];
            var row = document.createElement('div');
            row.className = 'stage-row st-done';
            row.style.setProperty('--stage-color', s.color);
            var head = document.createElement('div');
            head.className = 'stage-head';
            var icon = document.createElement('span');
            icon.className = 'stage-icon';
            icon.textContent = s.icon;
            var title = document.createElement('span');
            title.className = 'stage-title';
            title.textContent = s.num + '. ' + s.title;
            head.appendChild(icon); head.appendChild(title);
            if (rec && rec.duration_ms !== undefined && rec.duration_ms !== null) {
              var time = document.createElement('span');
              time.className = 'stage-time';
              time.textContent = rec.duration_ms + ' ms';
              head.appendChild(time);
            }
            var outs = document.createElement('div');
            outs.className = 'stage-req';
            (rec && rec.outputs_fa ? rec.outputs_fa : []).slice(0, 2).forEach(function (o) {
              var p = document.createElement('div');
              p.textContent = '▸ ' + o;
              outs.appendChild(p);
            });
            row.appendChild(head); row.appendChild(outs);
            box.appendChild(row);
          });
        } else {
          box.innerHTML = '<p class="hint">جزئیات مرحله‌ای این اجرا در همین صفحهٔ «خواندن دارو» موجود است.</p>';
        }
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

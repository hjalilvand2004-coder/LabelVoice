/* پوشش Tesseract.js — موتور OCR داخل مرورگر (WASM)، بدون سرور و بدون ارسال داده
 *
 * راهبرد داده زبان:
 * - حالت http(s): vendor و lang محلی → کاملاً آفلاین.
 * - حالت file://: بارگیری از CDN با نسخه‌های قفل‌شده (نیازمند اینترنت بار اول؛
 *   پس از آن مرورگر داده را در IndexedDB نگه می‌دارد).
 * پارامترهای محافظه‌کارانه (همان نسخه دسکتاپ): دو PSM (3 و 6) و زبان fas+eng.
 */
(function (root) {
  'use strict';
  var LBR = root.LBR = root.LBR || {};

  var TESSERACT_JS_VERSION = '6.0.1';
  var TESSERACT_CORE_VERSION = '6.1.2';
  var CDN = 'https://cdn.jsdelivr.net/npm/';
  var CDN_FALLBACK = 'https://unpkg.com/';
  var TESSDATA_CDN = 'https://tessdata.projectnaptha.com/4.0.0';

  var _worker = null;
  var _workerKey = null;
  var _inlineUrls = null; // blob-URLهای موتور درون‌خطی (یک‌بار ساخته می‌شوند)

  function abs(path) {
    return new URL(path, (document.baseURI || location.href)).href;
  }

  // ---------- موتور درون‌خطی برای نسخهٔ تک‌فایلی (v1.8.2) ----------
  // window.__LBR_OFFLINE__ = { v, prelude: <منبع پرلودِ کارگر — شامل همهٔ منابع به‌صورت data: URL>
  // چون importScripts(blob:) در مبدا-ناشناس (file://) مسدود است ولی importScripts(data:)
  // و new Worker(blob) مجازند: پرلود Blob می‌شود (با workerBlobURL:false) و داخل
  // کارگر، هستهٔ WASM و دادهٔ زبان با data: URL تزریق می‌شوند.
  function buildInlineUrls() {
    if (_inlineUrls) return _inlineUrls;
    var preludeUrl = URL.createObjectURL(
      new Blob([root.__LBR_OFFLINE__.prelude], { type: 'text/javascript' }));
    _inlineUrls = { workerPath: preludeUrl };
    return _inlineUrls;
  }

  function cdnConfig(base, langQuality) {
    var c = base || CDN;
    // v2.5.0: کیفیت داده روی CDN هم واقعاً انتخابی شد — integer یا best (LSTM)
    return {
      mode: 'cdn',
      workerPath: c + 'tesseract.js@' + TESSERACT_JS_VERSION + '/dist/worker.min.js',
      corePath: c + 'tesseract.js-core@' + TESSERACT_CORE_VERSION + '/',
      langPath: TESSDATA_CDN + (langQuality === 'best' ? '_best' : ''),
      languages: 'fas+eng'
    };
  }

  // پیکربندی بر اساس نحوه باز شدن صفحه (file:// یا http/https)
  function resolveConfig(langQuality) {
    var isFile = location.protocol === 'file:';
    if (isFile) {
      // v1.8.2: تک‌فایلی با موتور درون‌خطی → کاملاً آفلاین
      if (root.__LBR_OFFLINE__) {
        var u = buildInlineUrls();
        return {
          mode: 'inline',
          workerPath: u.workerPath,
          corePath: 'inline://core/',
          langPath: 'inline://lang/',
          languages: 'fas+eng'
        };
      }
      return cdnConfig(null, langQuality);
    }
    return {
      mode: 'local',
      workerPath: abs('vendor/tesseract/worker.min.js'),
      corePath: abs('vendor/core/'),
      langPath: abs('lang/' + (langQuality === 'best' ? 'best' : 'integer') + '/'),
      languages: 'fas+eng'
    };
  }

  function getLogger(onProgress) {
    if (!onProgress) return undefined;
    return function (m) {
      if (m && m.status) {
        onProgress({
          status: m.status,
          progress: typeof m.progress === 'number' ? m.progress : null
        });
      }
    };
  }

  // ساخت کارگر با یک پیکربندی مشخص
  function createWith(cfg, settings, onProgress) {
    if (typeof Tesseract === 'undefined') {
      return Promise.reject(new Error('کتابخانه OCR بارگیری نشده است.'));
    }
    var opts = {
      workerPath: cfg.workerPath,
      corePath: cfg.corePath,
      langPath: cfg.langPath,
      gzip: true,
      // بدون رابط هم باید تابع باشد؛ undefined باعث خطای تکراری
      // «m is not a function» در onmessage می‌شد (v1.8.2)
      logger: getLogger(onProgress) || function () { /* پیام پیشرفت نادیده */ },
      // خطاهای خروجی تمیزتر
      errorHandler: function (e) {
        if (root.console && root.console.warn) root.console.warn('OCR worker:', e);
      }
    };
    if (cfg.mode === 'inline') {
      // پرلود خودش Blob کامل است — نباید دوباره در Blob «importScripts» پیچیده شود
      // (importScripts(blob:) در مبدا-ناشناس file:// توسط مرورگر مسدود است)
      opts.workerBlobURL = false;
    }
    return Tesseract.createWorker(settings.ocr_languages, 1, opts)
      .then(function (worker) {
        // آزادسازی کارگر قبلی در صورت تغییر پیکربندی
        if (_worker && typeof _worker.terminate === 'function') {
          try { _worker.terminate(); } catch (e) { /* نادیده */ }
        }
        _worker = worker;
        _workerKey = [cfg.mode, cfg.langPath, settings.ocr_languages].join('|');
        return { worker: worker, cfg: cfg };
      });
  }

  // ساخت/استفاده مجدد کارگر OCR — با زنجیرهٔ بازگشت: درون‌خطی → jsdelivr → unpkg
  function getWorker(settings, langQuality, onProgress) {
    var cfg = resolveConfig(langQuality);
    var key = [cfg.mode, cfg.langPath, settings.ocr_languages].join('|');
    if (_worker && _workerKey === key) return Promise.resolve({ worker: _worker, cfg: cfg });
    var chain = createWith(cfg, settings, onProgress);
    if (cfg.mode === 'inline') {
      chain = chain.catch(function (err) {
        if (root.console && root.console.warn) {
          root.console.warn('موتور درون‌خطی OCR شکست خورد؛ بازگشت به CDN:', err);
        }
        return createWith(cdnConfig(), settings, onProgress);
      }).catch(function (err) {
        if (root.console && root.console.warn) {
          root.console.warn('CDN اول در دسترس نیست؛ CDN پشتیبان:', err);
        }
        return createWith(cdnConfig(CDN_FALLBACK), settings, onProgress);
      });
    }
    return chain;
  }

  // اجرای OCR روی یک نسخه تصویر با یک PSM؛ خروجی: آرایه کلمه‌های خام
  function recognizeWords(worker, canvas, variant, psm) {
    return worker.setParameters({
      tessedit_pageseg_mode: String(psm),
      preserve_interword_spaces: '1',
      // بدون این پارامتر، تسراکت برای تصاویر بدون DPI یکنواخت عمل می‌کند
      user_defined_dpi: '300'
    }).then(function () {
      // در tesseract.js v6 آرایه words پیش‌فرض حذف شده است؛
      // سلسله‌مراتب blocks → paragraphs → lines → words را صریح درخواست می‌کنیم.
      return worker.recognize(canvas, {},
        { text: true, blocks: true, hocr: false, tsv: false });
    }).then(function (result) {
      var data = result && result.data ? result.data : {};
      var words = [];
      if (Array.isArray(data.words) && data.words.length) {
        data.words.forEach(function (w) {
          addWord(words, w.text, w.confidence, w.bbox, variant);
        });
        return words;
      }
      (Array.isArray(data.blocks) ? data.blocks : []).forEach(function (b) {
        (b && b.paragraphs || []).forEach(function (p) {
          (p && p.lines || []).forEach(function (l) {
            (l && l.words || []).forEach(function (w) {
              addWord(words, w.text, w.confidence, w.bbox, variant);
            });
          });
        });
      });
      return words;
    });
  }

  function addWord(words, text, confidence, bbox, variant) {
    var t = (text || '').trim();
    if (!t) return;
    var conf = (confidence === null || confidence === undefined) ? null
      : confidence / 100.0; // tesseract.js اطمینان 0..100 می‌دهد
    var b = bbox || {};
    words.push({
      text: t,
      confidence: conf,
      x: Math.round(b.x0 !== undefined ? b.x0 : (b.left || 0)),
      y: Math.round(b.y0 !== undefined ? b.y0 : (b.top || 0)),
      w: Math.round((b.x1 !== undefined ? b.x1 : (b.right || 0)) -
        (b.x0 !== undefined ? b.x0 : (b.left || 0))),
      h: Math.round((b.y1 !== undefined ? b.y1 : (b.bottom || 0)) -
        (b.y0 !== undefined ? b.y0 : (b.top || 0))),
      variant: variant,
      engine: 'tesseract.js'
    });
  }

  // اجرای کامل روی نسخه‌های تصویر — معادل provider.run + منطق binarized در pipeline.py
  // v1.7.0: گروه‌بندی خروجی به تفکیک نسخه (byVariant) برای ادغام بهترین-اول
  function runOcr(canvases, settings, langQuality, onProgress) {
    var rawPieces = [];
    var byVariant = {};
    var add = function (variant, words) {
      rawPieces = rawPieces.concat(words);
      byVariant[variant] = (byVariant[variant] || []).concat(words);
    };
    return getWorker(settings, langQuality, onProgress).then(function (env) {
      var worker = env.worker;
      var psms = [settings.tesseract_psm];
      var extra = parseInt(settings.tesseract_extra_psm, 10) || 0;
      if (extra && extra !== settings.tesseract_psm) psms.push(extra);

      var chain = Promise.resolve();
      var mainNames = ['original', 'gray_clahe'];
      if (settings.use_white_on_dark_variant && canvases.white_on_dark) {
        // نسخه متن-روشن-روی-تیره: نام سفید روی جعبه‌های رنگی (v1.7.0)
        mainNames.push('white_on_dark');
      }
      mainNames.forEach(function (name) {
        var canvas = canvases[name];
        if (!canvas) return;
        psms.forEach(function (psm) {
          chain = chain.then(function () {
            return recognizeWords(worker, canvas, name, psm)
              .then(function (words) { add(name, words); });
          });
        });
      });
      // نسخه دودویی فقط برای مقایسه؛ وقتی خوانش نسخه‌های اصلی ضعیف است
      chain = chain.then(function () {
        if (!settings.use_binarized_variant || !canvases.binarized) return null;
        var confs = rawPieces
          .filter(function (p) { return p.confidence !== null; })
          .map(function (p) { return p.confidence; });
        if (!confs.length) {
          return recognizeWords(worker, canvases.binarized, 'binarized', psms[0])
            .then(function (words) { add('binarized', words); });
        }
        var mean = confs.reduce(function (s, c) { return s + c; }, 0) / confs.length;
        if (mean >= 0.8) return null;
        return recognizeWords(worker, canvases.binarized, 'binarized', psms[0])
          .then(function (words) { add('binarized', words); });
      });
      // گذر پراکنده (PSM 11): روی بسته‌ها متن‌ها پراکنده‌اند؛ وقتی خوانش
      // خط‌محور کم‌بازده است، این گذر کلمه‌های جاافتاده را برمی‌گرداند
      // v1.7.0: روی نسخه متن-روشن-روی-تیره هم اجرا می‌شود (برای نام سفید)
      chain = chain.then(function () {
        if (!settings.use_sparse_psm || rawPieces.length >= 25) return null;
        var targets = [];
        if (canvases.gray_clahe) targets.push(['sparse11', canvases.gray_clahe]);
        if (settings.use_white_on_dark_variant && canvases.white_on_dark) {
          targets.push(['sparse11_wod', canvases.white_on_dark]);
        }
        var sub = Promise.resolve();
        targets.forEach(function (t) {
          sub = sub.then(function () {
            return recognizeWords(worker, t[1], t[0], 11)
              .then(function (words) { add(t[0], words); });
          });
        });
        return sub;
      });
      return chain.then(function () {
        return { rawPieces: rawPieces, byVariant: byVariant, cfg: env.cfg };
      });
    });
  }

  function terminate() {
    if (_worker && typeof _worker.terminate === 'function') {
      try { _worker.terminate(); } catch (e) { /* نادیده */ }
    }
    _worker = null;
    _workerKey = null;
  }

  LBR.ocr = {
    resolveConfig: resolveConfig,
    getWorker: getWorker,
    runOcr: runOcr,
    terminate: terminate
  };
})(typeof window !== 'undefined' ? window : globalThis);

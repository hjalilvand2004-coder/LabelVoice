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
  var TESSDATA_CDN = 'https://tessdata.projectnaptha.com/4.0.0';

  var _worker = null;
  var _workerKey = null;

  function abs(path) {
    return new URL(path, (document.baseURI || location.href)).href;
  }

  // پیکربندی بر اساس نحوه باز شدن صفحه (file:// یا http/https)
  function resolveConfig(langQuality) {
    var isFile = location.protocol === 'file:';
    if (isFile) {
      return {
        mode: 'cdn',
        workerPath: CDN + 'tesseract.js@' + TESSERACT_JS_VERSION + '/dist/worker.min.js',
        corePath: CDN + 'tesseract.js-core@' + TESSERACT_CORE_VERSION + '/',
        langPath: TESSDATA_CDN,
        languages: 'fas+eng'
      };
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

  // ساخت/استفاده مجدد کارگر OCR
  function getWorker(settings, langQuality, onProgress) {
    var cfg = resolveConfig(langQuality);
    var key = [cfg.mode, cfg.langPath, settings.ocr_languages].join('|');
    if (_worker && _workerKey === key) return Promise.resolve({ worker: _worker, cfg: cfg });
    if (typeof Tesseract === 'undefined') {
      return Promise.reject(new Error('کتابخانه OCR بارگیری نشده است.'));
    }
    var opts = {
      workerPath: cfg.workerPath,
      corePath: cfg.corePath,
      langPath: cfg.langPath,
      gzip: true,
      logger: getLogger(onProgress),
      // خطاهای خروجی تمیزتر
      errorHandler: function (e) {
        if (root.console && root.console.warn) root.console.warn('OCR worker:', e);
      }
    };
    return Tesseract.createWorker(settings.ocr_languages, 1, opts)
      .then(function (worker) {
        // آزادسازی کارگر قبلی در صورت تغییر پیکربندی
        if (_worker && typeof _worker.terminate === 'function') {
          try { _worker.terminate(); } catch (e) { /* نادیده */ }
        }
        _worker = worker;
        _workerKey = key;
        return { worker: worker, cfg: cfg };
      });
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
  function runOcr(canvases, settings, langQuality, onProgress) {
    var rawPieces = [];
    return getWorker(settings, langQuality, onProgress).then(function (env) {
      var worker = env.worker;
      var psms = [settings.tesseract_psm];
      var extra = parseInt(settings.tesseract_extra_psm, 10) || 0;
      if (extra && extra !== settings.tesseract_psm) psms.push(extra);

      var chain = Promise.resolve();
      ['original', 'gray_clahe'].forEach(function (name) {
        var canvas = canvases[name];
        if (!canvas) return;
        psms.forEach(function (psm) {
          chain = chain.then(function () {
            return recognizeWords(worker, canvas, name, psm)
              .then(function (words) {
                rawPieces = rawPieces.concat(words);
              });
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
            .then(function (words) { rawPieces = rawPieces.concat(words); });
        }
        var mean = confs.reduce(function (s, c) { return s + c; }, 0) / confs.length;
        if (mean >= 0.8) return null;
        return recognizeWords(worker, canvases.binarized, 'binarized', psms[0])
          .then(function (words) { rawPieces = rawPieces.concat(words); });
      });
      // گذر پراکنده (PSM 11): روی بسته‌ها متن‌ها پراکنده‌اند؛ وقتی خوانش
      // خط‌محور کم‌بازده است، این گذر کلمه‌های جاافتاده را برمی‌گرداند
      chain = chain.then(function () {
        if (!settings.use_sparse_psm || rawPieces.length >= 25) return null;
        var canvas = canvases.gray_clahe || canvases.original;
        if (!canvas) return null;
        return recognizeWords(worker, canvas, 'sparse11', 11)
          .then(function (words) { rawPieces = rawPieces.concat(words); });
      });
      return chain.then(function () {
        return { rawPieces: rawPieces, cfg: env.cfg };
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

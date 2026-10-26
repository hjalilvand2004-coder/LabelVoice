/* دوربین زنده — معادل اپ بومی: پیش‌نمایش زنده، کادر راهنما، فلاش، زوم
 *
 * مشکل نسخه قبل: <input capture="environment"> در بسیاری از مرورگرهای اندروید
 * به‌جای دوربین، گالری را باز می‌کرد. این ماژول با getUserMedia مستقیماً
 * دوربین پشتی را روشن می‌کند، تصویر زنده نشان می‌دهد و با زدن دکمه، فریم
 * می‌گیرد.
 *
 * کیفیت‌افزایی سخت‌افزاری:
 * - درخواست بالاترین رزولوشن پشتیبانی‌شده (تا 4K) از دوربین
 * - گرفتن ۳ فریم پشت‌سرهم و نگه‌داشتن تیزترین فریم (واریانس لاپلاسین)
 *   تا لرزش دست کمترین اثر را روی OCR بگذارد.
 * - هشدار نور کم روی تصویر زنده + فلاش (در صورت پشتیبانی دستگاه)
 *
 * هیچ فریمی از این صفحه به هیچ سروری ارسال نمی‌شود.
 */
(function (root) {
  'use strict';
  var LBR = root.LBR = root.LBR || {};

  // ---------- ابزار ----------
  function $(id) { return document.getElementById(id); }

  function laplacianVariance(canvas) {
    // امتیاز تیزی روی نسخه کوچک خاکستری (سریع، بدون وابستگی به pipeline)
    var w0 = canvas.width, h0 = canvas.height;
    var scale = Math.min(1, 320 / Math.max(w0, h0));
    var w = Math.max(16, Math.round(w0 * scale));
    var h = Math.max(16, Math.round(h0 * scale));
    var c = document.createElement('canvas');
    c.width = w; c.height = h;
    var ctx = c.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(canvas, 0, 0, w, h);
    var d = ctx.getImageData(0, 0, w, h).data;
    var gray = new Float32Array(w * h);
    for (var i = 0, p = 0; p < gray.length; p++, i += 4) {
      gray[p] = (d[i] * 299 + d[i + 1] * 587 + d[i + 2] * 114) / 1000;
    }
    var sum = 0, sq = 0, n = 0;
    for (var y = 1; y < h - 1; y++) {
      for (var x = 1; x < w - 1; x++) {
        var idx = y * w + x;
        var lap = 4 * gray[idx] - gray[idx - 1] - gray[idx + 1] -
          gray[idx - w] - gray[idx + w];
        sum += lap; sq += lap * lap; n++;
      }
    }
    if (!n) return 0;
    var mean = sum / n;
    return sq / n - mean * mean;
  }

  function meanBrightness(canvas) {
    var w = canvas.width, h = canvas.height;
    var ctx = canvas.getContext('2d', { willReadFrequently: true });
    var step = Math.max(1, Math.floor(Math.min(w, h) / 64));
    var d = ctx.getImageData(0, 0, w, h).data;
    var sum = 0, n = 0;
    for (var y = 0; y < h; y += step) {
      for (var x = 0; x < w; x += step) {
        var i = (y * w + x) * 4;
        sum += d[i] * 299 + d[i + 1] * 587 + d[i + 2] * 114;
        n += 3000; // 299+587+114
      }
    }
    return n ? (sum / n) : 0;
  }

  function frameToCanvas(video, maxWidth) {
    var vw = video.videoWidth, vh = video.videoHeight;
    if (!vw || !vh) return null;
    var scale = 1;
    if (maxWidth && vw > maxWidth) scale = maxWidth / vw;
    var c = document.createElement('canvas');
    c.width = Math.round(vw * scale);
    c.height = Math.round(vh * scale);
    var ctx = c.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(video, 0, 0, c.width, c.height);
    return c;
  }

  // ---------- نشست دوربین ----------
  function CameraSession(opts) {
    opts = opts || {};
    this.onCapture = opts.onCapture || function () {};
    this.onClose = opts.onClose || function () {};
    this.maxFrameWidth = opts.maxFrameWidth || 0; // 0 = حداکثر سنسور
    this.stream = null;
    this.track = null;
    this.video = null;
    this.active = false;
    this.captureCount = 3;      // چند فریم برای انتخاب تیزترین
    this._torchOn = false;
    this._multiShotSupported = true;
  }

  CameraSession.prototype._q = function (constraints) {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      return Promise.reject(new Error('UNSUPPORTED'));
    }
    return navigator.mediaDevices.getUserMedia(constraints);
  };

  CameraSession.prototype.open = function (facing) {
    var self = this;
    this._facing = facing || 'environment';
    // رزولوشن بالا: ایده‌آل 2560×1440؛ مرورگر بهترین پشتیبانی‌شده را می‌دهد
    var video = {
      facingMode: { ideal: this._facing },
      width: { ideal: 2560 },
      height: { ideal: 1440 }
    };
    return this._q({ video: video, audio: false }).then(function (stream) {
      self.stream = stream;
      self.track = stream.getVideoTracks()[0] || null;
      self.video = $('camera-video');
      self.video.srcObject = stream;
      self.active = true;
      self._applyCaps();
      self._bindUI();
      self._showHint('جعبه دارو را داخل کادر نگه دارید تا متن صاف و پرشده باشد؛ سپس دکمه سفید را بزنید.');
      // بررسی پشتیبانی فلاش
      var caps = self.track && self.track.getCapabilities ? self.track.getCapabilities() : {};
      if (caps && caps.torch) show($('btn-torch')); else hide($('btn-torch'));
      return self;
    });
  };

  CameraSession.prototype._applyCaps = function () {
    var caps = this.track && this.track.getCapabilities ? this.track.getCapabilities() : {};
    var slider = $('camera-zoom');
    if (caps && caps.zoom && caps.zoom.min !== caps.zoom.max) {
      slider.min = caps.zoom.min;
      slider.max = caps.zoom.max;
      slider.step = (caps.zoom.step || ((caps.zoom.max - caps.zoom.min) / 10));
      slider.value = (this.track.getSettings().zoom || caps.zoom.min);
      show($('zoom-row'));
    } else {
      hide($('zoom-row'));
    }
  };

  CameraSession.prototype._bindUI = function () {
    var self = this;
    var video = this.video;
    video.setAttribute('playsinline', 'true');

    $('btn-shutter').onclick = function () { self.captureSequence(); };
    $('btn-camera-close').onclick = function () {
      self.close();
      self.onClose();
    };
    $('btn-torch').onclick = function () { self.toggleTorch(); };
    $('btn-flip').onclick = function () {
      var next = (self._facing === 'environment') ? 'user' : 'environment';
      self.stopStream();
      self.open(next).catch(function (e) { self._fatal(e); });
    };
    $('camera-zoom').oninput = function () {
      var v = parseFloat(this.value);
      if (self.track && self.track.applyConstraints) {
        self.track.applyConstraints({ advanced: [{ zoom: v }] })
          .catch(function () { /* نادیده */ });
      }
    };
  };

  CameraSession.prototype.toggleTorch = function () {
    var self = this;
    if (!this.track || !this.track.applyConstraints) return;
    this._torchOn = !this._torchOn;
    this.track.applyConstraints({ advanced: [{ torch: this._torchOn }] })
      .then(function () {
        $('btn-torch').classList.toggle('torch-on', self._torchOn);
      })
      .catch(function () {
        self._torchOn = false;
        self._showHint('فلاش روی این دستگاه قابل استفاده نیست.');
      });
  };

  CameraSession.prototype._showHint = function (msg, isError) {
    var el = $('camera-hint');
    el.textContent = msg;
    el.classList.toggle('camera-hint-error', !!isError);
    el.classList.remove('hidden');
  };

  CameraSession.prototype._fatal = function (err) {
    var msg;
    var name = err && err.name ? err.name : '';
    if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
      msg = 'اجازه دوربین داده نشد. از تنظیمات مرورگر، دسترسی دوربین را برای این برنامه فعال کنید.';
    } else if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
      msg = 'دوربینی روی این دستگاه پیدا نشد.';
    } else if (name === 'NotReadableError' || name === 'TrackStartError') {
      msg = 'دوربین توسط برنامه دیگری در حال استفاده است؛ آن را ببندید و دوباره تلاش کنید.';
    } else if (err && err.message === 'UNSUPPORTED') {
      msg = 'این مرورگر از دوربین زنده پشتیبانی نمی‌کند (در حالت file:// یا بدون HTTPS). ' +
        'از دکمه «عکس با دوربین سیستم» استفاده کنید.';
    } else {
      msg = 'باز کردن دوربین ناموفق بود: ' + (err && err.message ? err.message : name);
    }
    this._showHint(msg, true);
    show($('camera-fallback'));
  };

  // گرفتن چند فریم و انتخاب تیزترین — کاهش اثر لرزش دست روی OCR
  CameraSession.prototype.captureSequence = function () {
    var self = this;
    var video = this.video;
    if (!this.active || !video || !video.videoWidth) return;
    $('btn-shutter').disabled = true;
    this._showHint('در حال گرفتن فریم‌ها… دوربین را ثابت نگه دارید.');

    var frames = [];
    var delays = [0, 220, 440];
    delays.forEach(function (d, i) {
      setTimeout(function () {
        var c = frameToCanvas(video, self.maxFrameWidth);
        if (c) frames.push({ canvas: c, sharp: laplacianVariance(c), bright: 0 });
        if (i === delays.length - 1) self._finishCapture(frames);
      }, d);
    });
  };

  CameraSession.prototype._finishCapture = function (frames) {
    $('btn-shutter').disabled = false;
    if (!frames.length) {
      this._showHint('گرفتن فریم ناموفق بود؛ دوباره تلاش کنید.', true);
      return;
    }
    frames.forEach(function (f) { f.bright = meanBrightness(f.canvas); });
    // تیزترین فریم؛ در صورت تاری همه، همان بهترین برمی‌گردد و خط لوله هشدار می‌دهد
    frames.sort(function (a, b) { return b.sharp - a.sharp; });
    var best = frames[0];
    var veryBlurry = best.sharp < 12;
    var dark = best.bright < 50;

    if (dark) {
      this._showHint('نور کم است؛ اگر دکمه فلاش دارید روشن کنید یا به محیط روشن‌تر بروید.', true);
    } else if (veryBlurry) {
      this._showHint('تصویر تار است؛ دوربین را ثابت و به بسته نزدیک‌تر کنید.', true);
    }
    // دوربین باز می‌ماند تا کاربر در صورت نیاز فوراً عکس بهتری بگیرد؛
    // نتیجه به کنترل‌گر برگردانده می‌شود.
    this.onCapture(best.canvas, { blurry: veryBlurry, dark: dark });
  };

  CameraSession.prototype.stopStream = function () {
    if (this.stream) {
      this.stream.getTracks().forEach(function (t) { try { t.stop(); } catch (e) { /* نادیده */ } });
    }
    this.stream = null;
    this.track = null;
    if (this.video) this.video.srcObject = null;
    this.active = false;
  };

  CameraSession.prototype.close = function () {
    this.stopStream();
    hide($('camera-overlay'));
    var b = $('btn-torch');
    b.classList.remove('torch-on');
    this._torchOn = false;
    hide($('camera-fallback'));
  };

  function show(el) { el.classList.remove('hidden'); }
  function hide(el) { el.classList.add('hidden'); }

  // ---------- API عمومی ----------
  var _session = null;

  LBR.camera = {
    isSupported: function () {
      return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    },
    /** باز کردن رابط دوربین زنده؛ onCapture(canvas, flags) هنگام گرفتن عکس */
    open: function (opts) {
      if (_session) { try { _session.close(); } catch (e) { /* نادیده */ } }
      _session = new CameraSession(opts);
      show($('camera-overlay'));
      hide($('camera-fallback'));
      return _session.open(opts && opts.facing).then(function (s) { return s; })
        .catch(function (e) {
          _session._fatal(e);
          throw e;
        });
    },
    close: function () {
      if (_session) _session.close();
    },
    /** برای آزمون: نشست جاری */
    current: function () { return _session; }
  };
})(typeof window !== 'undefined' ? window : globalThis);

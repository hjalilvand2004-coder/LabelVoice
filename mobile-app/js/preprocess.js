/* پیش‌پردازش تصویر روی Canvas — معادل مرورگری preprocess.py (OpenCV)
 *
 * ملاحظه مهم (همان نسخه دسکتاپ): از پردازش‌هایی که شکل اعداد یا حروف را
 * تغییر دهند پرهیز می‌شود. تصویر اصلی حفظ می‌شود و OCR روی چند نسخه اجرا
 * و نتایج مقایسه می‌گردد: original / gray_clahe / binarized.
 */
(function (root) {
  'use strict';
  var LBR = root.LBR = root.LBR || {};

  var VARIANT_ORIGINAL = 'original';
  var VARIANT_GRAY_CLAHE = 'gray_clahe';
  var VARIANT_BINARIZED = 'binarized';
  var VARIANT_SHARPENED = 'sharpened';

  // ---------- بارگذاری و مقیاس ----------
  // بارگذاری تصویر با توجه به جهت EXIF (عکس‌های موبایل)
  function loadImage(fileOrBlobOrUrl) {
    if (typeof fileOrBlobOrUrl === 'string' || fileOrBlobOrUrl instanceof Blob) {
      return new Promise(function (resolve, reject) {
        var img = new Image();
        img.onload = function () { resolve(img); };
        img.onerror = function () { reject(new Error('بارگذاری تصویر ناموفق بود.')); };
        if (fileOrBlobOrUrl instanceof Blob) {
          img.src = URL.createObjectURL(fileOrBlobOrUrl);
        } else {
          img.src = fileOrBlobOrUrl;
        }
      });
    }
    return Promise.resolve(fileOrBlobOrUrl); // ImageBitmap
  }

  function newCanvas(w, h) {
    var c = document.createElement('canvas');
    c.width = w;
    c.height = h;
    return c;
  }

  // بزرگ/کوچک‌نمایی کنترل‌شده برای OCR (همان upscale_if_needed)
  function drawScaled(source, sw, sh, settings) {
    var target = settings.target_min_side;
    var maxSide = settings.max_side_px;
    var scale = 1.0;
    var minSide = Math.min(sw, sh);
    if (minSide < target) scale = Math.min(3.0, target / Math.max(1, minSide));
    if (Math.max(sw * scale, sh * scale) > maxSide) {
      scale = maxSide / Math.max(sw, sh);
    }
    var w = Math.max(1, Math.round(sw * scale));
    var h = Math.max(1, Math.round(sh * scale));
    var canvas = newCanvas(w, h);
    var ctx = canvas.getContext('2d', { willReadFrequently: true });
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(source, 0, 0, w, h);
    // داده خاکستری یک‌بار محاسبه و در اختیار کیفیت/نسخه‌ها قرار می‌گیرد
    var grayData = toGrayData(ctx, w, h);
    return { canvas: canvas, ctx: ctx, w: w, h: h, scale: scale, grayData: grayData };
  }

  // ---------- خاکستری + CLAHE سبک ----------
  function toGrayData(ctx, w, h) {
    var img = ctx.getImageData(0, 0, w, h);
    var d = img.data;
    var gray = new Uint8ClampedArray(w * h);
    for (var i = 0, p = 0; p < gray.length; p++, i += 4) {
      gray[p] = (d[i] * 299 + d[i + 1] * 587 + d[i + 2] * 114) / 1000;
    }
    return gray;
  }

  function grayToCanvas(gray, w, h) {
    var canvas = newCanvas(w, h);
    var ctx = canvas.getContext('2d', { willReadFrequently: true });
    var img = ctx.createImageData(w, h);
    var d = img.data;
    for (var p = 0, i = 0; p < gray.length; p++, i += 4) {
      d[i] = d[i + 1] = d[i + 2] = gray[p];
      d[i + 3] = 255;
    }
    ctx.putImageData(img, 0, 0);
    return canvas;
  }

  // CLAHE سبک: هیستوگرام موضعی 8×8 با محدودسازی و درون‌یابی دوخطی
  function clahe(gray, w, h, clipLimit, tileSize) {
    var out = new Uint8ClampedArray(gray.length);
    var tilesX = Math.ceil(w / tileSize);
    var tilesY = Math.ceil(h / tileSize);
    var clipCount = Math.floor(clipLimit * tileSize * tileSize / 256) + 1;
    var maps = [];
    for (var ty = 0; ty < tilesY; ty++) {
      for (var tx = 0; tx < tilesX; tx++) {
        var hist = new Uint32Array(256);
        var x0 = tx * tileSize, y0 = ty * tileSize;
        var x1 = Math.min(w, x0 + tileSize), y1 = Math.min(h, y0 + tileSize);
        for (var y = y0; y < y1; y++) {
          for (var x = x0; x < x1; x++) hist[gray[y * w + x]]++;
        }
        // محدودسازی و بازتوزیع
        var excess = 0;
        for (var v = 0; v < 256; v++) {
          if (hist[v] > clipCount) { excess += hist[v] - clipCount; hist[v] = clipCount; }
        }
        var boost = Math.floor(excess / 256);
        var rem = excess - boost * 256;
        var cdf = new Float32Array(256);
        var acc = 0;
        var area = (x1 - x0) * (y1 - y0);
        for (var v2 = 0; v2 < 256; v2++) {
          acc += hist[v2] + boost + (v2 < 128 ? 1 : 0) * (rem > 0 ? 1 : 0);
          cdf[v2] = acc;
        }
        for (var v3 = 0; v3 < 256; v3++) maps.push(cdf[v3] / Math.max(1, acc));
      }
    }
    // درون‌یابی دوخطی بین نگاشت کاشی‌ها
    for (var yy = 0; yy < h; yy++) {
      var fy = yy / tileSize - 0.5;
      var ty1 = Math.max(0, Math.min(tilesY - 1, Math.floor(fy)));
      var ty2 = Math.max(0, Math.min(tilesY - 1, ty1 + 1));
      var wy = Math.max(0, Math.min(1, fy - ty1));
      for (var xx = 0; xx < w; xx++) {
        var fx = xx / tileSize - 0.5;
        var tx1 = Math.max(0, Math.min(tilesX - 1, Math.floor(fx)));
        var tx2 = Math.max(0, Math.min(tilesX - 1, tx1 + 1));
        var wx = Math.max(0, Math.min(1, fx - tx1));
        var v4 = gray[yy * w + xx];
        var m11 = maps[(ty1 * tilesX + tx1) * 256 + v4];
        var m12 = maps[(ty1 * tilesX + tx2) * 256 + v4];
        var m21 = maps[(ty2 * tilesX + tx1) * 256 + v4];
        var m22 = maps[(ty2 * tilesX + tx2) * 256 + v4];
        var top = m11 + (m12 - m11) * wx;
        var bottom = m21 + (m22 - m21) * wx;
        out[yy * w + xx] = Math.round((top + (bottom - top) * wy) * 255);
      }
    }
    return out;
  }

  // ---------- تیزکردن (Unsharp Mask) — بازیابی لبه‌های نرم‌شده با فوکوس ----------
  // ماسک تیزکننده: gray + amount*(gray − blur(gray)) با blur جعبه‌ای ۳×۳
  function sharpenGray(gray, w, h, amount) {
    var a = (amount === undefined) ? 1.1 : amount;
    var blur = new Float32Array(gray.length);
    for (var y = 0; y < h; y++) {
      for (var x = 0; x < w; x++) {
        var i = y * w + x;
        var s = gray[i], n = 1;
        if (x > 0) { s += gray[i - 1]; n++; }
        if (x < w - 1) { s += gray[i + 1]; n++; }
        if (y > 0) { s += gray[i - w]; n++; }
        if (y < h - 1) { s += gray[i + w]; n++; }
        blur[i] = s / n;
      }
    }
    var out = new Uint8ClampedArray(gray.length);
    for (var j = 0; j < gray.length; j++) {
      out[j] = gray[j] + a * (gray[j] - blur[j]);
    }
    return out;
  }

  // ---------- برش ناحیه بسته (خروجی boxdetect) ----------
  function cropCanvas(sourceCanvas, box) {
    var c = newCanvas(box.w, box.h);
    var ctx = c.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(sourceCanvas,
      box.x, box.y, box.w, box.h,
      0, 0, box.w, box.h);
    return c;
  }

  // ---------- چرخش ۹۰ درجه (برای تلاش جهت‌های دیگر OCR) ----------
  function rotate90(sourceCanvas, direction) {
    // direction: 1 = ساعتگرد، -1 = پادساعتگرد
    var w = sourceCanvas.width, h = sourceCanvas.height;
    var out = newCanvas(h, w);
    var ctx = out.getContext('2d', { willReadFrequently: true });
    if (direction === 1) {
      ctx.translate(h, 0);
      ctx.rotate(Math.PI / 2);
    } else {
      ctx.translate(0, w);
      ctx.rotate(-Math.PI / 2);
    }
    ctx.drawImage(sourceCanvas, 0, 0);
    return out;
  }

  // ---------- آستانه‌گذاری تطبیقی (معادل adaptiveThreshold گاوسی) ----------
  function binarizeCore(gray, w, h, windowSize, c, above) {
    // میانگین با تصویر انتگرالی (تقریب کارآمد پنجره گاوسی)
    var integral = new Float64Array((w + 1) * (h + 1));
    for (var y = 0; y < h; y++) {
      var rowSum = 0;
      for (var x = 0; x < w; x++) {
        rowSum += gray[y * w + x];
        integral[(y + 1) * (w + 1) + (x + 1)] = integral[y * (w + 1) + (x + 1)] + rowSum;
      }
    }
    var r = (windowSize - 1) >> 1;
    var out = new Uint8ClampedArray(gray.length);
    for (var y2 = 0; y2 < h; y2++) {
      var y0 = Math.max(0, y2 - r), y1c = Math.min(h - 1, y2 + r);
      for (var x2 = 0; x2 < w; x2++) {
        var x0 = Math.max(0, x2 - r), x1c = Math.min(w - 1, x2 + r);
        var area = (y1c - y0 + 1) * (x1c - x0 + 1);
        var sum = integral[(y1c + 1) * (w + 1) + (x1c + 1)] -
          integral[y0 * (w + 1) + (x1c + 1)] -
          integral[(y1c + 1) * (w + 1) + x0] +
          integral[y0 * (w + 1) + x0];
        var mean = sum / area;
        if (above) {
          // متن روشن‌تر از همسایگی → جوهر (برای متن سفید روی جعبه تیره)
          out[y2 * w + x2] = gray[y2 * w + x2] > mean + c ? 255 : 0;
        } else {
          out[y2 * w + x2] = gray[y2 * w + x2] > mean - c ? 255 : 0;
        }
      }
    }
    return out;
  }

  function binarize(gray, w, h, windowSize, c) {
    return binarizeCore(gray, w, h, windowSize, c, false);
  }

  // نسخه ویژه «متن روشن روی پس‌زمینه تیره/میانه» (v1.7.0 — معادل white_on_dark
  // در preprocess.py): desktop = bitwise_not(adaptiveThreshold(BINARY_INV,51,12))
  // که از نظر ریاضی ≡ adaptiveThreshold(BINARY, 51, 12) است؛ یعنی متن روشن
  // (روشن‌تر از همسایگی منهای C) جوهر سفید می‌شود و تسراکت ۵ پلاریتی معکوس
  // را خودش تشخیص می‌دهد (روی نمونه واقعی «MEDICINE / BOX» را خواند).
  function whiteOnDark(gray, w, h, windowSize, c) {
    return binarizeCore(gray, w, h, windowSize, c, false);
  }

  // ---------- صاف‌کردن چرخش کم‌زاویه (معادل auto_deskew) ----------
  // برآورد زاویه با واریانس پروفایل افقی روی نسخه کوچک دودویی
  function estimateSkewAngle(canvas, maxAngle) {
    var w0 = canvas.width, h0 = canvas.height;
    var scale = Math.min(1, 300 / Math.max(w0, h0));
    var w = Math.max(16, Math.round(w0 * scale));
    var h = Math.max(16, Math.round(h0 * scale));
    var small = newCanvas(w, h);
    var sctx = small.getContext('2d', { willReadFrequently: true });
    sctx.drawImage(canvas, 0, 0, w, h);
    var gray = toGrayData(sctx, w, h);
    var bw = binarize(gray, w, h, 35, 20);
    // معکوس: متن = 1
    var bestAngle = 0, bestScore = -1;
    for (var a = -maxAngle; a <= maxAngle; a += 0.5) {
      var rotated = rotateGray(bw, w, h, a);
      // نمره: واریانس مجموع سطرها (سطرهای تراز = قله‌های تیزتر)
      var rowSum = new Float64Array(h);
      for (var y = 0; y < h; y++) {
        var s = 0;
        for (var x = 0; x < w; x++) if (rotated[y * w + x] === 0) s++;
        rowSum[y] = s;
      }
      var mean = 0;
      for (var y2 = 0; y2 < h; y2++) mean += rowSum[y2];
      mean /= h;
      var variance = 0;
      for (var y3 = 0; y3 < h; y3++) variance += (rowSum[y3] - mean) * (rowSum[y3] - mean);
      if (variance > bestScore) { bestScore = variance; bestAngle = a; }
    }
    return bestAngle;
  }

  function rotateGray(src, w, h, angleDeg) {
    var out = new Uint8ClampedArray(src.length);
    var rad = angleDeg * Math.PI / 180;
    var cos = Math.cos(rad), sin = Math.sin(rad);
    var cx = w / 2, cy = h / 2;
    for (var y = 0; y < h; y++) {
      for (var x = 0; x < w; x++) {
        var dx = x - cx, dy = y - cy;
        var sx = Math.round(cx + dx * cos - dy * sin);
        var sy = Math.round(cy + dx * sin + dy * cos);
        out[y * w + x] = (sx >= 0 && sx < w && sy >= 0 && sy < h) ? src[sy * w + sx] : 255;
      }
    }
    return out;
  }

  function rotateCanvas(canvas, angleDeg) {
    var w = canvas.width, h = canvas.height;
    var rad = -angleDeg * Math.PI / 180; // چرخش معکوس برای اصلاح
    var out = newCanvas(w, h);
    var ctx = out.getContext('2d', { willReadFrequently: true });
    ctx.fillStyle = 'rgb(245,245,245)';
    ctx.fillRect(0, 0, w, h);
    ctx.translate(w / 2, h / 2);
    ctx.rotate(rad);
    ctx.drawImage(canvas, -w / 2, -h / 2);
    return out;
  }

  // اصلاح چرخش کم‌زاویه؛ زاویه‌های بزرگ قابل اعتماد نیستند و دست نمی‌خورند
  function autoDeskew(canvas, settings) {
    var angle = estimateSkewAngle(canvas, settings.deskew_max_angle_deg);
    if (Math.abs(angle) >= 0.5 && Math.abs(angle) <= settings.deskew_max_angle_deg) {
      return { canvas: rotateCanvas(canvas, angle), angle: angle };
    }
    return { canvas: canvas, angle: 0.0 };
  }

  // ---------- ساخت نسخه‌های پردازشی ----------
  function buildVariants(sourceCanvas, sw, sh, settings) {
    var scaled = drawScaled(sourceCanvas, sw, sh, settings);
    var variants = {};
    variants[VARIANT_ORIGINAL] = scaled.canvas;
    var gray = scaled.grayData;
    var claheGray = clahe(gray, scaled.w, scaled.h,
      settings.clahe_clip_limit, settings.clahe_tile_size);
    variants[VARIANT_GRAY_CLAHE] = grayToCanvas(claheGray, scaled.w, scaled.h);
    // نسخه تیزشده: برای عکس‌های کمی نرم دوربین موبایل مؤثر است
    if (settings.use_sharpened_variant) {
      var sharp = sharpenGray(claheGray, scaled.w, scaled.h, 1.1);
      variants[VARIANT_SHARPENED] = grayToCanvas(sharp, scaled.w, scaled.h);
    }
    if (settings.use_binarized_variant) {
      var bw = binarize(gray, scaled.w, scaled.h, 31, 15);
      variants[VARIANT_BINARIZED] = grayToCanvas(bw, scaled.w, scaled.h);
    }
    // v1.7.0: نسخه متن-روشن-روی-تیره برای نام سفید روی جعبه‌های رنگی
    if (settings.use_white_on_dark_variant) {
      var wod = whiteOnDark(gray, scaled.w, scaled.h, 51, 12);
      variants[VARIANT_WHITE_ON_DARK] = grayToCanvas(wod, scaled.w, scaled.h);
    }
    return {
      variants: variants,
      width: scaled.w,
      height: scaled.h,
      scale: scaled.scale,
      grayData: gray
    };
  }

  LBR.preprocess = {
    VARIANT_ORIGINAL: VARIANT_ORIGINAL,
    VARIANT_GRAY_CLAHE: VARIANT_GRAY_CLAHE,
    VARIANT_BINARIZED: VARIANT_BINARIZED,
    VARIANT_SHARPENED: VARIANT_SHARPENED,
    VARIANT_WHITE_ON_DARK: VARIANT_WHITE_ON_DARK,
    loadImage: loadImage,
    drawScaled: drawScaled,
    toGrayData: toGrayData,
    clahe: clahe,
    binarize: binarize,
    whiteOnDark: whiteOnDark,
    sharpenGray: sharpenGray,
    cropCanvas: cropCanvas,
    rotate90: rotate90,
    autoDeskew: autoDeskew,
    buildVariants: buildVariants
  };
})(typeof window !== 'undefined' ? window : globalThis);

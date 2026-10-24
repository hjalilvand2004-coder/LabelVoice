/* تشخیص ناحیه بسته/جعبه دارو در تصویر — «شیء اصلی را پیدا کن و برش بزن»
 *
 * هدف: وقتی کاربر دوربین را به جعبه دارو می‌گیرد، پس‌زمینه (میز، دست، اجناس
 * دیگر) OCR را مخدوش و پاسخ را بی‌کیفیت می‌کند. این ماژول بزرگ‌ترین ناحیه
 * متراکم متن/گرافیک (خودِ بسته) را پیدا می‌کند و مختصات برش آن را می‌دهد.
 *
 * الگوریتم (خالص جاوااسکریپت روی آرایه خاکستری — بدون وابستگی، قابل تست در Node):
 *  ۱) کوچک‌نمایی به حداکثر ۴۰۰ پیکسل (سرعت)
 *  ۲) گرادیان سوبل → نقاط لبه (بالاترین درصدی)
 *  ۳) اتساع (dilate) با هسته بزرگ → اتصال خطوط متن به بلوک‌های یکپارچه
 *  ۴) برچسب‌گذاری اجزای همبند (BFS) و یافتن بزرگ‌ترین جزء
 *  ۵) اعتبارسنجی هندسی (مساحت، پرشدگی، نسبت ابعاد) → مختصات در مقیاس اصلی
 *
 * اگر ناحیه معتبری پیدا نشود، found=false برمی‌گردد و کل تصویر استفاده
 * می‌شود (هیچ حدسی زده نمی‌شود — همان اصل شواهد‌محور).
 */
(function (root) {
  'use strict';
  var LBR = root.LBR = root.LBR || {};

  var DEFAULTS = {
    analyze_max_side: 400,   // حداکثر ضلع برای تحلیل
    edge_percentile: 0.82,   // نقاط با گرادیان بالاتر از این درصدی = لبه
    fallback_percentile: 0.95, // اگر تصویر بیش از حد صاف بود
    dilate_ratio: 0.035,     // شعاع اتساع نسبت به ضلع بزرگ
    min_area_ratio: 0.12,    // کمترین سهم مساحت جزء از تصویر
    max_area_ratio: 0.985,   // بیشترین سهم (بیشتر = کل قاب، برش بی‌معنا)
    min_fill_ratio: 0.35,    // کمترین پرشدگی جعبه محیطی جزء
    min_side_ratio: 0.30,    // کمترین سهم ضلع جزء از ضلع تصویر
    margin_ratio: 0.04       // حاشیه امن دور ناحیه برش
  };

  function sobelEdges(gray, w, h) {
    var mag = new Float32Array(w * h);
    for (var y = 1; y < h - 1; y++) {
      for (var x = 1; x < w - 1; x++) {
        var i = y * w + x;
        var tl = gray[i - w - 1], tc = gray[i - w], tr = gray[i - w + 1];
        var ml = gray[i - 1], mr = gray[i + 1];
        var bl = gray[i + w - 1], bc = gray[i + w], br = gray[i + w + 1];
        var gx = (tr + 2 * mr + br) - (tl + 2 * ml + bl);
        var gy = (bl + 2 * bc + br) - (tl + 2 * tc + tr);
        mag[i] = Math.sqrt(gx * gx + gy * gy);
      }
    }
    return mag;
  }

  function percentileOf(arr, q) {
    var sample = [];
    var step = Math.max(1, Math.floor(arr.length / 20000));
    for (var i = 0; i < arr.length; i += step) sample.push(arr[i]);
    sample.sort(function (a, b) { return a - b; });
    var idx = Math.min(sample.length - 1, Math.floor(q * sample.length));
    return sample[idx];
  }

  function dilate(mask, w, h, r) {
    // اتساع مستطیلی سریع: دو گذر یک‌بعدی (افقی سپس عمودی)
    var tmp = new Uint8Array(mask.length);
    for (var y = 0; y < h; y++) {
      var row = y * w;
      for (var x = 0; x < w; x++) {
        var v = 0;
        var x0 = Math.max(0, x - r), x1 = Math.min(w - 1, x + r);
        for (var k = x0; k <= x1; k++) {
          if (mask[row + k]) { v = 1; break; }
        }
        tmp[row + x] = v;
      }
    }
    var out = new Uint8Array(mask.length);
    for (var x2 = 0; x2 < w; x2++) {
      for (var y2 = 0; y2 < h; y2++) {
        var v2 = 0;
        var y0 = Math.max(0, y2 - r), y1 = Math.min(h - 1, y2 + r);
        for (var k2 = y0; k2 <= y1; k2++) {
          if (tmp[k2 * w + x2]) { v2 = 1; break; }
        }
        out[y2 * w + x2] = v2;
      }
    }
    return out;
  }

  // بزرگ‌ترین جزء همبند ماسک؛ خروجی: bbox و مساحت و پرشدگی
  function largestComponent(mask, w, h) {
    var visited = new Uint8Array(mask.length);
    var stack = new Int32Array(mask.length);
    var best = null;
    for (var start = 0; start < mask.length; start++) {
      if (!mask[start] || visited[start]) continue;
      var sp = 0;
      stack[sp++] = start;
      visited[start] = 1;
      var minX = w, minY = h, maxX = 0, maxY = 0, area = 0;
      while (sp > 0) {
        var idx = stack[--sp];
        var x = idx % w, y = (idx / w) | 0;
        area++;
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
        // ۸-همسایگی
        for (var dy = -1; dy <= 1; dy++) {
          var ny = y + dy;
          if (ny < 0 || ny >= h) continue;
          for (var dx = -1; dx <= 1; dx++) {
            var nx = x + dx;
            if (nx < 0 || nx >= w) continue;
            var nIdx = ny * w + nx;
            if (mask[nIdx] && !visited[nIdx]) {
              visited[nIdx] = 1;
              stack[sp++] = nIdx;
            }
          }
        }
      }
      var bw = maxX - minX + 1, bh = maxY - minY + 1;
      var bboxArea = bw * bh;
      var cand = {
        x: minX, y: minY, w: bw, h: bh,
        area: area,
        fill: bboxArea ? area / bboxArea : 0
      };
      if (!best || cand.area > best.area) best = cand;
    }
    return best;
  }

  /**
   * تشخیص ناحیه بسته در تصویر خاکستری.
   * @param {Uint8ClampedArray|Float32Array} gray  داده خاکستری w*h
   * @param {number} w  عرض تصویر اصلی
   * @param {number} h  ارتفاع تصویر اصلی
   * @param {object} [opts] بازنویسی پارامترها
   * @returns {{found:boolean, box:{x,y,w,h}|null, reason:string, debug:object}}
   *          box در مختصات تصویر ورودی است.
   */
  function detectLabelRegion(gray, w, h, opts) {
    var o = Object.assign({}, DEFAULTS, opts || {});
    var debug = { analyzed_w: 0, analyzed_h: 0, candidates: 0 };

    if (w < 60 || h < 60) {
      return { found: false, box: null, reason: 'image_too_small', debug: debug };
    }

    // ۱) کوچک‌نمایی
    var scale = Math.min(1, o.analyze_max_side / Math.max(w, h));
    var sw = Math.max(32, Math.round(w * scale));
    var sh = Math.max(32, Math.round(h * scale));
    debug.analyzed_w = sw; debug.analyzed_h = sh;
    var small = new Float32Array(sw * sh);
    // نمونه‌برداری نزدیک‌ترین همسایه (نه میانگین): لبه‌های تیز حفظ می‌شوند؛
    // میانگین‌گیری، گرادیان متن‌های ریز را در مقیاس کوچک می‌خشکاند.
    for (var y = 0; y < sh; y++) {
      var sy = Math.min(h - 1, Math.floor(y * h / sh));
      for (var x = 0; x < sw; x++) {
        var sx = Math.min(w - 1, Math.floor(x * w / sw));
        small[y * sw + x] = gray[sy * w + sx];
      }
    }

    // ۲) لبه‌ها و آستانه درصدی
    var mag = sobelEdges(small, sw, sh);
    var thr = percentileOf(mag, o.edge_percentile);
    if (thr <= 0) thr = percentileOf(mag, o.fallback_percentile);
    if (thr <= 0) {
      return { found: false, box: null, reason: 'flat_image', debug: debug };
    }
    var mask = new Uint8Array(sw * sh);
    for (var i2 = 0; i2 < mask.length; i2++) mask[i2] = mag[i2] >= thr ? 1 : 0;

    // ۳) اتصال بلوک‌های متن
    var r = Math.max(2, Math.round(o.dilate_ratio * Math.max(sw, sh)));
    mask = dilate(mask, sw, sh, r);
    mask = dilate(mask, sw, sh, r); // دو گذر → اتصال قوی‌تر خطوط نزدیک

    // ۴) بزرگ‌ترین جزء
    var comp = largestComponent(mask, sw, sh);
    debug.candidates = comp ? 1 : 0;
    if (!comp) {
      return { found: false, box: null, reason: 'no_component', debug: debug };
    }

    // ۵) اعتبارسنجی هندسی
    var areaRatio = comp.area / (sw * sh);
    var sideX = comp.w / sw, sideY = comp.h / sh;
    debug.area_ratio = Math.round(areaRatio * 1000) / 1000;
    debug.fill_ratio = Math.round(comp.fill * 1000) / 1000;

    if (areaRatio < o.min_area_ratio) {
      return { found: false, box: null, reason: 'content_too_small', debug: debug };
    }
    if (areaRatio > o.max_area_ratio) {
      return { found: false, box: null, reason: 'fills_whole_frame', debug: debug };
    }
    if (comp.fill < o.min_fill_ratio) {
      return { found: false, box: null, reason: 'scattered_content', debug: debug };
    }
    if (sideX < o.min_side_ratio || sideY < o.min_side_ratio) {
      return { found: false, box: null, reason: 'degenerate_shape', debug: debug };
    }

    // ۶) نگاشت به مختصات اصلی + حاشیه امن
    var mx = Math.round(o.margin_ratio * w);
    var my = Math.round(o.margin_ratio * h);
    var bx = Math.max(0, Math.floor(comp.x / scale) - mx);
    var by = Math.max(0, Math.floor(comp.y / scale) - my);
    var bx2 = Math.min(w, Math.ceil((comp.x + comp.w) / scale) + mx);
    var by2 = Math.min(h, Math.ceil((comp.y + comp.h) / scale) + my);
    var bw2 = bx2 - bx, bh2 = by2 - by;
    if (bw2 < 40 || bh2 < 40) {
      return { found: false, box: null, reason: 'crop_too_small', debug: debug };
    }
    return {
      found: true,
      box: { x: bx, y: by, w: bw2, h: bh2 },
      reason: 'ok',
      debug: debug
    };
  }

  LBR.boxdetect = {
    DEFAULTS: DEFAULTS,
    detectLabelRegion: detectLabelRegion,
    // برای آزمون‌ها
    _internal: { sobelEdges: sobelEdges, dilate: dilate, largestComponent: largestComponent }
  };
})(typeof window !== 'undefined' ? window : globalThis);

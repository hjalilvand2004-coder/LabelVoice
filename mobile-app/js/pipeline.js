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
    var sum = 0, sqSum = 0, bright = 0, washed = 0, k;
    for (k = 0; k < n; k++) {
      var v = gray[k];
      sum += v;
      sqSum += v * v;
      if (v > 248) bright++;
      if (v >= 190 && v <= 246) washed++;
    }
    var meanBrightness = sum / n;
    // انحراف معیار سراسری (v1.7.0): برای رفع هشدار کاذب «شسته‌شده» لازم است —
    // عکس محصول روی میز روشن، washedRatio بالا دارد ولی کنتراست کم نیست
    var grayStd = Math.sqrt(Math.max(0, sqSum / n - meanBrightness * meanBrightness));
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
    // شستگی واقعی = میان‌روشن زیاد + کنتراست سراسری کم + میانگین روشن
    // (v1.7.0 — معادل شرط اصلاح‌شده در quality.py؛ بدون شرط کنتراست،
    // هر عکس محصول روی میز/پس‌زمینه روشن هشدار کاذب می‌گرفت)
    if (washedRatio > 0.55 && grayStd < 35 && meanBrightness > 200) {
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

  // تشخیص «همان ناحیه متن»: IoU بالا یا احتواء ≥ 0.55 «با قرینه متنی»
  // (v1.7.0 — معادل _same_region در pipeline.py؛ قرینه = زیررشته یا شباهت ≥ 0.6
  // تا کلمات همسایه با کادر همپوشان اشتباهاً یکی نشوند)
  function sameRegion(a, b, textA, textB) {
    if (iou(a, b) > 0.40) return true;
    var ax2 = a.x + a.w, ay2 = a.y + a.h;
    var bx2 = b.x + b.w, by2 = b.y + b.h;
    var ix = Math.max(0, Math.min(ax2, bx2) - Math.max(a.x, b.x));
    var iy = Math.max(0, Math.min(ay2, by2) - Math.max(a.y, b.y));
    var inter = ix * iy;
    if (inter <= 0) return false;
    var contained = (inter / (b.w * b.h)) >= 0.55 ||
      (inter / (a.w * a.h)) >= 0.55;
    if (!contained) return false;
    var ta = (textA || '').trim().toLowerCase();
    var tb = (textB || '').trim().toLowerCase();
    if (!ta || !tb) return false;
    if (ta.indexOf(tb) !== -1 || tb.indexOf(ta) !== -1) return true;
    return similarityRatio(ta, tb) >= 0.60;
  }

  // ---------- گیت کیفیت قطعه‌ها (v1.7.0 — معادل _filter_pieces) ----------
  // نماد محض، اطمینان خیلی پایین، قطعه کوتاه کم‌اطمینان و قطعه کوتاهِ
  // کادر-غول‌پیکر (شکست تحلیل چیدمان) حذف می‌شوند.
  // v1.8.0: تشخیص زبالهٔ ترکیب‌خطی — حرف فارسی + حرف لاتین در یک قطعه
  // (یا رقم فارسی + رقم لاتین) فقط محصول خوانش خراب است.
  function isMixedScriptGarbage(text) {
    var t = text || '';
    var faLetter = /[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]/.test(t);
    var latLetter = /[a-zA-Z\u00C0-\u024F]/.test(t);
    if (faLetter && latLetter) return true;
    var faDigit = /[\u06F0-\u06F9\u0660-\u0669]/.test(t);
    var latDigit = /[0-9]/.test(t);
    if (faDigit && latDigit) return true;
    return false;
  }

  function filterPieces(raw, imageArea, settings) {
    var out = [];
    (raw || []).forEach(function (p) {
      var text = (p.text || '').trim();
      if (!text) return;
      if (isMixedScriptGarbage(text)) return; // v1.8.0
      if (p.confidence !== null && p.confidence !== undefined &&
        p.confidence < 0.30) return; // piece_conf_floor
      var hasAlnum = /[\p{L}\p{N}]/u.test(text);
      if (!hasAlnum) return;
      var alnumN = (text.match(/[\p{L}\p{N}]/gu) || []).length;
      if (text.length <= 2 && (p.confidence === null || p.confidence === undefined ||
        p.confidence < 0.30)) return; // short_piece_conf_min (برابر کف مطلق تا
      // واحدهای معنی‌دار کم‌اطمینان مثل «mg» حذف نشوند)
      if (imageArea && alnumN <= 2 && (p.w * p.h) > 0.15 * imageArea) return;
      out.push(p);
    });
    return out;
  }

  // امتیاز واریانت (معادل _score_variant): اطمینان × طول مؤثر قطعه‌های معتبر
  function scoreVariant(pieces) {
    var score = 0;
    (pieces || []).forEach(function (p) {
      if (p.confidence === null || p.confidence === undefined) return;
      var alnum = ((p.text || '').match(/[\p{L}\p{N}]/gu) || []).length;
      if (alnum < 2) return;
      score += p.confidence * Math.min(alnum, 14);
    });
    return score;
  }

  // v1.8.0-د: کادر منحط — خیلی نازک/خیلی ریز (نقطه و خط) و نشان‌گردِ درشتِ
  // تک‌نویسه (مثل «۲۸» داخل دایره که به‌صورت «۵» با کادر مربعی می‌آید).
  function isDegenerateBox(p) {
    var w = p.bbox.w, h = p.bbox.h;
    if (h < 12 || w < 3) return true;
    var t = (p.text || '').trim();
    if ((w * h) < 60 && t.length <= 2) return true;
    var alnumN = ((t.match(/[\p{L}\p{N}]/gu) || []).length);
    if (alnumN <= 2 && (w * h) >= 8000) {
      var longSide = Math.max(w, h), shortSide = Math.min(w, h);
      if (shortSide > 0 && longSide / shortSide <= 1.6) return true;
    }
    return false;
  }

  // فیلتر اجماعی (v1.8.0 — معادل _apply_consensus_filter): قطعهٔ تک‌رأیِ
  // کم‌اطمینان حذف می‌شود؛ کوتاه‌ها سخت‌گیری بیشتری دارند.
  function applyConsensusFilter(pieces) {
    var minN = 6, lonelyConf = 0.55;
    if ((pieces || []).length < minN) {
      var kept = pieces.filter(function (p) { return !isDegenerateBox(p); });
      return kept.length ? kept : pieces;
    }
    var out = [];
    pieces.forEach(function (p) {
      if (isDegenerateBox(p)) return;
      var support = p.support || 1;
      var conf = p.confidence;
      if (support <= 1) {
        var alnum = ((p.text || '').match(/[\p{L}\p{N}]/gu) || []).length;
        var floor = alnum <= 2 ? Math.max(lonelyConf, 0.80) : lonelyConf;
        if (conf === null || conf === undefined || conf < floor) return;
      }
      out.push(p);
    });
    return out.length ? out : pieces;
  }

  // ادغام بهترین-اول (v1.7.0 + v1.8.0 — معادل _merge_pieces_best_first):
  // واریانت با بیشترین امتیاز مبناست؛ بقیه فقط نواحی پوشش‌نداده را پر می‌کنند.
  // v1.8.0: رأی اجماعی (support) + دو گذر (سالم‌ها اول، فشرده‌ها بعد) +
  // قوانین جایگزینی محافظه‌کارانه برای عبارت چندواژه‌ای در برابر کلمهٔ دقیق.
  function mergePiecesBestFirst(byVariant) {
    var order = Object.keys(byVariant || {}).map(function (k) {
      return { name: k, pieces: byVariant[k] };
    }).sort(function (a, b) { return scoreVariant(b.pieces) - scoreVariant(a.pieces); });
    var normalItems = [], squeezedItems = [];
    order.forEach(function (v) {
      v.pieces.forEach(function (rp) {
        var norm = tn.normalizeForMatching(rp.text);
        var nWords = norm.split(/\s+/).filter(Boolean).length;
        var isSqueezed = nWords >= 2 && rp.h > 0 && rp.w < 1.6 * rp.h * nWords;
        (isSqueezed ? squeezedItems : normalItems).push(rp);
      });
    });
    var kept = [];
    [false, true].forEach(function (passSqueezed) {
      var items = passSqueezed ? squeezedItems : normalItems;
      items.forEach(function (rp) {
        var bb = { x: rp.x, y: rp.y, w: rp.w, h: rp.h };
        var norm = tn.normalizeForMatching(rp.text);
        var normL = norm.toLowerCase();
        var duplicated = false;
        for (var i = 0; i < kept.length; i++) {
          var ex = kept[i];
          if (!sameRegion(ex.bbox, bb, ex.text, rp.text)) continue;
          // قطعهٔ فشرده در گذر دوم فقط رأی می‌دهد
          if (!passSqueezed) {
            var exNorm = ex.normalized_text.toLowerCase();
            var confRp = rp.confidence || 0;
            var confEx = ex.confidence || 0;
            if (exNorm !== normL) {
              if (normL.indexOf(exNorm) !== -1 || exNorm.indexOf(normL) !== -1) {
                var lenGap = Math.abs(normL.length - exNorm.length);
                var longerNew = normL.length > exNorm.length;
                var winnerNew;
                if (lenGap >= 2) {
                  var multiIn = normL.split(/\s+/).filter(Boolean).length >= 2;
                  var multiEx = exNorm.split(/\s+/).filter(Boolean).length >= 2;
                  if (longerNew) {
                    winnerNew = multiIn ? (confRp >= confEx) : (confRp >= 0.5);
                  } else {
                    winnerNew = multiEx ? (confRp >= confEx + 0.15) : (confEx < 0.5);
                  }
                } else if (lenGap === 1) {
                  winnerNew = longerNew ? (confRp >= confEx - 0.05)
                    : (confRp < confEx - 0.05);
                } else {
                  winnerNew = confRp > confEx;
                }
                if (winnerNew) {
                  ex.text = rp.text; ex.normalized_text = norm;
                  ex.confidence = rp.confidence; ex.variant = rp.variant;
                }
              } else {
                var longer = normL.length > exNorm.length;
                var sameLenBetter = normL.length === exNorm.length && confRp > confEx;
                if ((longer || sameLenBetter) && confRp >= confEx * 0.9) {
                  ex.text = rp.text; ex.normalized_text = norm;
                  ex.confidence = rp.confidence; ex.variant = rp.variant;
                }
              }
            }
          }
          ex.support = (ex.support || 1) + 1;
          duplicated = true;
          break;
        }
        if (!duplicated) {
          kept.push({
            id: '', text: rp.text, normalized_text: norm, bbox: bb,
            confidence: rp.confidence, variant: rp.variant, engine: rp.engine,
            support: 1
          });
        }
      });
    });
    return applyConsensusFilter(kept);
  }

  // حذف قطعه‌های تکراری بین نسخه‌ها (IoU بالا + متن یکسان) — مسیر قدیمی (سازگاری آزمون‌ها)
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

  // حذف خوانش‌های جایگزینِ یک جایگاه در یک سطر (v1.8.0 — معادل _dedupe_column_reads)
  function dedupeColumnReads(sub) {
    function strength(p) {
      var conf = (p.confidence === null || p.confidence === undefined) ? 0.4 : p.confidence;
      return conf * (1.0 + 0.25 * ((p.support || 1) - 1));
    }
    var out = [];
    sub.slice().sort(function (a, b) { return strength(b) - strength(a); })
      .forEach(function (piece) {
        var px0 = piece.bbox.x, px1 = piece.bbox.x + piece.bbox.w;
        var overlaps = false;
        for (var i = 0; i < out.length; i++) {
          var kx0 = out[i].bbox.x, kx1 = out[i].bbox.x + out[i].bbox.w;
          var inter = Math.min(px1, kx1) - Math.max(px0, kx0);
          if (inter <= 0) continue;
          var minW = Math.max(1, Math.min(px1 - px0, kx1 - kx0));
          if (inter / minW > 0.60) { overlaps = true; break; }
        }
        if (!overlaps) out.push(piece);
      });
    return out;
  }

  // سطرهای منطقی ساخته‌شده از قطعات OCR — v1.8.0 (بازنویسی معادل پایتون):
  // تلورانس Y نسبی (میانگین گروه + ارتفاع ورودی)، شکست ستونی با فاصلهٔ افقی
  // بزرگ، و حذف خوانش هم‌ستون.
  function buildLines(pieces) {
    if (!pieces.length) return [];
    var ordered = pieces.slice().sort(function (a, b) {
      return ((a.bbox.y + (a.bbox.h >> 1)) - (b.bbox.y + (b.bbox.h >> 1))) ||
        (a.bbox.x - b.bbox.x);
    });
    // --- گروه‌بندی سطری با تلورانس نسبی ---
    var groups = [];
    var cur = [], curMeanYc = 0;
    ordered.forEach(function (piece) {
      var yc = piece.bbox.y + (piece.bbox.h >> 1);
      if (!cur.length) {
        cur = [piece];
        curMeanYc = yc;
        return;
      }
      var localH = cur.reduce(function (s, p) { return s + p.bbox.h; }, 0) / cur.length;
      var tol = Math.max(10, 0.55 * (localH + piece.bbox.h) / 2);
      if (Math.abs(yc - curMeanYc) <= tol) {
        cur.push(piece);
        curMeanYc = (curMeanYc * (cur.length - 1) + yc) / cur.length;
      } else {
        groups.push(cur);
        cur = [piece];
        curMeanYc = yc;
      }
    });
    if (cur.length) groups.push(cur);

    var lines = [];
    var gi = 0;
    groups.forEach(function (group0) {
      // --- شکست ستونی داخل هر گروه ---
      group0.sort(function (a, b) { return a.bbox.x - b.bbox.x; });
      var subGroups = [[group0[0]]];
      for (var k = 1; k < group0.length; k++) {
        var piece = group0[k];
        var prev = subGroups[subGroups.length - 1][subGroups[subGroups.length - 1].length - 1];
        var gap = piece.bbox.x - (prev.bbox.x + prev.bbox.w);
        if (gap > 4.5 * Math.max(piece.bbox.h, prev.bbox.h, 14)) {
          subGroups.push([piece]);
        } else {
          subGroups[subGroups.length - 1].push(piece);
        }
      }
      subGroups.forEach(function (sub0) {
        gi++;
        var sub = dedupeColumnReads(sub0);
        sub = dedupeSimilarPieces(sub);
        if (!sub.length) return;
        sub.sort(function (a, b) { return a.bbox.x - b.bbox.x; });
        var joined = sub.map(function (p) { return p.text; }).join(' ');
        if (tn.isMostlyPersian(joined)) sub = sub.slice().reverse();
        var text = sub.map(function (p) { return p.text; }).join(' ').trim();
        var norm = tn.normalizeForMatching(text);
        var x0 = Math.min.apply(null, sub.map(function (p) { return p.bbox.x; }));
        var y0 = Math.min.apply(null, sub.map(function (p) { return p.bbox.y; }));
        var x1 = Math.max.apply(null, sub.map(function (p) { return p.bbox.x + p.bbox.w; }));
        var y1 = Math.max.apply(null, sub.map(function (p) { return p.bbox.y + p.bbox.h; }));
        var confs = sub
          .filter(function (p) { return p.confidence !== null && p.confidence !== undefined; })
          .map(function (p) { return p.confidence; });
        lines.push({
          id: 'line_' + ('000' + gi).slice(-3),
          text: text,
          normalized_text: norm,
          source_ids: sub.map(function (p) { return p.id; }),
          bbox: { x: x0, y: y0, w: Math.max(1, x1 - x0), h: Math.max(1, y1 - y0) },
          confidence_mean: confs.length
            ? Math.round((confs.reduce(function (s, c) { return s + c; }, 0) / confs.length) * 1000) / 1000
            : null
        });
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
  // extra.onStage: اختیاری — اعلام مرحله‌به‌مرحله مطابق ملزومات استاد (v1.6.0)
  //   onStage('fields', payload) و onStage('response', payload)
  function buildResultFromPieces(rawPieces, settings, imageW, imageH, durations, extra) {
    extra = extra || {};
    var onStage = typeof extra.onStage === 'function' ? extra.onStage : null;
    var tStage = performance.now();
    var pieces;
    if (extra.byVariant) {
      // v1.7.0: ادغام بهترین-اول با گیت کیفیت قطعه‌ها
      var byVariant = {};
      var imageArea = (imageW && imageH) ? (imageW * imageH) : null;
      Object.keys(extra.byVariant).forEach(function (k) {
        byVariant[k] = filterPieces(extra.byVariant[k], imageArea, settings);
      });
      pieces = mergePiecesBestFirst(byVariant);
    } else {
      pieces = mergePieces(rawPieces);
    }
    var rawLines = buildLines(pieces);
    var cls = extractor.classifyProductType(rawLines.map(function (l) { return l.normalized_text; }));
    var ex = extractor.extractFields(rawLines, cls.type, settings, imageH);
    var extractMs = Math.round(performance.now() - tStage);
    if (onStage) {
      var statusCounts = {};
      Object.keys(ex.fields).forEach(function (k) {
        var st = ex.fields[k].status;
        statusCounts[st] = (statusCounts[st] || 0) + 1;
      });
      var extractedN = (statusCounts.extracted || 0) + (statusCounts.user_corrected || 0);
      var withEv = 0;
      Object.keys(ex.fields).forEach(function (k) {
        var f = ex.fields[k];
        if ((f.status === 'extracted' || f.status === 'user_corrected') && f.source_ids && f.source_ids.length) withEv++;
      });
      onStage('fields', {
        status_counts: statusCounts,
        evidence_coverage: extractedN ? Math.round(100 * withEv / extractedN) : 100,
        product_type_fa: cls.type === 'medicine' ? 'دارو' :
          (cls.type === 'general_product' ? 'محصول عمومی' : 'نامشخص'),
        warnings_fa: ex.warnings || [],
        duration_ms: extractMs
      });
    }
    var tResp = performance.now();
    var responseFa = responder.buildResponse(ex.fields, extra.qualityIssues || [], ex.warnings, pieces.length, cls.type);
    var selfCheck = guard.validateText(responseFa);
    if (!selfCheck.ok) {
      // حکمتی برای خطای سازنده؛ پاسخ امن حداقلی جایگزین می‌شود
      responseFa = 'پاسخ تولیدشده از قواعد ایمنی عبور نکرد؛ لطفاً تصویر واضح‌تری ارائه دهید. ' +
        responder.buildResponse({}, extra.qualityIssues || [], [], 0);
      selfCheck = guard.validateText(responseFa);
    }
    if (onStage) {
      onStage('response', {
        guard_ok: !!selfCheck.ok,
        guard_violations: (selfCheck.violations || []),
        llm_used: false,
        length: responseFa.length,
        preview: responseFa.slice(0, 200),
        duration_ms: Math.round(performance.now() - tResp)
      });
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
        app_version: '1.7.0-mobile'
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
    sameRegion: sameRegion,
    filterPieces: filterPieces,
    scoreVariant: scoreVariant,
    mergePiecesBestFirst: mergePiecesBestFirst,
    mergePieces: mergePieces,
    assignIds: assignIds,
    dedupeSimilarPieces: dedupeSimilarPieces,
    buildLines: buildLines,
    scoreOcrYield: scoreOcrYield,
    buildResultFromPieces: buildResultFromPieces,
    applyUserCorrections: applyUserCorrections
  };
})(typeof window !== 'undefined' ? window : globalThis);

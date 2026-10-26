/* LabelVoice TTS v2.12.3 — موتور صوتی کاملاً لوکال (Piper فارسی)
 *
 * v2.12.0 — «مدل دانلودشده در فایل‌های پروژه؛ بدون هیچ سرویس اینترنتی»:
 *   - مدل: VITS Piper «fa_IR-amir-medium» (نسخهٔ کوانتیزهٔ int8 — ۱۸.۶MB)
 *     منبع وزن‌ها: rhasspy/piper-voices v1.0.0 (لایسنس MIT)
 *   - فونِم‌سازی: espeak-ng (WASM piper-phonemize؛ دادهٔ تریم‌شدهٔ fa+en)
 *   - اجرا: onnxruntime-web 1.18 (WASM/SIMD) — همهٔ فایل‌ها داخل vendor/tts/
 *   - هیچ درخواستی به اینترنت صادر نمی‌شود؛ speechSynthesis/TTS گوشی هم
 *     به‌کلی استفاده نمی‌شود (v2.11.0 سرویس آنلاین Edge بود که حذف شد).
 *
 * API عمومی (سازگار با v2.11.0):
 *   LVTts.speak(text, {rate, onStatus}) → Promise<{via:'local', bytes}>
 *   LVTts.stop() · LVTts.playBytes(bytes) · LVTts.voices · LVTts.defaultVoice
 */
(function (global) {
  'use strict';

  var VERSION = '2.12.3';
  var VOICE_ID = 'fa_IR-amir-medium';
  var VOICE_LABEL = 'امیر — Piper فارسی (لوکال، int8)';
  var DEFAULT_RATE = '+0%';
  var CHUNK_MAX = 240;

  /* مسیر دارایی‌ها نسبت به ریشهٔ برنامه (index.html) */
  var ASSETS = {
    ortJs: './vendor/tts/ort.wasm.min.js',
    glue: './vendor/tts/piper-phonemize.js',
    phonemizeWasm: './vendor/tts/piper_phonemize.wasm',
    phonemizeData: './vendor/tts/piper_phonemize.data',
    model: './vendor/tts/fa_IR-amir-medium.int8.onnx',
    config: './vendor/tts/fa_IR-amir-medium.onnx.json'
  };

  var cfg = null;          /* محتوای fa_IR-amir-medium.onnx.json */
  var ortRef = null;       /* ماژول onnxruntime-web (UMD → global.ort) */
  var glueMod = null;      /* ماژول ESM گلو (createPiperPhonemize) */
  var session = null;      /* InferenceSession آماده */
  var currentAudio = null;

  /* در نسخهٔ تک‌فایلی، دارایی‌ها با data: URL از __LBR_TTS_ASSETS__ می‌آیند */
  function rurl(p) {
    var map = global.__LBR_TTS_ASSETS__;
    return (map && map[p]) ? map[p] : p;
  }

  /* import() پویا در اسکریپت کلاسیک مسیر نسبی را نسبت به URL خودِ اسکریپت
     حل می‌کند (نه سند)؛ پس مسیر گلو را صریحاً مطلق می‌کنیم. */
  function absUrl(p) {
    try { return new URL(p, (global.document && global.document.baseURI) || global.location.href).href; }
    catch (e) { return p; }
  }

  function faError(fa) {
    var e = new Error(fa);
    e.fa = fa;
    return e;
  }

  /* v2.12.3: اگر صفحه با file:// باز شده باشد، fetch() مسدود می‌شود و خطا
     بدون پیام فارسی به رابط می‌رسید (پیغام عمومی گمراه‌کننده). اکنون از
     همان ابتدا تشخیص داده و راهنمای دقیق فارسی نشان داده می‌شود. */
  function isFileProtocol() {
    try { return global.location && global.location.protocol === 'file:'; }
    catch (e) { return false; }
  }

  /* v2.12.3: پوشش خطاهای شبکه‌ای fetch (TypeError بدون fa) با پیام فارسی */
  function wrapFetchError(err, asset) {
    if (err && err.fa) return err;
    if (isFileProtocol()) {
      return faError('این صفحه با file:// باز شده است؛ مرورگر بارگیری فایل‌های مدل صوتی را مسدود می‌کند.' +
        ' لطفاً "START-WINDOWS.bat" را اجرا کنید (سرور محلی) یا از فایل تک‌فایلی "label-reader-singlefile.html" استفاده کنید.');
    }
    return faError('بارگیری فایل مدل صوتی ناموفق بود (' + asset + ')' +
      (err && err.message ? ': ' + err.message : '') +
      '. فایل‌های vendor/tts باید کنار برنامه باشند و صفحه از طریق سرور محلی (START-WINDOWS.bat) باز شود.');
  }

  /* ---------- ابزارهای خالص (آزمون‌پذیر در Node) ---------- */

  /** «+10%» → 1.1 و «-15%» → 0.85 — دامنهٔ مجاز 0.5..2.0 */
  function rateToSpeed(rate) {
    var m = /^[+-]\d{1,3}%$/.test(String(rate || '')) ? parseInt(rate, 10) : 0;
    var s = 1 + (isNaN(m) ? 0 : m) / 100;
    return Math.max(0.5, Math.min(2.0, s));
  }

  /** پاک‌سازی متن برای فونِم‌ساز: حذف کاراکترهای کنترلی/ایموجی؛ حفظ ZWNJ فارسی */
  function cleanText(text) {
    var s = String(text || '');
    var out = '';
    for (var i = 0; i < s.length; i++) {
      var c = s.charCodeAt(i);
      if (c === 0x200c) { out += '\u200c'; continue; }  /* نیم‌فاصله — ضروری فارسی */
      if (c < 0x20 && c !== 0x0a) { continue; }         /* کنترلی به‌جز LF */
      if (c >= 0xd800 && c <= 0xdbff) { continue; }     /* emoji (surrogate) */
      if (c >= 0xdc00 && c <= 0xdfff) { continue; }
      out += s.charAt(i);
    }
    return out.replace(/[ \t]+/g, ' ').replace(/\n{2,}/g, '\n').trim();
  }

  /** شکستن متن به قطعه‌های ≤ maxLen روی مرز جملهٔ فارسی/انگلیسی */
  function chunkSentences(text, maxLen) {
    maxLen = maxLen || CHUNK_MAX;
    var t = String(text || '');
    var parts = [], buf = '', i, ch;
    for (i = 0; i < t.length; i++) {      /* بدون lookbehind — سازگار با WebView قدیمی */
      ch = t.charAt(i);
      buf += ch;
      if ('.!؟?؛;:\n'.indexOf(ch) >= 0) { parts.push(buf); buf = ''; }
    }
    if (buf) parts.push(buf);
    var chunks = [], cur = '';
    for (i = 0; i < parts.length; i++) {
      var p = parts[i];
      if (!p.trim()) continue;
      if (cur && (cur.length + p.length) > maxLen) { chunks.push(cur); cur = p; }
      else { cur += p; }
      while (cur.length > maxLen) {       /* جملهٔ خیلی بلند → برش سخت */
        chunks.push(cur.slice(0, maxLen));
        cur = cur.slice(maxLen);
      }
    }
    if (cur.trim()) chunks.push(cur);
    return chunks.filter(function (c) { return c.trim().length > 0; });
  }

  /** سرگذاشتن WAV 16بیتی مونو — خروجی Uint8Array (آزمون‌پذیر) */
  function encodeWav(samples, sampleRate) {
    var n = samples.length, bytesPer = 2, header = 44;
    var buf = new ArrayBuffer(header + n * bytesPer);
    var v = new DataView(buf);
    function u32(o, x) { v.setUint32(o, x, true); }
    function u16(o, x) { v.setUint16(o, x, true); }
    u32(0, 0x46464952);            /* RIFF (LE بایت‌ها: R,I,F,F) */
    u32(4, buf.byteLength - 8);
    u32(8, 0x45564157);            /* WAVE */
    u32(12, 0x20746D66);           /* fmt  */
    u32(16, 16); u16(20, 1); u16(22, 1);
    u32(24, sampleRate);
    u32(28, sampleRate * bytesPer);
    u16(32, bytesPer); u16(34, 16);
    u32(36, 0x61746164);           /* data */
    u32(40, n * bytesPer);
    var off = header;
    for (var i = 0; i < n; i++) {
      var s = samples[i];
      v.setInt16(off, s >= 1 ? 32767 : (s <= -1 ? -32768 : (s * 32768) | 0), true);
      off += bytesPer;
    }
    return new Uint8Array(buf);
  }

  /* ---------- بارگیری اجزا ---------- */

  function loadScript(url) {
    return new Promise(function (resolve, reject) {
      var s = document.createElement('script');
      s.src = url;
      s.onload = function () { resolve(); };
      s.onerror = function () {
        reject(faError('بارگیری موتور اجرا (onnxruntime) ناموفق بود. برنامه را از طریق سرور محلی باز کنید.'));
      };
      document.head.appendChild(s);
    });
  }

  function ensureConfig() {
    if (cfg) return Promise.resolve();
    if (isFileProtocol() && !global.__LBR_TTS_ASSETS__) {
      return Promise.reject(faError('این صفحه با file:// باز شده است؛ بارگیری مدل صوتی در این حالت مسدود می‌شود.' +
        ' لطفاً "START-WINDOWS.bat" را اجرا کنید (سرور محلی) یا از فایل تک‌فایلی "label-reader-singlefile.html" استفاده کنید.'));
    }
    return fetch(rurl(ASSETS.config)).then(function (r) {
      if (!r.ok) throw faError('پیکربندی مدل صوتی یافت نشد (' + ASSETS.config + ').');
      return r.json();
    }).then(function (j) {
      if (!j || !j.espeak || !j.audio || !j.inference) {
        throw faError('پیکربندی مدل صوتی نامعتبر است.');
      }
      cfg = j;
    }).catch(function (err) {
      throw wrapFetchError(err, ASSETS.config);
    });
  }

  function ensureOrt() {
    if (global.ort) { ortRef = global.ort; return Promise.resolve(); }
    return loadScript(rurl(ASSETS.ortJs)).then(function () {
      if (!global.ort) throw faError('موتور اجرا (ort) بارگیری نشد.');
      ortRef = global.ort;
      /* ort ≥1.19: لودر، mjs و wasm را از wasmPaths می‌گیرد؛
         در تک‌فایل هر دو data: URL هستند (rurl)، در حالت عادی فایل لوکال. */
      ortRef.env.wasm.wasmPaths = {
        mjs: absUrl(rurl('./vendor/tts/ort-wasm-simd-threaded.mjs')),
        wasm: absUrl(rurl('./vendor/tts/ort-wasm-simd-threaded.wasm'))
      };
      ortRef.env.wasm.numThreads = 1;      /* بدون COOP/COEP تک‌نخی پایدار است */
    });
  }

  function ensureGlue() {
    if (glueMod) return Promise.resolve();
    /* قطعهٔ ESM با import() پویا — همهٔ مرورگرهای مدرن و WebView اندروید */
    return import(absUrl(rurl(ASSETS.glue))).then(function (m) {
      if (!m || typeof m.createPiperPhonemize !== 'function') {
        throw faError('ماژول فونِم‌ساز نامعتبر است.');
      }
      glueMod = m;
    }).catch(function (err) {
      if (err && err.fa) throw err;
      throw faError('بارگیری ماژول فونِم‌ساز ناموفق بود (' +
        (err && err.message ? err.message : err) +
        '). صفحه باید از طریق سرور محلی (http) باز شود، نه file://.');
    });
  }

  function ensureSession(onStatus) {
    if (session) return Promise.resolve();
    if (onStatus) onStatus('بارگیری مدل صوتی (۱۸.۶ مگابایت — فقط بار اول)…');
    return fetch(rurl(ASSETS.model)).then(function (r) {
      if (!r.ok) throw faError('مدل صوتی یافت نشد (' + ASSETS.model + ').');
      return r.arrayBuffer();
    }).then(function (buf) {
      if (onStatus) onStatus('آماده‌سازی مدل صوتی در حافظه…');
      return ortRef.InferenceSession.create(new Uint8Array(buf), {
        executionProviders: ['wasm'],
        graphOptimizationLevel: 'all'
      }).catch(function (err) {
        /* v2.12.3: خطای ساخت نشست ort (مثلاً شکست import ماژول mjs با
           MIME نادرست در سرور محلی) بدون fa بود و پیغام عمومی می‌داد */
        throw faError('راه‌اندازی موتور اجرا (onnxruntime) ناموفق بود' +
          (err && err.message ? ': ' + err.message : '') +
          '. اگر صفحه را با سرور محلی (START-WINDOWS.bat) باز کرده‌اید، لطفاً از نسخهٔ جدید بسته اطمینان حاصل کنید.');
      });
    }).then(function (s) { session = s; })
      .catch(function (err) {
        throw (err && err.fa) ? err : wrapFetchError(err, ASSETS.model);
      });
  }

  /** فونِم‌سازی یک قطعه — هر بار نمونهٔ تازهٔ ماژول (الگوی رسمی piper-web) */
  var _phonemeIdsResolve = null, _phonemeIdsReject = null;

  function phonemizeChunk(text) {
    return glueMod.createPiperPhonemize({
      print: function (line) {
        if (_phonemeIdsResolve) {
          try {
            var ids = JSON.parse(line).phoneme_ids;
            _phonemeIdsResolve(ids);
          } catch (e) {
            _phonemeIdsReject(faError('خروجی فونِم‌ساز قابل خواندن نبود.'));
          }
        }
      },
      printErr: function () { /* لاگ خاموش؛ شکست با timeout گزارش می‌شود */ },
      locateFile: function (f) {
        if (f.endsWith('.wasm')) return rurl(ASSETS.phonemizeWasm);
        if (f.endsWith('.data')) return rurl(ASSETS.phonemizeData);
        return f;
      }
    }).then(function (mod) {
      return new Promise(function (resolve, reject) {
        var settled = false;
        _phonemeIdsResolve = function (ids) {
          if (settled) return;
          settled = true;
          resolve(ids);
        };
        _phonemeIdsReject = function (err) {
          if (settled) return;
          settled = true;
          reject(err);
        };
        try {
          mod.callMain([
            '-l', (cfg && cfg.espeak && cfg.espeak.voice) || 'fa',
            '--input', JSON.stringify([{ text: text }]),
            '--espeak_data', '/espeak-ng-data'
          ]);
        } catch (e) {
          _phonemeIdsReject(faError('فونِم‌سازی متن ناموفق بود.'));
          return;
        }
        setTimeout(function () {
          _phonemeIdsReject(faError('فونِم‌سازی بیش از حد طول کشید.'));
        }, 30000);
      });
    });
  }

  /** استنتاج یک قطعه → Float32Array صدا */
  function inferChunk(ids) {
    var inf = cfg.inference;
    var speed = _currentSpeed;
    var feeds = {
      input: new ortRef.Tensor('int64', BigUint64ArrayFromIds(ids), [1, ids.length]),
      input_lengths: new ortRef.Tensor('int64', BigInt64From([ids.length]), [1]),
      scales: new ortRef.Tensor('float32',
        new Float32Array([inf.noise_scale, inf.length_scale / speed, inf.noise_w]), [3])
    };
    if (cfg.speaker_id_map && Object.keys(cfg.speaker_id_map).length) {
      feeds.sid = new ortRef.Tensor('int64', BigInt64From([0]), [1]);
    }
    return session.run(feeds).then(function (out) {
      var key = 'output' in out ? 'output' : Object.keys(out)[0];
      return out[key].data;
    });
  }

  function BigUint64ArrayFromIds(ids) {
    var a = new BigInt64Array(ids.length);
    for (var i = 0; i < ids.length; i++) a[i] = BigInt(ids[i] | 0);
    return a;
  }
  function BigInt64From(arr) {
    var a = new BigInt64Array(arr.length);
    for (var i = 0; i < arr.length; i++) a[i] = BigInt(arr[i]);
    return a;
  }

  /* ---------- نقطهٔ ورود اصلی ---------- */
  /**
   * speak(text, opts) → Promise<{via:'local', bytes}>
   * opts: { rate: '+10%', onStatus: fn }
   * کاملاً لوکال: مدل داخل فایل‌های پروژه است و هیچ درخواست شبکه‌ای به بیرون
   * نمی‌رود؛ متن فقط در همین دستگاه به صدا تبدیل می‌شود.
   */
  function speak(text, opts) {
    opts = opts || {};
    var onStatus = typeof opts.onStatus === 'function' ? opts.onStatus : function () {};
    var clean = cleanText(text);
    if (!clean) {
      return Promise.reject(faError('متنی برای خواندن وجود ندارد.'));
    }
    _currentSpeed = rateToSpeed(opts.rate);
    stop();

    var chunks = chunkSentences(clean);
    if (!chunks.length) return Promise.reject(faError('متنی برای خواندن وجود ندارد.'));

    onStatus('آماده‌سازی موتور صوتی لوکال…');
    return ensureConfig()
      .then(function () { return ensureOrt(); })
      .then(function () { return ensureGlue(); })
      .then(function () { return ensureSession(onStatus); })
      .then(function () {
        var collected = [];
        var chain = Promise.resolve();
        chunks.forEach(function (ch, idx) {
          chain = chain.then(function () {
            onStatus('تولید صدا با مدل Piper (لوکال) — بخش ' +
              (idx + 1) + ' از ' + chunks.length + '…');
            return phonemizeChunk(ch).then(function (ids) {
              if (!ids || !ids.length) {
                throw faError('هیچ فونمی از متن ساخته نشد (کاراکترهای پشتیبانی‌نشده؟)');
              }
              return inferChunk(ids);
            }).then(function (samples) {
              for (var i = 0; i < samples.length; i++) collected.push(samples[i]);
            });
          });
        });
        return chain.then(function () {
          var rate = (cfg.audio && cfg.audio.sample_rate) || 22050;
          var wav = encodeWav(collected, rate);
          onStatus('صدا با مدل Piper فارسی (کاملاً لوکال) ساخته شد.');
          return { via: 'local', bytes: wav, rate: rate };
        });
      });
  }
  var _currentSpeed = 1.0;

  /** پخش Uint8Array صدا (WAV) — جایگزین speechSynthesis/TTS گوشی */
  function playBytes(bytes) {
    stop();
    var blob = new Blob([bytes], { type: 'audio/wav' });
    var url = URL.createObjectURL(blob);
    var audio = new Audio(url);
    currentAudio = audio;
    audio.onended = function () {
      if (currentAudio === audio) {
        try { URL.revokeObjectURL(url); } catch (e) { /* نادیده */ }
        currentAudio = null;
      }
    };
    var p = audio.play();
    if (p && typeof p.catch === 'function') {
      p.catch(function () { /* autoplay-block: کاربر همین حالا دکمه را زده */ });
    }
    return audio;
  }

  /* ---------- API عمومی ---------- */

  var LVTts = {
    version: VERSION,
    voices: [VOICE_LABEL],
    defaultVoice: VOICE_LABEL,
    voiceId: VOICE_ID,
    fullyLocal: true,
    speak: speak,
    stop: function () {
      if (currentAudio) {
        try { currentAudio.pause(); } catch (e) { /* نادیده */ }
        try { currentAudio.src = ''; } catch (e) { /* نادیده */ }
        currentAudio = null;
      }
    },
    playBytes: playBytes,
    engineReady: function () { return !!session; },
    /* قلاب‌های آزمون (پاریتی با پایتون) */
    _internal: {
      rateToSpeed: rateToSpeed,
      cleanText: cleanText,
      chunkSentences: chunkSentences,
      encodeWav: encodeWav,
      assets: ASSETS
    }
  };

  if (typeof module !== 'undefined' && module.exports) { module.exports = LVTts; }
  global.LVTts = LVTts;

})(typeof window !== 'undefined' ? window : this);

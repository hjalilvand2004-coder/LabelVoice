/* ============================================================
 * LVTts — تبدیل متن به گفتار مشترک وب/موبایل (v2.11.0)
 * ============================================================
 * خواستهٔ کاربر: «همان مدل دسکتاپ در موبایل، بدون TTS خود گوشی»
 *
 * مدل صوتی: همان مدل دسکتاپ = صداهای نورال فارسی Microsoft Edge
 * (fa-IR-FaridNeural / fa-IR-DilaraNeural) از سرویس edge-tts.
 * دو مسیر تولید صدا (هر دو «همان مدل» دسکتاپ‌اند):
 *   ۱) پل دسکتاپ  : POST {host}/api/tts  → همان کد پایتون label_reader/tts
 *   ۲) مستقیم      : WebSocket به سرویس مایکروسافت با پیاده‌سازی کامل
 *                    پروتکل edge-tts 7.3.1 (شامل توکن Sec-MS-GEC v2)
 * هیچ استفاده‌ای از speechSynthesis مرورگر یا TextToSpeech اندروید
 * انجام نمی‌شود (قرارداد محصول: خروجی صوتی یکسان در همهٔ رابط‌ها).
 *
 * حریم خصوصی: متن فقط با رضایت صریح کاربر و فقط برای همان یک درخواست
 * به سرویس ابری ارسال می‌شود؛ چیزی ذخیره نمی‌شود.
 *
 * برای آزمون‌های Node، این فایل به global هم متصل می‌شود (window اختیاری).
 */
(function (global) {
  'use strict';

  // ---------- ثابت‌های پروتکل (منبع حقیقت: edge-tts==7.3.1) ----------
  var TRUSTED_TOKEN = '6A5AA1D4EAFF4E9FB37E23D68491D6F4';
  var CHROMIUM_FULL_VERSION = '143.0.3650.75';
  var SEC_MS_GEC_VERSION = '2-' + CHROMIUM_FULL_VERSION;
  var WSS_BASE = ('wss://speech.platform.bing.com/consumer/speech/synthesize/readaloud/edge/v1' +
    '?TrustedClientToken=' + TRUSTED_TOKEN);
  var WIN_EPOCH = 11644473600;
  var OUTPUT_FORMAT = 'audio-24khz-48kbitrate-mono-mp3';
  var DEFAULT_VOICE = 'fa-IR-FaridNeural';
  var EDGE_VOICES = ['fa-IR-FaridNeural', 'fa-IR-DilaraNeural'];
  var SSML_CHUNK_BYTES = 2000;   // مرز امن زیر سقف ۴۰۹۶ بایتی سرویس
  var WS_OPEN_TIMEOUT_MS = 12000;
  var WS_TOTAL_TIMEOUT_MS = 45000;
  var BRIDGE_TIMEOUT_MS = 8000;
  /* قلاب‌های آزمون Node (تولید نهایی استفاده نمی‌کند) */
  var _wsCtorOverride = null;
  var _wsConnectOptions = null;
  var _uaOverride = null;

  // ---------- ثابت‌های DRM v2 (استخراج برنامه‌ای از edge_tts.drm) ----------
  var K_STD = [0x428A2F98, 0x71374491, 0xB5C0FBCF, 0xE9B5DBA5, 0x3956C25B, 0x59F111F1, 0x923F82A4, 0xAB1C5ED5, 0xD807AA98, 0x12835B01, 0x243185BE, 0x550C7DC3, 0x72BE5D74, 0x80DEB1FE, 0x9BDC06A7, 0xC19BF174, 0xE49B69C1, 0xEFBE4786, 0x0FC19DC6, 0x240CA1CC, 0x2DE92C6F, 0x4A7484AA, 0x5CB0A9DC, 0x76F988DA, 0x983E5152, 0xA831C66D, 0xB00327C8, 0xBF597FC7, 0xC6E00BF3, 0xD5A79147, 0x06CA6351, 0x14292967, 0x27B70A85, 0x2E1B2138, 0x4D2C6DFC, 0x53380D13, 0x650A7354, 0x766A0ABB, 0x81C2C92E, 0x92722C85, 0xA2BFE8A1, 0xA81A664B, 0xC24B8B70, 0xC76C51A3, 0xD192E819, 0xD6990624, 0xF40E3585, 0x106AA070, 0x19A4C116, 0x1E376C08, 0x2748774C, 0x34B0BCB5, 0x391C0CB3, 0x4ED8AA4A, 0x5B9CCA4F, 0x682E6FF3, 0x748F82EE, 0x78A5636F, 0x84C87814, 0x8CC70208, 0x90BEFFFA, 0xA4506CEB, 0xBEF9A3F7, 0xC67178F2];
  var INIT_STATE = [0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A, 0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19];
  var BLOCK_STATE = [0xFD9FBEA2, 0x91243CE7, 0xBE499094, 0xCD2E1E0A, 0x6C006F49, 0x04BD35AB, 0xFEB0A7E4, 0x03EFFBD2];
  var SCHED14 = [0xEB24BF9E, 0x1558691F, 0xA0C09EE2, 0x0CFA32BA, 0xA622EE8C, 0xD1DD9491, 0xC0DD25A0, 0xF9E70AB6, 0xF0C31573, 0x7058CE4E, 0x7188E606, 0x00E5AB33, 0xD258B060, 0x72766564];
  var BLOCK_K14 = 0xC9DC06A7;                    // جایگزین K[14] در بلوک نخست
  var SIGMA0_ADJ = 0x059C0B80, SIGMA1_ADJ = 0x000B92C0;
  var CS64_FACTOR = 0x82893933, CS64_ADJ0 = 0xF2F90B1A, CS64_ADJ1 = 0x0B1A0000;
  var CS64_COEFFS = [
    [0xE82E91B1, 0xB32700D0], [0x44DE24C6, 0x88DFF51D],
    [0x3BEB65BC, 0x29514038], [0xC89C5933, 0xB328CBDF],
    [0x8D1EC211, 0xD405B4D5], [0x314EF5D5, 0x26E55F3C],
    [0xE92491B1, 0x607801C6], [0xF0A5B9D5, 0x82B2C1FB],
    [0x06064CF3, 0xFA51A3DA], [0xDA79FA60, 0x207CC464],
    [0xBED20560, 0x3C3C74F3], [0x89F9C9F8, 0xD2D14B61],
    [0x35FA38C6, 0xBB04A2C1], [0xCB49E3C6, 0xC5626167]
  ];
  var BLOCK_K = K_STD.slice(0, 14).concat([BLOCK_K14], K_STD.slice(15));

  // ---------- ابزارهای بیتی ----------
  function rotr(x, n) { return ((x >>> n) | (x << (32 - n))) >>> 0; }
  function rol16(v) { v = v >>> 0; return ((v << 16) | (v >>> 16)) >>> 0; }
  // معادل _sigma0/_sigma1 پایتون (ترکیب شیفت‌ها با یک ماسک نهایی)
  function sigma0(v) { return ((v >>> 7) ^ (v << 25) ^ (v >>> 18) ^ (v << 14) ^ (v >>> 3)) >>> 0; }
  function sigma1(v) { return ((v >>> 17) ^ (v << 15) ^ (v >>> 19) ^ (v << 13) ^ (v >>> 10)) >>> 0; }

  function sha256Rounds(state, words, kArr, firstRound) {
    var a = state[0], b = state[1], c = state[2], d = state[3];
    var e = state[4], f = state[5], g = state[6], h = state[7];
    for (var i = firstRound; i < 64; i++) {
      var S1 = (rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)) >>> 0;
      var ch = (g ^ (e & (f ^ g))) >>> 0;
      // جمع پنج عبارت ۳۲بیتی در double دقیق است (< 2^53) سپس mod 2^32
      var t1 = (h + S1 + ch + kArr[i] + words[i]) >>> 0;
      var S0 = (rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)) >>> 0;
      var maj = ((a & b) | (c & (a | b))) >>> 0;
      var t2 = (S0 + maj) >>> 0;
      h = g; g = f; f = e; e = (d + t1) >>> 0;
      d = c; c = b; b = a; a = (t1 + t2) >>> 0;
    }
    return [a, b, c, d, e, f, g, h];
  }

  function expandSchedule(words, first) {
    for (var i = first; i < 64; i++) {
      var x = words[i - 2], y = words[i - 15];
      words[i] = (sigma1(x) + words[i - 7] + sigma0(y) + words[i - 16]) >>> 0;
    }
  }

  /* حالت اولیهٔ وابسته به داده — پورت مستقیم _sha256_init */
  function modifiedInit(data7) {
    var words = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
    words[14] = ((data7[0] << 16) | (data7[1] << 8) | data7[2]) >>> 0;
    words[15] = ((data7[3] << 24) | (data7[4] << 16) | (data7[5] << 8) | data7[6]) >>> 0;
    for (var index = 16; index < 30; index++) {
      var value = SCHED14[index - 16];
      if (index - 2 >= 14) {
        value += (index === 16)
          ? (sigma1(words[index - 2]) ^ SIGMA1_ADJ)
          : sigma1(words[index - 2]);
      }
      if (index - 7 >= 14) { value += words[index - 7]; }
      if (index - 15 >= 14) {
        value += (index === 29)
          ? (sigma0(words[index - 15]) ^ SIGMA0_ADJ)
          : sigma0(words[index - 15]);
      }
      words[index] = value >>> 0;
    }
    words[30] = (sigma1(words[28]) + words[23] + sigma0(words[15]) +
                 words[14] + BLOCK_K14 - K_STD[14]) >>> 0;
    expandSchedule(words, 31);
    var working = sha256Rounds(BLOCK_STATE, words, BLOCK_K, 14);
    var out = new Array(8);
    for (var i = 0; i < 8; i++) { out[i] = (INIT_STATE[i] + working[i]) >>> 0; }
    return out;
  }

  /* پورت مستقیم _sha256_digest — SHA-256 با حالت اولیهٔ وابسته به داده */
  function modifiedSha256(data) {
    if (data.length < 7) { throw new Error('token data too short'); }
    var length = 57 + data.length;
    var zeroCount = (((55 - length) % 64) + 64) % 64;
    var bodyLen = (data.length - 7) + 1 + zeroCount + 8;
    var padded = new Uint8Array(bodyLen);
    padded.set(data.subarray(7), 0);
    padded[data.length - 7] = 0x80;
    var dv = new DataView(padded.buffer);
    var bitLen = length * 8;
    dv.setUint32(bodyLen - 8, Math.floor(bitLen / 4294967296));
    dv.setUint32(bodyLen - 4, bitLen >>> 0);
    var state = modifiedInit(data.subarray(0, 7));
    for (var off = 0; off < bodyLen; off += 64) {
      var words = new Array(16);
      for (var j = 0; j < 16; j++) { words[j] = dv.getUint32(off + j * 4); }
      expandSchedule(words, 16);
      var working = sha256Rounds(state, words, K_STD, 0);
      for (var i2 = 0; i2 < 8; i2++) { state[i2] = (state[i2] + working[i2]) >>> 0; }
    }
    var out = new Uint8Array(32);
    var dv2 = new DataView(out.buffer);
    for (var i3 = 0; i3 < 8; i3++) { dv2.setUint32(i3 * 4, state[i3]); }
    return out;
  }

  /* پورت مستقیم _cs64_digest — همهٔ ضرب‌ها با Math.imul (۳۲ بیت پایین دقیق) */
  function cs64Digest(data, digest) {
    var dvD = new DataView(digest.buffer, digest.byteOffset, digest.byteLength);
    var key_a = dvD.getUint32(0, true) | 1;
    var key_b = dvD.getUint32(4, true) | 1;
    var f0 = Math.imul(key_a, CS64_FACTOR) >>> 0;
    var f1 = Math.imul(key_b, CS64_FACTOR) >>> 0;
    var terms = [], offsets = [], i, idx, p;
    for (i = 0; i < CS64_COEFFS.length; i++) {
      terms.push(Math.imul(CS64_COEFFS[i][0], (i % 2 === 0) ? f0 : f1) >>> 0);
      offsets.push(CS64_COEFFS[i][1]);
    }
    // _words_le4_even(b"\x00" + data) — کلمات ۳۲بیتی little-endian با صفر
    var padded = new Uint8Array(1 + data.length + ((-(1 + data.length)) % 4 + 4) % 4);
    padded[0] = 0;
    padded.set(data, 1);
    var wordCount = padded.length / 4;
    var wordsArr = [];
    for (var w = 0; w < wordCount; w++) {
      var base = w * 4;
      wordsArr.push((padded[base] | (padded[base + 1] << 8) |
                     (padded[base + 2] << 16) | (padded[base + 3] << 24)) >>> 0);
    }
    if (wordsArr.length % 2) { wordsArr.push(0); }
    for (idx = 0; idx < wordsArr.length; idx++) {
      var word = wordsArr[idx];
      var term = Math.imul(word, (idx % 2 === 0) ? key_a : key_b) >>> 0;
      var offset = Math.imul(rol16(word), (idx % 2 === 0) ? 0xEF0569FB : 0xC31713DB) >>> 0;
      if (idx === 0) {
        term = (term + Math.imul(CS64_ADJ0, f0)) >>> 0;
        offset = (offset + CS64_ADJ1) >>> 0;
      }
      terms.push(term);
      offsets.push(offset);
    }
    var swap_acc = 0, swap_last = 0, st = 0, acc = 0;
    for (p = 0; p < terms.length; p += 2) {
      var x = terms[p], y = terms[p + 1];
      var t = rol16((offsets[p] + x) >>> 0);
      var q = Math.imul(t, 0x76F50F34) >>> 0;
      swap_acc = (swap_acc + ((Math.imul(rol16(q), 0xC3EFEA97) + q) >>> 0)) >>> 0;
      var t2 = rol16((offsets[p + 1] + y) >>> 0);
      var q2 = Math.imul(t2, 0x1881CE3C) >>> 0;
      swap_last = ((Math.imul(rol16(q2), 0x35BD1EC9) + q2) >>> 0);
      swap_acc = (swap_acc + swap_last) >>> 0;

      st = (Math.imul(st, key_a) + x) >>> 0;
      st = Math.imul(rol16(st), 0xCF98B111) >>> 0;
      st = Math.imul(rol16(st), 0x87085B9F) >>> 0;
      st = Math.imul(rol16(st), 0x12CEB96D) >>> 0;
      st = Math.imul(rol16(st), 0x257E1D83) >>> 0;
      acc = (acc + st) >>> 0;
      var t3 = (Math.imul(st, key_b) + y) >>> 0;
      t3 = Math.imul(rol16(t3), 0xA27416F5) >>> 0;
      t3 = Math.imul(rol16(t3), 0xD38396FF) >>> 0;
      st = Math.imul(rol16(Math.imul(rol16(t3), 0x7C932B89) >>> 0), 0xBFA49F69) >>> 0;
      acc = (acc + st) >>> 0;
    }
    return [(swap_last ^ st) >>> 0, (swap_acc ^ acc) >>> 0];
  }

  /* پورت generate_sec_ms_gec_v2 — همان جریان عملیات float64 پایتون */
  function tokenAt(unixTs) {
    var ticks = unixTs + WIN_EPOCH;
    ticks = ticks - (ticks % 300);
    ticks = ticks * (1e9 / 100);
    var str = BigInt(ticks).toString() + TRUSTED_TOKEN;
    var data = new Uint8Array(str.length);
    for (var i = 0; i < str.length; i++) { data[i] = str.charCodeAt(i) & 0xFF; }
    var digest = modifiedSha256(data);
    var cs = cs64Digest(data, digest);
    // معادل struct.pack("<II", a, b).hex().upper() — هر کلمه little-endian
    function hex2(b) { return ('0' + b.toString(16)).slice(-2); }
    function hex8le(v) {
      return hex2(v & 0xFF) + hex2((v >>> 8) & 0xFF) +
             hex2((v >>> 16) & 0xFF) + hex2((v >>> 24) & 0xFF);
    }
    var hex = '';
    for (var j = 0; j < 32; j++) { hex += ('0' + digest[j].toString(16)).slice(-2); }
    return (hex8le(cs[0]) + hex8le(cs[1])).toUpperCase() + '-' + hex.toUpperCase();
  }

  // ---------- ابزارهای متن و زمان ----------
  function removeIncompatible(s) {
    // بازه‌های ناسازگار با سرویس با فاصله جایگزین می‌شوند (پورت دقیق edge-tts؛
    // ۹=Tab، ۱۰=LF و ۱۳=CR حفظ می‌شوند)
    var out = '';
    for (var i = 0; i < s.length; i++) {
      var c = s.charCodeAt(i);
      if ((c >= 0 && c <= 8) || (c >= 11 && c <= 12) || (c >= 14 && c <= 31)) {
        out += ' ';
      } else {
        out += s.charAt(i);
      }
    }
    return out;
  }
  function xmlEscape(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function utf8Bytes(s) {
    if (typeof TextEncoder !== 'undefined') { return new TextEncoder().encode(s); }
    // پشتیبان ساده برای محیط‌های قدیمی (آزمون)
    var out = [], i, c;
    for (i = 0; i < s.length; i++) {
      c = s.codePointAt(i);
      if (c > 0xFFFF) { i++; }
      if (c < 0x80) { out.push(c); }
      else if (c < 0x800) { out.push(0xC0 | (c >> 6), 0x80 | (c & 63)); }
      else if (c < 0x10000) { out.push(0xE0 | (c >> 12), 0x80 | ((c >> 6) & 63), 0x80 | (c & 63)); }
      else { out.push(0xF0 | (c >> 18), 0x80 | ((c >> 12) & 63), 0x80 | ((c >> 6) & 63), 0x80 | (c & 63)); }
    }
    return new Uint8Array(out);
  }
  function utf8Decode(bytes) {
    if (typeof TextDecoder !== 'undefined') {
      return new TextDecoder('utf-8').decode(bytes);
    }
    return decodeURIComponent(escape(String.fromCharCode.apply(null, bytes)));
  }
  var WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  function jsDateString() {
    // معادل date_to_string پایتون: "Wed Oct 25 19:36:00 2026 GMT+0000 (Coordinated Universal Time)"
    var d = new Date();
    function p2(n) { return (n < 10 ? '0' : '') + n; }
    return WEEKDAYS[d.getUTCDay()] + ' ' + MONTHS[d.getUTCMonth()] + ' ' +
      p2(d.getUTCDate()) + ' ' + d.getUTCFullYear() + ' ' +
      p2(d.getUTCHours()) + ':' + p2(d.getUTCMinutes()) + ':' + p2(d.getUTCSeconds()) +
      ' GMT+0000 (Coordinated Universal Time)';
  }
  function uuidHex() {
    var b = new Uint8Array(16);
    if (global.crypto && global.crypto.getRandomValues) {
      global.crypto.getRandomValues(b);
    } else {
      for (var i = 0; i < 16; i++) { b[i] = Math.floor(Math.random() * 256); }
    }
    var hex = '';
    for (var j = 0; j < 16; j++) { hex += ('0' + b[j].toString(16)).slice(-2); }
    return hex;
  }
  /* برش متن فرار-شده به قطعه‌های ≤ maxBytes بایت (ترجیح مرز فاصله/سطر) */
  function splitEscapedByBytes(escaped, maxBytes) {
    if (utf8Bytes(escaped).length <= maxBytes) { return [escaped]; }
    var parts = [], cur = '', buf = 0;
    var tokens = escaped.split(/(\s+)/);
    for (var i = 0; i < tokens.length; i++) {
      var tk = tokens[i];
      var n = utf8Bytes(tk).length;
      if (buf + n > maxBytes && cur) {
        parts.push(cur); cur = ''; buf = 0;
        if (/^\s+$/.test(tk)) { continue; }
      }
      // توکن‌های بسیار بلندتر از سقف: برش اجباری کاراکتری
      while (utf8Bytes(tk).length > maxBytes) {
        var lo = 1, hi = tk.length, cut = 1;
        while (lo <= hi) {
          var mid = (lo + hi) >> 1;
          if (utf8Bytes(tk.slice(0, mid)).length <= maxBytes) { cut = mid; lo = mid + 1; }
          else { hi = mid - 1; }
        }
        parts.push(tk.slice(0, cut));
        tk = tk.slice(cut);
      }
      if (tk) {
        cur += tk; buf += utf8Bytes(tk).length;
      }
    }
    if (cur) { parts.push(cur); }
    return parts;
  }

  // ---------- مسیر ۱: پل دسکتاپ (POST /api/tts — همان کد پایتون دسکتاپ) ----------
  function synthesizeViaBridge(host, text, opts) {
    var base = String(host || '').replace(/\/+$/, '');
    if (!base) { return Promise.reject(new Error('bridge-host-empty')); }
    var ctrl = (typeof AbortSignal !== 'undefined' && AbortSignal.timeout)
      ? { signal: AbortSignal.timeout(opts && opts.timeoutMs || BRIDGE_TIMEOUT_MS) } : {};
    return fetch(base + '/api/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: text,
        consent: true,
        voice: (opts && opts.voice) || DEFAULT_VOICE,
        rate: (opts && opts.rate) || '+0%'
      }),
      signal: ctrl.signal
    }).then(function (resp) {
      var ct = resp.headers.get('Content-Type') || '';
      if (resp.ok && ct.indexOf('audio') >= 0) { return resp.blob(); }
      return resp.json().catch(function () { return {}; }).then(function (j) {
        var err = new Error(j.error_fa || ('bridge-http-' + resp.status));
        err.fa = j.error_fa || ('پل دسکتاپ پاسخ ' + resp.status + ' داد.');
        throw err;
      });
    });
  }

  // ---------- مسیر ۲: کلاینت مستقیم سرویس edge-tts (پروتکل 7.3.1) ----------
  function synthChunkDirect(escapedText, voice, rate) {
    return new Promise(function (resolve, reject) {
      var token;
      try { token = tokenAt(Date.now() / 1000); }
      catch (e) { reject(new Error('token-generation-failed')); return; }
      var url = WSS_BASE + '&ConnectionId=' + uuidHex() +
        '&Sec-MS-GEC=' + token + '&Sec-MS-GEC-Version=' + SEC_MS_GEC_VERSION;
      var WS = _wsCtorOverride || global.WebSocket;
      if (!WS) { reject(new Error('websocket-unsupported')); return; }
      var ws;
      // آرگومان سوم در مرورگر نادیده گرفته می‌شود؛ در پکیج ws گزینه‌های اتصال است
      try { ws = new WS(url, undefined, _wsConnectOptions || undefined); } catch (e) { reject(e); return; }
      ws.binaryType = 'arraybuffer';
      var parts = [], finished = false, opened = false;
      var totalTimer = setTimeout(function () {
        cleanup(new Error('edge-timeout'));
      }, WS_TOTAL_TIMEOUT_MS);
      function finish() {
        if (finished) { return; }
        finished = true;
        clearTimeout(totalTimer);
        var size = 0, i;
        for (i = 0; i < parts.length; i++) { size += parts[i].length; }
        if (!size) { reject(new Error('edge-empty-audio')); return; }
        var out = new Uint8Array(size), pos = 0;
        for (i = 0; i < parts.length; i++) { out.set(parts[i], pos); pos += parts[i].length; }
        resolve(out);
      }
      function cleanup(err) {
        if (finished) { return; }
        finished = true;
        clearTimeout(totalTimer);
        try { ws.close(); } catch (e) { /* نادیده */ }
        reject(err);
      }
      ws.onopen = function () {
        opened = true;
        ws.send('X-Timestamp:' + jsDateString() +
          '\r\nContent-Type:application/json; charset=utf-8\r\nPath:speech.config\r\n\r\n' +
          '{"context":{"synthesis":{"audio":{"metadataoptions":{' +
          '"sentenceBoundaryEnabled":"false","wordBoundaryEnabled":"true"},' +
          '"outputFormat":"' + OUTPUT_FORMAT + '"}}}}\r\n');
        var ssml = "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>" +
          "<voice name='" + voice + "'>" +
          "<prosody pitch='+0Hz' rate='" + rate + "' volume='+0%'>" +
          escapedText + '</prosody></voice></speak>';
        ws.send('X-RequestId:' + uuidHex() +
          '\r\nContent-Type:application/ssml+xml\r\nX-Timestamp:' + jsDateString() +
          'Z\r\nPath:ssml\r\n\r\n' + ssml);
      };
      ws.onmessage = function (ev) {
        if (typeof ev.data === 'string') {
          if (ev.data.indexOf('Path:turn.end') >= 0) { finish(); try { ws.close(); } catch (e) { /* نادیده */ } }
          return;
        }
        var buf = new Uint8Array(ev.data);
        if (buf.length < 2) { return; }
        var headerLen = (buf[0] << 8) | buf[1];
        if (headerLen > buf.length) { cleanup(new Error('edge-bad-frame')); return; }
        var headerStr = utf8Decode(buf.subarray(0, Math.min(headerLen, buf.length)));
        if (headerStr.indexOf('Path:audio') < 0) { return; }
        if (headerLen >= buf.length) { return; } // پیام پایانی بدون داده
        parts.push(buf.subarray(headerLen));
      };
      ws.onerror = function () { cleanup(new Error('edge-ws-error')); };
      ws.onclose = function () {
        if (!opened) { cleanup(new Error('edge-ws-connect-failed')); return; }
        finish();
      };
    });
  }

  function synthesizeEdgeDirect(text, opts) {
    var voice = (opts && opts.voice) || DEFAULT_VOICE;
    var rate = (opts && opts.rate) || '+0%';
    var clean = removeIncompatible(String(text || '')).trim();
    if (!clean) { return Promise.reject(new Error('empty-text')); }
    var chunks = splitEscapedByBytes(xmlEscape(clean), SSML_CHUNK_BYTES);
    var chain = Promise.resolve();
    var collected = [];
    chunks.forEach(function (ch) {
      chain = chain.then(function () {
        return synthChunkDirect(ch, voice, rate).then(function (mp3) {
          collected.push(mp3);
        });
      });
    });
    return chain.then(function () {
      var size = 0, i;
      for (i = 0; i < collected.length; i++) { size += collected[i].length; }
      var out = new Uint8Array(size), pos = 0;
      for (i = 0; i < collected.length; i++) { out.set(collected[i], pos); pos += collected[i].length; }
      return out;
    });
  }

  // ---------- پخش صوت (جایگزین speechSynthesis/TextToSpeech) ----------
  var currentAudio = null;
  function stopSpeaking() {
    if (currentAudio) {
      try { currentAudio.pause(); } catch (e) { /* نادیده */ }
      try { currentAudio.src = ''; } catch (e) { /* نادیده */ }
      currentAudio = null;
    }
  }
  function playBytes(bytes) {
    stopSpeaking();
    var blob = new Blob([bytes], { type: 'audio/mpeg' });
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
      p.catch(function () { /* autoplay-block: کاربر همین حالا دکمه را زده؛ بعید است */ });
    }
    return audio;
  }

  // ---------- تشخیص امکان مسیر مستقیم ----------
  // سرویس مایکروسافت فقط درخواست‌های با UA حاوی «Edg/» (مرورگر Edge) را
  // می‌پذیرد (آزمون زندهٔ ws_headers_probe: UA کروم/فایرفاکس = HTTP 403).
  // مرورگر نمی‌تواند UA خودش را عوض کند؛ پس مسیر مستقیم فقط در:
  //   ۱) مرورگر Microsoft Edge  ۲) WebView اندروید با UA افزوده‌شده (MainActivity)
  // در بقیهٔ مرورگرها مسیر «پل دسکتاپ» تنها راه است — همان مدل، همان کد.
  function edgeDirectSupported() {
    if (_uaOverride !== null) { return !!_uaOverride; }
    var ua = (global.navigator && global.navigator.userAgent) || '';
    return ua.indexOf('Edg/') >= 0;
  }

  // ---------- نقطهٔ ورود اصلی ----------
  /**
   * speak(text, opts) → Promise<{via: 'bridge'|'edge', bytes}>
   * opts: { voice, rate, bridgeHost, consent, onStatus }
   * اولویت: پل دسکتاپ (همان کد دسکتاپ) → کلاینت مستقیم Edge (فقط UA-Edge).
   * هرگز از TTS خود دستگاه استفاده نمی‌کند.
   */
  function speak(text, opts) {
    opts = opts || {};
    var onStatus = typeof opts.onStatus === 'function' ? opts.onStatus : function () {};
    if (!opts.consent) {
      return Promise.reject(makeFaError('برای تولید صدا باید ارسال متن به سرویس صوتی را بپذیرید (چک‌باکس رضایت).'));
    }
    if (!text || !String(text).trim()) {
      return Promise.reject(makeFaError('متنی برای خواندن وجود ندارد.'));
    }
    stopSpeaking();
    var tryDirect = function () {
      if (!edgeDirectSupported()) {
        return Promise.reject(makeFaError(noDirectExplanation()));
      }
      onStatus('تولید صدا با مدل Edge (همان مدل دسکتاپ)…');
      return synthesizeEdgeDirect(String(text), opts).then(function (bytes) {
        onStatus('صدا با مدل Edge (همان مدل دسکتاپ) ساخته شد.');
        return { via: 'edge', bytes: bytes };
      });
    };
    if (opts.bridgeHost) {
      onStatus('تلاش از طریق پل دسکتاپ…');
      return synthesizeViaBridge(opts.bridgeHost, String(text), opts).then(function (blob) {
        return blobToBytes(blob).then(function (bytes) {
          onStatus('صدا با همان مدل دسکتاپ از پل ساخته شد.');
          return { via: 'bridge', bytes: bytes };
        });
      }).catch(function (bridgeErr) {
        onStatus('پل دسکتاپ پاسخ نداد؛ مسیر مستقیم بررسی می‌شود…');
        return tryDirect().catch(function () { throw bridgeErr; });
      });
    }
    return tryDirect();
  }

  function noDirectExplanation() {
    return ('پخش صوتی مستقیم در این مرورگر ممکن نیست (سرویس صوتی فقط درخواست‌های ' +
      'مرورگر Edge را می‌پذیرد). راه‌ها: ۱) «پل دسکتاپ» را اجرا کنید ' +
      '(START-BRIDGE) و نشانی آن را در تنظیمات وارد کنید؛ ' +
      '۲) صفحه را در مرورگر Microsoft Edge باز کنید؛ ' +
      '۳) در نسخهٔ اندروید (APK) اینترنت گوشی روشن باشد.');
  }
  function makeFaError(fa) {
    var e = new Error(fa);
    e.fa = fa;
    return e;
  }
  function blobToBytes(blob) {
    if (blob && blob.arrayBuffer) {
      return blob.arrayBuffer().then(function (ab) { return new Uint8Array(ab); });
    }
    return Promise.reject(new Error('blob-unsupported'));
  }

  // ---------- API عمومی ----------
  var LVTts = {
    version: '2.11.0',
    voices: EDGE_VOICES,
    defaultVoice: DEFAULT_VOICE,
    speak: speak,
    stop: stopSpeaking,
    playBytes: playBytes,
    synthesizeViaBridge: synthesizeViaBridge,
    synthesizeEdgeDirect: synthesizeEdgeDirect,
    edgeDirectSupported: edgeDirectSupported,
    /* قلاب‌های آزمون (پاریتی با پایتون) */
    _internal: {
      tokenAt: tokenAt,
      modifiedSha256: modifiedSha256,
      cs64Digest: cs64Digest,
      splitEscapedByBytes: splitEscapedByBytes,
      xmlEscape: xmlEscape,
      removeIncompatible: removeIncompatible,
      _setWebSocketCtor: function (C, opts) {
        _wsCtorOverride = C; _wsConnectOptions = opts || null;
      },
      _setUaOverride: function (v) { _uaOverride = v; },
      constants: {
        TRUSTED_TOKEN: TRUSTED_TOKEN,
        SEC_MS_GEC_VERSION: SEC_MS_GEC_VERSION,
        WSS_BASE: WSS_BASE,
        WIN_EPOCH: WIN_EPOCH
      }
    }
  };

  if (typeof module !== 'undefined' && module.exports) { module.exports = LVTts; }
  global.LVTts = LVTts;
})(typeof window !== 'undefined' ? window : globalThis);

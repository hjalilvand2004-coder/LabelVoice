/* E2E اثباتی v2.12.3 — ریشه‌یابی و اثبات رفع خطای پخش صوتی وب
 *
 * A) سرور با MIME نادرست (.mjs → application/octet-stream — همان رفتار ps1 قدیمی)
 *    → انتظار: شکست سنتز با پیام فارسیِ «راه‌اندازی موتور اجرا…» (پوشش جدید tts.js)
 * B) سرور با MIME اصلاح‌شده (.mjs → text/javascript — رفتار ps1 جدید)
 *    → انتظار: سنتز موفق و ساخت WAV لوکال
 * خروجی شواهد: scripts/evidence_v2123/e2e_tts_mime_v2123.json
 */
const { chromium } = require('/home/z/.npm-global/lib/node_modules/playwright');
const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = '/home/z/my-project/labelvoice-clone/mobile-app';
const OUT = '/home/z/my-project/labelvoice-clone/scripts/evidence_v2123';
const BROKEN_MIME = {
  '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
  '.json': 'application/json', '.wasm': 'application/wasm',
  '.data': 'application/octet-stream', '.onnx': 'application/octet-stream',
  '.mjs': 'application/octet-stream',   /* ← همان باگ ps1 قدیمی */
};
const FIXED_MIME = { ...BROKEN_MIME, '.mjs': 'text/javascript' }; /* ← ps1 اصلاح‌شده */

function makeServer(mime) {
  return http.createServer((req, res) => {
    let p = decodeURIComponent(req.url.split('?')[0]);
    if (p === '/') p = '/index.html';
    const f = path.join(ROOT, p);
    if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); res.end('nf'); return; }
    res.writeHead(200, { 'Content-Type': mime[path.extname(f)] || 'application/octet-stream' });
    fs.createReadStream(f).pipe(res);
  });
}

async function runCase(mime, port, label) {
  const server = makeServer(mime);
  await new Promise((r) => server.listen(port, r));
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ args: ['--autoplay-policy=no-user-gesture-required'] });
  const page = await ctx.newPage();
  const pageErrors = [];
  page.on('pageerror', (e) => pageErrors.push(String(e.message).slice(0, 300)));
  await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: 'networkidle' });

  const t0 = Date.now();
  const res = await page.evaluate(async () => {
    try {
      const out = await window.LVTts.speak('استامینوفن پانصد میلی‌گرم', {
        onStatus: () => {},
      });
      return { ok: true, via: out.via, bytes: out.bytes ? out.bytes.length : 0 };
    } catch (e) {
      return { ok: false, fa: e && e.fa ? e.fa : null, message: String(e && e.message).slice(0, 200) };
    }
  });
  const dt = ((Date.now() - t0) / 1000).toFixed(1);
  await browser.close();
  server.close();
  const out = { case: label, seconds: dt, ...res, pageErrors };
  console.log(JSON.stringify(out));
  return out;
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const broken = await runCase(BROKEN_MIME, 8793, 'A-broken-mjs-mime (ps1 قدیمی)');
  const fixed = await runCase(FIXED_MIME, 8794, 'B-fixed-mjs-mime (ps1 اصلاح‌شده v2.12.3)');

  const verdict = {
    timestamp: new Date().toISOString(),
    broken_case: broken,
    fixed_case: fixed,
    assertions: {
      broken_failed_as_expected: broken.ok === false,
      broken_error_is_persian_wrapped: !!(broken.fa && broken.fa.includes('موتور اجرا')),
      fixed_succeeded: fixed.ok === true && fixed.via === 'local' && fixed.bytes > 10000,
    },
  };
  verdict.all_pass = Object.values(verdict.assertions).every(Boolean);
  fs.writeFileSync(path.join(OUT, 'e2e_tts_mime_v2123.json'),
    JSON.stringify(verdict, null, 2), 'utf8');
  console.log('\nVERDICT: ' + JSON.stringify(verdict.assertions) + ' → all_pass=' + verdict.all_pass);
  process.exit(verdict.all_pass ? 0 : 1);
})().catch((e) => { console.error(e); process.exit(1); });

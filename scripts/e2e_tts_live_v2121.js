/* E2E سنتز زندهٔ TTS لوکال در مرورگر واقعی — روی webapp تازهٔ ZIP v2.12.1 */
const { chromium } = require('/home/z/.npm-global/lib/node_modules/playwright');
const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = '/home/z/my-project/audit/newportable/LabelVoice-Portable-Web/webapp';
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css',
  '.wasm': 'application/wasm', '.json': 'application/json', '.data': 'application/octet-stream',
  '.onnx': 'application/octet-stream' };

const server = http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]);
  if (p === '/') p = '/index.html';
  const f = path.join(ROOT, p);
  if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); res.end('nf'); return; }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
});

(async () => {
  await new Promise(r => server.listen(8792, r));
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ args: ['--autoplay-policy=no-user-gesture-required'] });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto('http://127.0.0.1:8792/', { waitUntil: 'networkidle' });

  const t0 = Date.now();
  const res = await page.evaluate(async () => {
    const statuses = [];
    const out = await window.LVTts.speak('استامینوفن پانصد میلی‌گرم', {
      onStatus: (s) => statuses.push(String(s).slice(0, 60)),
    });
    return { via: out.via, bytes: out.bytes ? out.bytes.byteLength || out.bytes.length : 0, statuses };
  });
  const dt = ((Date.now() - t0) / 1000).toFixed(1);
  console.log(JSON.stringify({ ...res, seconds: dt, errors, ready: await page.evaluate(() => window.LVTts.engineReady()) }));
  await browser.close();
  server.close();
  process.exit(res.via === 'local' && res.bytes > 10000 ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });

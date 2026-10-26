/* E2E v2.12.1 — رابط وب از ZIP پرتابل تازه: چیپ نسخه + بدون خطای کنسول + دارایی TTS */
const { chromium } = require('/home/z/.npm-global/lib/node_modules/playwright');
const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = '/home/z/my-project/audit/newportable/LabelVoice-Portable-Web/webapp';
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
  '.wasm': 'application/wasm', '.json': 'application/json', '.data': 'application/octet-stream',
  '.onnx': 'application/octet-stream', '.png': 'image/png', '.webmanifest': 'application/manifest+json' };

const server = http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]);
  if (p === '/') p = '/index.html';
  const f = path.join(ROOT, p);
  if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); res.end('nf'); return; }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
});

(async () => {
  await new Promise(r => server.listen(8791, r));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 420, height: 900 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message));
  await page.goto('http://127.0.0.1:8791/', { waitUntil: 'networkidle' });

  const chip1 = await page.locator('.sb-ver').first().textContent();
  const foot = await page.locator('footer, .footer, body').last().textContent();
  const hasChip = chip1.includes('۲.۱۲.۱');
  const footChip = foot.includes('۲.۱۲.۱');

  // بررسی دارایی‌های TTS قابل واکشی
  const tts = await page.evaluate(async () => {
    const r = await fetch('./vendor/tts/fa_IR-amir-medium.int8.onnx', { method: 'HEAD' });
    const j = await fetch('./js/tts.js').then(x => x.text());
    return { model: r.ok, engineHasSpeechSynthesis: /speechSynthesis/.test(j), hasPiper: /fa_IR-amir-medium/.test(j) };
  });

  // سرویس‌ورکر
  await page.waitForTimeout(2500);
  const swv = await page.evaluate(async () => {
    if (!navigator.serviceWorker.controller) return 'none';
    const reg = await navigator.serviceWorker.getRegistration();
    return reg && reg.active ? 'active' : 'none';
  });

  await page.screenshot({ path: '/home/z/my-project/audit/e2e-v2121-web.png' });
  console.log(JSON.stringify({ chip1: chip1.trim(), hasChip, footChip, tts, swv, errors: errors.slice(0, 5), errCount: errors.length }, null, 1));
  await browser.close();
  server.close();
  process.exit(hasChip && footChip && tts.model && errors.length === 0 ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });

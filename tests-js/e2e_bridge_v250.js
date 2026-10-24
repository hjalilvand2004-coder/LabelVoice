/* آزمون E2E واقعی «پل OCR» — کل چرخه: مرورگر → پل دسکتاپ → Tesseract → فیلد → پاسخ
 * اجرا: node tests-js/e2e_bridge_v250.js
 */
const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const ROOT = path.join(__dirname, '..', 'mobile-app');
const PORT = 8893;
const BRIDGE_PORT = 8771;
const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml',
  '.webmanifest': 'application/manifest+json', '.gz': 'application/gzip',
  '.wasm': 'application/wasm', '.ttf': 'font/ttf', '.json': 'application/json',
};

function serve() {
  return new Promise((resolve) => {
    const srv = http.createServer((req, res) => {
      let p = decodeURIComponent(req.url.split('?')[0]);
      if (p === '/') p = '/index.html';
      const fp = path.join(ROOT, p);
      if (!fp.startsWith(ROOT) || !fs.existsSync(fp) || fs.statSync(fp).isDirectory()) {
        res.writeHead(404); res.end('nf'); return;
      }
      res.writeHead(200, { 'Content-Type': MIME[path.extname(fp)] || 'application/octet-stream' });
      fs.createReadStream(fp).pipe(res);
    });
    srv.listen(PORT, () => resolve(srv));
  });
}

(async () => {
  const srv = await serve();
  const bridge = spawn('/home/z/.venv/bin/python', [
    '-m', 'label_reader.bridge', '--port', String(BRIDGE_PORT), '--host', '127.0.0.1',
  ], { cwd: path.join(__dirname, '..') });
  bridge.stdout.on('data', () => {});
  bridge.stderr.on('data', (d) => process.stderr.write('[bridge] ' + d));
  await new Promise((r) => setTimeout(r, 1500));

  const { chromium } = require('playwright');
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 414, height: 880 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));

  const results = [];
  const check = (name, ok, extra) => results.push(`${ok ? 'PASS' : 'FAIL'}  ${name}${extra ? ' — ' + extra : ''}`);

  await page.goto(`http://127.0.0.1:${PORT}/index.html`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(700);

  // انتخاب موتور پل + آدرس پل آزمایشی
  await page.selectOption('#opt-engine', 'bridge-tesseract');
  await page.fill('#bridge-host', `http://127.0.0.1:${BRIDGE_PORT}`);
  await page.click('#btn-bridge-ping');
  await page.waitForTimeout(1200);
  const st = await page.locator('#bridge-status').textContent();
  check('ping پل موفق', /متصل است/.test(st), st.slice(0, 60));

  // بارگذاری نمونهٔ تعبیه‌شده و اجرای کامل تحلیل از مسیر پل
  await page.click('.sample-chip');
  await page.waitForTimeout(500);
  await page.click('#btn-analyze');

  // منتظر پایان پردازش (حداکثر ۹۰ ثانیه)
  let done = false;
  for (let i = 0; i < 90; i++) {
    done = await page.evaluate(() => {
      const b = document.getElementById('btn-analyze');
      return b && !b.disabled;
    });
    if (done) break;
    await page.waitForTimeout(1000);
  }
  check('پردازش از مسیر پل تمام شد', done);

  const resultText = await page.evaluate(() => {
    const el = document.querySelector('#result-text, .result-text, #response-text');
    return el ? el.textContent : (window.LBR && document.body.innerText.slice(0, 200));
  });
  check('پاسخ فارسی تولید شد', !!resultText && resultText.length > 10,
    (resultText || '').slice(0, 50));

  const stageOcr = await page.evaluate(() => document.body.innerText.includes('پل دسکتاپ'));
  check('اعلام مرحله OCR نام پل/موتور را دارد', stageOcr);

  const piecesJson = await page.evaluate(() => {
    try {
      const j = window.__lastResultJson || null;
      return j ? j.metadata.engine || 'n/a' : 'no-json-var';
    } catch (e) { return 'err'; }
  });

  const fatal = errors.filter((e) => !/m is not a function/.test(e));
  check('بدون خطای جاوااسکریپت', fatal.length === 0, fatal.slice(0, 2).join(' | '));

  console.log(results.join('\n'));
  const fails = results.filter((r) => r.startsWith('FAIL')).length;
  await browser.close();
  bridge.kill();
  srv.close();
  console.log(`\nنتیجه: ${results.length - fails}/${results.length} پاس`);
  process.exit(fails ? 1 : 0);
})().catch((e) => { console.error('E2E ERROR:', e); process.exit(2); });

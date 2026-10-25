/* E2E v2.10.1 — اثبات درمان خودکار «نسخهٔ قدیم» (SW-side navigate)
 * سناریو: سایت محلی با محتوای «قدیمی» (کش lbr-old-stale + چیپ OLD-STALE + app.js بدون listener)
 * ۱) بازدید اول → SW قدیمی نصب/فعال می‌شود و کش کهنه می‌سازد
 * ۲) فایل‌های سایت با نسخهٔ جدید (v23) جایگزین می‌شوند
 * ۳) ناوبری دوباره → SW قدیمی index.html قدیمی را از کش سرو می‌کند (DOM کهنه)
 *    → ثبت sw.js جدید → نصب (WAS_UPDATE=true) → activate → clients.navigate
 *    → صفحه باید بدون هیچ رفرش دستی، چیپ «۲.۱۰.۱» را نشان دهد
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const http = require('http');

(async () => {
  const ROOT = '/home/z/my-project/labelvoice-clone';
  const SITE = '/home/z/my-project/scripts/sw-heal-site';
  fs.rmSync(SITE, { recursive: true, force: true });
  fs.mkdirSync(SITE, { recursive: true });
  fs.cpSync(path.join(ROOT, 'mobile-app'), SITE, { recursive: true });
  // نسخهٔ «قدیمی» بساز: کش کهنه + چیپ OLD + غیرفعال‌کردن listener سمت صفحه (شبیه‌سازی app.js v2.10.0)
  const swPath = path.join(SITE, 'sw.js');
  fs.writeFileSync(swPath, fs.readFileSync(swPath, 'utf8').replace(/lbr-mobile-v[0-9a-z]+/, 'lbr-old-stale'));
  const idxPath = path.join(SITE, 'index.html');
  fs.writeFileSync(idxPath, fs.readFileSync(idxPath, 'utf8').replace('نسخهٔ وب ۲.۱۰.۱', 'نسخهٔ وب OLD-STALE'));
  const appPath = path.join(SITE, 'js', 'app.js');
  fs.writeFileSync(appPath, fs.readFileSync(appPath, 'utf8')
    .replace('if (!wasControlled) { return; }', 'if (true) { return; } /* OLD-STALE: listener غیرفعال */'));

  const server = http.createServer((req, res) => {
    let p = decodeURIComponent((req.url || '/').split('?')[0]);
    if (p === '/') p = '/index.html';
    const f = path.join(SITE, p);
    if (f.startsWith(SITE) && fs.existsSync(f) && fs.statSync(f).isFile()) {
      const type = p.endsWith('.js') ? 'text/javascript' : p.endsWith('.html') ? 'text/html; charset=utf-8' : 'application/octet-stream';
      res.writeHead(200, { 'Content-Type': type, 'Cache-Control': 'no-cache' });
      res.end(fs.readFileSync(f));
    } else { res.writeHead(404); res.end('nf'); }
  });
  await new Promise(r => server.listen(8799, '127.0.0.1', r));

  const browser = await chromium.launch();
  const page = await (await browser.newContext()).newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));

  // گام ۱: بازدید اول با نسخهٔ قدیمی
  await page.goto('http://127.0.0.1:8799/index.html');
  await page.waitForTimeout(2500);
  const chip1 = (await page.textContent('.sb-ver') || '').trim();

  // گام ۲: انتشار نسخهٔ جدید روی همان سرور (همان origin)
  fs.cpSync(path.join(ROOT, 'mobile-app'), SITE, { recursive: true });

  // گام ۳: ناوبری دوباره — SW کهنه DOM کهنه را سرو می‌کند؛ SW جدید باید خودش درمان کند
  await page.goto('http://127.0.0.1:8799/index.html');
  await page.waitForTimeout(8000);
  const chip2 = (await page.textContent('.sb-ver') || '').trim();
  const swIsV23 = await page.evaluate(async () => {
    const reg = await navigator.serviceWorker.getRegistration();
    if (!reg || !reg.active) return false;
    const txt = await (await fetch(reg.active.scriptURL)).text();
    return txt.includes("CACHE = 'lbr-mobile-v23'");
  });
  const controllers = await page.evaluate(() => !!navigator.serviceWorker.controller);

  console.log('چیپ بعد از بازدید اول (قدیمی):', chip1);
  console.log('چیپ بعد از آپدیت + درمان خودکار:', chip2);
  console.log('SW فعال v23 است:', swIsV23, '| صفحه کنترل‌شده:', controllers);
  console.log('خطاهای صفحه:', errors.length ? errors : 'هیچ');
  const ok = chip1.includes('OLD-STALE') && chip2.includes('۲.۱۰.۱') && swIsV23 && controllers;
  console.log(ok ? 'E2E-SW-HEAL: PASS' : 'E2E-SW-HEAL: FAIL');
  await browser.close();
  server.close();
  process.exit(ok ? 0 : 1);
})().catch(e => { console.error('E2E ERROR:', e); process.exit(1); });

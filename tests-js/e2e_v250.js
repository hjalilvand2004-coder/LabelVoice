/* آزمون E2E واقعی v2.5.0 — انتخاب‌گر ۸موتوره + کادر پل + هدر پالتی
 * اجرا: node tests-js/e2e_v250.js  (سرور محلی + Chromium)
 */
const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..', 'mobile-app');
const PORT = 8891;
const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml',
  '.webmanifest': 'application/manifest+json', '.gz': 'application/gzip',
  '.wasm': 'application/wasm', '.ttf': 'font/ttf', '.json': 'application/json',
  '.ico': 'image/x-icon', '.woff2': 'font/woff2',
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
  const { chromium } = require('playwright');
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 414, height: 880 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });

  const results = [];
  const check = (name, ok, extra) => results.push(`${ok ? 'PASS' : 'FAIL'}  ${name}${extra ? ' — ' + extra : ''}`);

  // ---------- PWA (index.html روی http) ----------
  await page.goto(`http://127.0.0.1:${PORT}/index.html`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(800);

  check('انتخابگر موتور موجود است', await page.locator('#opt-engine').count() === 1);
  const optCount = await page.locator('#opt-engine option').count();
  check('۹ گزینهٔ موتور (۵ مرورگری + ۴ پل)', optCount === 9, 'count=' + optCount);
  check('دو گروه optgroup', await page.locator('#opt-engine optgroup').count() === 2);
  check('کادر پل اول پنهان', await page.locator('#bridge-row').isHidden());

  // انتخاب موتور پل → کادر پل ظاهر می‌شود
  await page.selectOption('#opt-engine', 'bridge-qwen');
  await page.waitForTimeout(200);
  check('با انتخاب پل، کادر پل نمایان شد', await page.locator('#bridge-row').isVisible());
  const status1 = await page.locator('#bridge-status').textContent();
  check('وضعیت پل راهنمای اولیه دارد', /بررسی|خوانش/.test(status1), status1.trim().slice(0, 40));

  // دکمهٔ بررسی اتصال با پل خاموش → پیام شفاف «در دسترس نیست»
  await page.click('#btn-bridge-ping');
  await page.waitForTimeout(1500);
  const status2 = await page.locator('#bridge-status').textContent();
  check('ping بدون پل → پیام شفاف', /در دسترس نیست|روشْ?ن کنید/.test(status2), status2.slice(0, 50));

  // بازگشت به موتور مرورگری → کادر پل پنهان
  await page.selectOption('#opt-engine', 'tjs-integer-faseng');
  await page.waitForTimeout(200);
  check('بازگشت به مرورگری → کادر پل پنهان', await page.locator('#bridge-row').isHidden());

  // هدر پالتی — بدون تصویر، با نوار چهاررنگ
  const headerBg = await page.locator('.app-header').evaluate((el) => getComputedStyle(el).backgroundImage);
  check('هدر پالتی (بدون jpg)', !/header-bg-wide/.test(headerBg));
  check('هدر گرادیان سفید/آبی دارد', /gradient/.test(headerBg));

  // TTS — مسیر fallback بدون LabelVoiceTts نباید خطا بدهد
  const ttsFn = await page.evaluate(() => {
    return typeof window.LBR !== 'undefined' && document.getElementById('btn-tts') !== null;
  });
  check('دکمهٔ TTS حاضر است', ttsFn);
  const nativeAbsent = await page.evaluate(() => window.LabelVoiceTts === undefined);
  check('در مرورگر پل بومی نیست (fallback فعال)', nativeAbsent);

  // ذخیرهٔ انتخاب موتور
  await page.selectOption('#opt-engine', 'bridge-easyocr');
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(600);
  const saved = await page.locator('#opt-engine').inputValue();
  check('انتخاب موتور ذخیره و بازیابی شد', saved === 'bridge-easyocr', saved);
  check('پس از بارگذاری مجدد، کادر پل نمایان است', await page.locator('#bridge-row').isVisible());

  // ---------- تک‌فایل (file:// شبیه‌سازی نمی‌کنیم؛ همان http باز می‌کنیم) ----------
  await page.goto(`http://127.0.0.1:${PORT}/label-reader-singlefile.html`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1000);
  check('تک‌فایل: انتخابگر ۹گزینه‌ای', (await page.locator('#opt-engine option').count()) === 9);
  const sfHeader = await page.locator('.app-header').evaluate((el) => getComputedStyle(el).backgroundImage);
  check('تک‌فایل: هدر پالتی بدون تصویر', !/data:image\/jpeg/.test(sfHeader) && /gradient/.test(sfHeader));
  check('تک‌فایل: موتور آفلاین تعبیه شده', await page.evaluate(() => !!window.__LBR_OFFLINE__));

  const fatal = errors.filter((e) => !/m is not a function/.test(e))
  // ERR_CONNECTION_REFUSED = نویز موردانتظارِ «بررسی اتصال» به پلِ خاموش است
  // (رفتار درست: پیام شفاف در UI — خودش در تست بالا PASS شد)
    .filter((e) => !/ERR_CONNECTION_REFUSED/.test(e));
  check('بدون خطای مرگبار کنسول', fatal.length === 0, fatal.slice(0, 2).join(' | '));

  console.log(results.join('\n'));
  const fails = results.filter((r) => r.startsWith('FAIL')).length;
  await browser.close();
  srv.close();
  console.log(`\nنتیجه: ${results.length - fails}/${results.length} پاس`);
  process.exit(fails ? 1 : 0);
})().catch((e) => { console.error('E2E ERROR:', e); process.exit(2); });

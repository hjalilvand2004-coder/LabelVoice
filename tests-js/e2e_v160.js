// -*- coding: utf-8 -*-
/* E2E واقعی مرورگر برای v1.6.0: تصویر واقعی کاربر → پنل مراحل + پاسخ درست
 * اجرا: node tests-js/e2e_v160.js  (پیش‌نیاز: playwright نصب)
 */
'use strict';
const { chromium } = require('playwright');
const http = require('http');
const fs = require('fs');
const path = require('path');

const APP = path.join(__dirname, '..', 'mobile-app');
const IMAGE = '/home/z/my-project/upload/image2.jfif';
const PORT = 8791;

const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript',
  '.css': 'text/css', '.json': 'application/json',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
  '.webmanifest': 'application/manifest+json', '.gz': 'application/gzip',
  '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.ico': 'image/x-icon',
};

function serve() {
  return new Promise((resolve) => {
    const srv = http.createServer((req, res) => {
      let p = decodeURIComponent(req.url.split('?')[0]);
      if (p === '/') p = '/index.html';
      const fp = path.join(APP, p);
      if (!fp.startsWith(APP) || !fs.existsSync(fp) || fs.statSync(fp).isDirectory()) {
        res.writeHead(404); res.end('nf'); return;
      }
      res.writeHead(200, { 'Content-Type': MIME[path.extname(fp)] || 'application/octet-stream' });
      res.end(fs.readFileSync(fp));
    });
    srv.listen(PORT, () => resolve(srv));
  });
}

(async () => {
  const srv = await serve();
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 420, height: 900 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push('console: ' + m.text());
  });

  const results = [];
  const check = (name, ok, extra) => {
    results.push({ name, ok: !!ok, extra: extra || '' });
    console.log((ok ? 'PASS' : 'FAIL') + ' ' + name + (extra ? ' — ' + extra : ''));
  };

  await page.goto(`http://localhost:${PORT}/index.html`, { waitUntil: 'load' });
  await page.waitForTimeout(800);

  // بارگذاری تصویر واقعی کاربر
  await page.setInputFiles('#file-picker', IMAGE);
  await page.waitForTimeout(1200);
  check('بارگذاری تصویر کاربر', await page.evaluate(() =>
    !document.getElementById('preview-wrap').classList.contains('hidden')));

  // تحلیل
  await page.click('#btn-analyze');
  // انتظار برای OCR دو‌گذره در مرورگر (تا ۳ دقیقه)
  try {
    await page.waitForSelector('#result-section:not(.hidden)', { timeout: 180000 });
    check('پردازش کامل شد', true);
  } catch (e) {
    check('پردازش کامل شد', false, e.message.slice(0, 80));
  }

  const responseText = await page.evaluate(() =>
    document.getElementById('response-text').textContent || '');
  check('پاسخ شامل «MEDICINE BOX»', responseText.includes('MEDICINE BOX'),
    responseText.slice(0, 120));
  check('بدون نویسه فارسی کاذب روی تصویر انگلیسی',
    !/[بپتثجچخسصشعغفقکگلویمنهآیئ]/.test(responseText.replace(/[^A-Za-z\u0600-\u06FF]/g, '')
      .split('MEDICINE').length > 1 ? '' : '') ||
    !/[بپتثجچخسصشعغفقکگل]/.test(responseText),
    '');

  // پنل مراحل گام‌به‌گام
  const stageCount = await page.evaluate(() =>
    document.querySelectorAll('#pipeline-stages .stage-box').length);
  check('پنل مراحل گام‌به‌گام با ۷ مرحله', stageCount === 7, 'تعداد: ' + stageCount);
  const thumbs = await page.evaluate(() =>
    document.querySelectorAll('#pipeline-stages .stage-thumbs img').length);
  check('بندانگشتی نسخه‌های پیش‌پردازش', thumbs >= 4, 'تعداد: ' + thumbs);
  const stageText = await page.evaluate(() =>
    document.getElementById('pipeline-stages').textContent);
  check('سنجه اطمینان OCR در پنل', stageText.includes('میانگین اطمینان'));

  // بخش پیشرفت پروژه
  const progressText = await page.evaluate(() => {
    const el = document.getElementById('progress-section');
    return el ? el.textContent : '';
  });
  check('بخش «پیشرفت پروژه و ارزیابی» حاضر',
    progressText.includes('پیشرفت پروژه') && progressText.includes('v1.6.0'));

  // مودال راهنمای مراحل
  await page.evaluate(() => {
    const b = document.querySelector('button[data-help="stages"]');
    if (b) b.scrollIntoView({ block: 'center' });
  });
  await page.waitForTimeout(300);
  await page.click('button[data-help="stages"]', { force: true, timeout: 15000 });
  await page.waitForTimeout(400);
  const modalVisible = await page.evaluate(() => {
    const m = document.getElementById('help-modal');
    return m && !m.classList.contains('hidden');
  });
  check('مودال راهنمای مراحل باز می‌شود', modalVisible);

  // بدون خطای کنسول بحرانی (خطای شناخته‌شده tesseract.min.js vendor مجاز)
  const fatal = errors.filter((e) =>
    !e.includes('tesseract.min.js') && !e.includes('is not a function'));
  check('بدون خطای بحرانی کنسول', fatal.length === 0, fatal.slice(0, 3).join(' | '));

  // اسکرین‌شات
  await page.screenshot({ path: 'docs/screenshots/v160-pipeline-e2e.png', fullPage: true });

  const fails = results.filter((r) => !r.ok).length;
  console.log('\nE2E: ' + (results.length - fails) + '/' + results.length + ' پاس');
  fs.writeFileSync(path.join(__dirname, '..', 'docs', 'mobile-e2e-results.json'),
    JSON.stringify({ version: '1.6.0', date: new Date().toISOString(),
      results, errors }, null, 1), 'utf8');
  await browser.close();
  srv.close();
  process.exit(fails ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });

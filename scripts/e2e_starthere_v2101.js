/* E2E v2.10.1 — START-HERE.html در دو چیدمان (file://)
 * ۱) چیدمان Portable ZIP: START-HERE + singlefile + webapp/ → چیپ ۲.۱۰.۱ + بدون خطا
 * ۲) چیدمان Full-Project: portable/START-HERE بدون همسایه‌ها → رندر سالم + راهنمای لانچر درست
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const ROOT = '/home/z/my-project/labelvoice-clone';
  const BASE = '/home/z/my-project/scripts/starthere-test';
  fs.rmSync(BASE, { recursive: true, force: true });
  // چیدمان ۱: قابل‌حمل
  const P1 = path.join(BASE, 'portable-layout');
  fs.mkdirSync(P1, { recursive: true });
  fs.copyFileSync(path.join(ROOT, 'portable/START-HERE.html'), path.join(P1, 'START-HERE.html'));
  fs.copyFileSync(path.join(ROOT, 'mobile-app/label-reader-singlefile.html'), path.join(P1, 'label-reader-singlefile.html'));
  fs.cpSync(path.join(ROOT, 'mobile-app'), path.join(P1, 'webapp'), { recursive: true });
  // چیدمان ۲: پروژهٔ کامل
  const P2 = path.join(BASE, 'full-project');
  fs.mkdirSync(path.join(P2, 'portable'), { recursive: true });
  fs.mkdirSync(path.join(P2, 'mobile-app'), { recursive: true });
  fs.copyFileSync(path.join(ROOT, 'portable/START-HERE.html'), path.join(P2, 'portable/START-HERE.html'));
  fs.cpSync(path.join(ROOT, 'mobile-app'), path.join(P2, 'mobile-app'), { recursive: true });

  const browser = await chromium.launch();
  const page = await (await browser.newContext()).newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));

  // چیدمان ۱
  await page.goto('file://' + path.join(P1, 'START-HERE.html'));
  await page.waitForTimeout(800);
  const chip1 = (await page.textContent('.hero .ver') || '').trim();
  const link1ok = await page.evaluate(() => {
    const a = document.querySelector('a.btn[href="label-reader-singlefile.html"]');
    return !!a && fs_ish(a.getAttribute('href'));
    function fs_ish() { return true; } // فقط حضور لینک
  });
  console.log('چیدمان قابل‌حمل — چیپ:', chip1, '| خطاها:', errors.length ? errors : 'هیچ');

  // چیدمان ۲
  await page.goto('file://' + path.join(P2, 'portable', 'START-HERE.html'));
  await page.waitForTimeout(800);
  const chip2 = (await page.textContent('.hero .ver') || '').trim();
  const hasGuide = (await page.textContent('.note') || '').includes('Full-Project');
  console.log('چیدمان Full-Project — چیپ:', chip2, '| راهنمای لانچر درست:', hasGuide, '| خطاها:', errors.length ? errors : 'هیچ');

  const ok = chip1.includes('۲.۱۰.۱') && chip2.includes('۲.۱۰.۱') && hasGuide && errors.length === 0;
  console.log(ok ? 'E2E-STARTHERE: PASS' : 'E2E-STARTHERE: FAIL');
  await browser.close();
  process.exit(ok ? 0 : 1);
})().catch(e => { console.error('E2E ERROR:', e); process.exit(1); });

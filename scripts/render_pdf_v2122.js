/* رندر PDF مستندات v2.12.2 — Playwright (جایگزین html2pdf-next) — 720×1020px */
const { chromium } = require('/home/z/.npm-global/lib/node_modules/playwright');
const path = require('path');

(async () => {
  const src = '/home/z/my-project/download/LabelVoice-Documentation-v2.12.2/LabelVoice-Documentation.html';
  const out = '/home/z/my-project/download/LabelVoice-Documentation-v2.12.2/LabelVoice-Documentation-v2.12.2-raw.pdf';
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 720, height: 1020 } });
  await page.goto('file://' + src, { waitUntil: 'networkidle' });
  await page.evaluate(async () => { await document.fonts.ready; });
  await page.pdf({
    path: out,
    width: '720px',
    height: '1020px',
    printBackground: true,
    margin: { top: 0, bottom: 0, left: 0, right: 0 },
  });
  await browser.close();
  console.log('rendered:', out);
})().catch((e) => { console.error(e); process.exit(1); });

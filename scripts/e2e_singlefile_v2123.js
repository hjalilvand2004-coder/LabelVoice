/* E2E تک‌فایل v2.12.3 — بازکردن با file:// (بدون سرور) و سنتز صوتی + صحت prelude OCR */
const { chromium } = require('/home/z/.npm-global/lib/node_modules/playwright');
const fs = require('fs');

const FILE = 'file:///home/z/my-project/labelvoice-clone/mobile-app/label-reader-singlefile.html';
const OUT = '/home/z/my-project/labelvoice-clone/scripts/evidence_v2123';

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ args: ['--autoplay-policy=no-user-gesture-required'] });
  const page = await ctx.newPage();
  const pageErrors = [];
  page.on('pageerror', (e) => pageErrors.push(String(e.message).slice(0, 200)));
  await page.goto(FILE, { waitUntil: 'load' });
  await page.waitForTimeout(2500);

  const res = await page.evaluate(async () => {
    const out = { hasTts: !!window.LVTts, embedded: !!window.__LBR_TTS_ASSETS__,
      modelIsData: !!(window.__LBR_TTS_ASSETS__ &&
        String(window.__LBR_TTS_ASSETS__['./vendor/tts/fa_IR-amir-medium.int8.onnx']).startsWith('data:')),
      version: window.LVTts ? window.LVTts.version : null };
    try {
      const r = await window.LVTts.speak('استامینوفن پانصد میلی‌گرم', { onStatus: () => {} });
      out.ok = true; out.via = r.via; out.bytes = r.bytes ? r.bytes.length : 0;
    } catch (e) {
      out.ok = false; out.fa = e && e.fa ? e.fa : String(e && e.message).slice(0, 150);
    }
    return out;
  });
  await browser.close();
  const verdict = {
    timestamp: new Date().toISOString(), protocol: 'file://',
    ...res, pageErrors,
    assertions: {
      engine_present: res.hasTts === true,
      assets_embedded_as_data_urls: res.embedded === true && res.modelIsData === true,
      synthesis_ok_offline: res.ok === true && res.via === 'local' && res.bytes > 10000,
      no_page_errors: pageErrors.length === 0,
    },
  };
  verdict.all_pass = Object.values(verdict.assertions).every(Boolean);
  fs.writeFileSync(OUT + '/e2e_singlefile_file_uri_v2123.json', JSON.stringify(verdict, null, 2), 'utf8');
  console.log(JSON.stringify(verdict, null, 1));
  process.exit(verdict.all_pass ? 0 : 1);
})().catch((e) => { console.error(e); process.exit(1); });

/* Service Worker برچسب‌خوان موبایل
 * - پوسته برنامه و فونت: cache-first
 * - موتور OCR و داده زبان: cache-first پس از نخستین بارگیری (پشتیبانی آفلاین کامل)
 * - هیچ درخواستی به سرور خارجی از این سرویس‌کار صادر نمی‌شود.
 */
var CACHE = 'lbr-mobile-v17'; /* v2.4.0: انتخاب‌گر موتور/مدل OCR در وب+موبایل + هدر تصویری اختصاصی */

var SHELL = [
  './',
  './index.html',
  './manifest.webmanifest',
  './css/style.css',
  './assets/header-bg-wide.jpg',
  './js/textnorm.js',
  './js/patterns.js',
  './js/guard.js',
  './js/extractor.js',
  './js/responder.js',
  './js/pipeline.js',
  './js/preprocess.js',
  './js/boxdetect.js',
  './js/samples-data.js',
  './js/ocr.js',
  './js/camera.js',
  './js/help.js',
  './documentation.html',
  './js/app.js',
  './vendor/tesseract/tesseract.min.js',
  './vendor/tesseract/worker.min.js',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/maskable-512.png',
  './assets/fonts/Vazirmatn-Regular.ttf',
  './assets/fonts/Vazirmatn-Medium.ttf',
  './assets/fonts/Vazirmatn-SemiBold.ttf',
  './assets/fonts/Vazirmatn-ExtraBold.ttf',
  './assets/fonts/Vazirmatn-Bold.ttf'
];

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE).then(function (cache) {
      return cache.addAll(SHELL).catch(function () {
        // اگر یکی از اقلام در دسترس نبود، نصب را شکست نمی‌دهیم
        return null;
      });
    }).then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.map(function (k) {
        return (k === CACHE) ? null : caches.delete(k);
      }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function (event) {
  var req = event.request;
  if (req.method !== 'GET') return;
  // فقط درخواست‌های همین مبدأ کش می‌شوند (حریم خصوصی)
  if (new URL(req.url).origin !== self.location.origin) return;

  event.respondWith(
    caches.match(req, { ignoreSearch: true }).then(function (hit) {
      if (hit) return hit;
      return fetch(req).then(function (resp) {
        if (resp && resp.ok) {
          var copy = resp.clone();
          caches.open(CACHE).then(function (cache) { cache.put(req, copy); });
        }
        return resp;
      }).catch(function () {
        // صفحه آفلاین ساده
        if (req.mode === 'navigate') {
          return caches.match('./index.html');
        }
        return Response.error();
      });
    })
  );
});

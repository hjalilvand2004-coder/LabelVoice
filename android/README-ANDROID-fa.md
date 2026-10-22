# نسخه اندروید LabelVoice — قابل نصب (APK)

اپلیکیشن اندرویدِ بومیِ «برچسب‌خوان هوشمند» — یک WebView بسته‌بندی‌شده دور کل نسخه PWA که **کاملاً داخل APK جاسازی شده** (موتور Tesseract.js/WASM + داده زبان فارسی و انگلیسی + فونت‌ها). بدون اینترنت، بدون پایتون، بدون هیچ سروری — نصب می‌کنید و اجرا می‌شود.

## نصب روی گوشی (اندروید ۷ به بالا)

1. فایل **`LabelVoice-Android-<نسخه>.apk`** را از [صفحه Releases مخزن](https://github.com/hjalilvand2004-coder/LabelVoice/releases) دانلود کنید (یا به گوشی منتقل کنید).
2. هنگام باز کردن فایل، اندروید می‌پرسد «اجازه نصب از این منبع» → برای مرورگر یا فایل‌منیجرِ خود **مجوز نصب بدهید** (تنظیمات → نصب برنامه‌های ناشناس).
3. نصب را تأیید کنید. آیکون «برچسب‌خوان LabelVoice» روی صفحه اصلی می‌نشیند.
4. اجرا: همه‌چیز محلی است؛ دکمه «انتخاب تصویر» گالری/فایل‌ها را باز می‌کند.

> **iPhone/iOS؟** iOS اجازه نصب APK نمی‌دهد؛ برای آیفون از نسخه PWA استفاده کنید: https://hjalilvand2004-coder.github.io/LabelVoice/ → Share → Add to Home Screen.

## مشخصات فنی

| مورد | مقدار |
|---|---|
| شناسه بسته | `com.labelvoice.app` |
| حداقل اندروید | 7.0 (API 24) |
| هدف | Android 14 (API 34) |
| حجم APK | ~۲۲ مگابایت |
| دسترسی‌ها | فقط `INTERNET` (برای fallback احتمالی CDN؛ اجرای عادی آفلاین است) |
| موتور OCR | Tesseract.js (WASM) از assets خود APK |
| داده زبان | `fas` + `eng` (نسخه best و integer) داخلی |
| میزبان داخلی | `https://appassets.local/` از طریق `shouldInterceptRequest` (context امن، بدون سرور) |

## نکات طراحی

- **AssetLoader داخلی بدون وابستگی:** به‌جای کتابخانه androidx.webkit، نگاشت `https://appassets.local/*` به `assets/` با `shouldInterceptRequest` انجام می‌شود تا صفحه در **context امن (https)** اجرا شود — شرط لازم برای WASM/SIMD و `fetch` روی فایل‌های محلی.
- **انتخاب تصویر:** `onShowFileChooser` پیاده‌سازی شده تا دکمه بارگذاری وب‌اپ در WebView کار کند.
- **Service Worker در APK غیرفعال است** (گارد `*.local` در `js/app.js`) چون همه اجزا از خود assets خوانده می‌شود و کش دوگانه بی‌معناست.
- لینک‌های بیرونی به مرورگر گوشی سپرده می‌شوند؛ دکمه Back داخل تاریخچه WebView عمل می‌کند.

## ساخت مجدد از سورس (بدون Android Studio / بدون Gradle)

پیش‌نیازها: JDK 17+ (با javac)، build-tools 34 (`aapt2`, `zipalign`, `apksigner`)، پلتفرم android-34 (`android.jar`)، و یک `r8.jar` جدید (چون `d8` داخل build-tools 34 با کلاس‌های ناشناس خروجی javacهای جدید NPE می‌دهد).

```bash
cd android
export BUILD_TOOLS=/path/to/build-tools/34.0.0
export ANDROID_JAR=/path/to/platforms/android-34/android.jar
export R8_JAR=/path/to/r8-8.5.35.jar   # از dl.google.com/android/maven2/com/android/tools/r8/
bash build_apk.sh
# خروجی: android/build/LabelVoice-Android-1.0.2.apk
```

کلید امضا در `keystore/labelvoice.keystore` (در گیت نیست) ساخته می‌شود؛ برای به‌روزرسانی‌های بعدی **همان کلید را نگه دارید** وگرنه کاربر باید اپ را حذف و دوباره نصب کند. رمز فعلی: `labelvoice-sign`.

## حریم خصوصی

OCR و پردازش تصویر کاملاً **روی خود دستگاه** اجرا می‌شود؛ تصویر برچسب هرگز از گوشی خارج نمی‌شود. مرز ایمنی محصول (فقط خواندن متن بسته، بدون هیچ توصیه پزشکی) در این نسخه عیناً برقرار است.

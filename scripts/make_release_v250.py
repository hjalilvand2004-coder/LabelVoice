#!/usr/bin/env python3
"""انتشار Release v2.5.0 — توکن فقط گذرا از ورودی استاندارد؛ هرگز ذخیره نمی‌شود."""
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

REPO = "hjalilvand2004-coder/LabelVoice"
TOKEN = os.environ.get("GH_TOKEN") or sys.stdin.readline().strip()
VERSION = "2.5.0"
ASSETS = [
    ("/home/z/my-project/labelvoice-clone/mobile-app/label-reader-singlefile.html",
     f"label-reader-singlefile-v{VERSION}.html",
     "تک‌فایل قابل حمل با انتخاب‌گر ۹موتوره (۵ مرورگری + ۴ پل دسکتاپ) + موتور OCR تعبیه‌شده — اجرا بدون پایتون با دوبار کلیک"),
    ("/home/z/my-project/download/LabelVoice-v2.5.0-Portable-Web.zip",
     f"LabelVoice-v{VERSION}-Portable-Web.zip",
     "بستهٔ قابل حمل: START-HERE + تک‌فایل + webapp/ + لانچرها + START-BRIDGE.bat/.sh (پل OCR)"),
    ("/home/z/my-project/download/LabelVoice-v2.5.0-Mobile-App-PWA.zip",
     f"LabelVoice-v{VERSION}-Mobile-App-PWA.zip",
     "اپ موبایل (PWA): انتخاب‌گر ۹موتوره + کادر پل OCR + Service Worker v18 + Manifest + آیکون‌ها"),
    ("/home/z/my-project/download/LabelVoice-v2.5.0-Full-Project.zip",
     f"LabelVoice-v{VERSION}-Full-Project.zip",
     "کل پروژه: دسکتاپ Streamlit + پل OCR (bridge.py) + وب + اپ موبایل + آزمون‌ها + مستندات"),
    ("/home/z/my-project/labelvoice-clone/android/build/LabelVoice-Android-2.5.0.apk",
     f"LabelVoice-v{VERSION}-Android.apk",
     "نسخهٔ نصب‌پذیر اندروید (versionCode 17) — رفع پخش صوتی با پل بومی TTS + انتخاب‌گر موتور؛ امضاشده"),
]
BODY = """## برچسب‌خوان هوشمند دارو و محصولات — نسخه ۲.۵.۰

**توسعه و طراحی: حمید جلیلوند و نوید بدری**

### ۱) «جایی که انتخاب مدل OCR واقعاً صورت بگیرد» — هم در موبایل اپلیکیشن و هم در وب‌سایت ✅
بازخورد: «پیغام می‌دهد موتورها در منوی موتور OCR دسکتاپ در دسترس‌اند، ولی در عمل جایی نیست که این انتخاب صورت بگیرد».

انتخاب‌گر «🧠 موتور و مدل خوانش (OCR)» اکنون در وب / PWA / تک‌فایل / APK **۹ گزینهٔ واقعاً مؤثر** دارد:

| گروه | گزینه‌ها | کجا اجرا می‌شود |
|---|---|---|
| روی همین دستگاه (WASM) | Tesseract.js سریع (integer) و دقیق‌تر (LSTM/best) × زبان‌های `fas` / `eng` / `fas+eng` | داخل مرورگر — کاملاً آفلاین |
| 🛰️ **پل OCR** (v2.5.0) | **EasyOCR** · **Surya** · **Qwen3-VL-2B-Instruct** · **Tesseract 5** | روی رایانهٔ دسکتاپِ خود شما |

- **پل OCR چگونه کار می‌کند؟** موتورهای سنگین پایتونی‌اند و داخل مرورگر اجرا نمی‌شوند. سرور کوچک محلی (`label_reader/bridge.py`) روی رایانهٔ شما بالا می‌آید — در دسکتاپ: سایدبار ← «🛰️ پل OCR برای موبایل/وب» ← شروع (یا `START-BRIDGE.bat`) — سپس آدرس نمایش‌داده‌شده (مثل `http://192.168.1.5:8770`) را در کادر پلِ انتخاب‌گر موبایل/وب وارد و «بررسی اتصال» را بزنید. `/ping` فهرست موتورهای آمادهٔ رایانه را نشان می‌دهد؛ انتخاب موتور در `localStorage` ذخیره می‌شود.
- **حریم خصوصی:** تصویر فقط بین دستگاه شما و رایانهٔ خودتان در شبکهٔ محلی رد و بدل می‌شود؛ ذخیره‌سازی یا لاگ محتوایی وجود ندارد (لاگ فقط متد/مسیر/کد).
- **بدون میان‌بر:** خروجی پل از همان فیلتر قطعات زباله، ادغام بهترین-اول، گیت کیفیت و پاسخ فارسی نگهبان‌دار عبور می‌کند؛ نام موتور در اعلام مرحله ۲ و JSON درج می‌شود.
- درجناخوانی گزینه‌های مرورگری: در تک‌فایل زبان با دادهٔ تعبیه‌شده واقعاً انتخاب می‌شود؛ روی PWA/APK کیفیت integer/best هم اعمال می‌شود (APK از CDN `4.0.0_best`).

### ۲) رفع «پخش صوتی پاسخ در موبایل اپلیکیشن کار نمی‌کند» ✅
`speechSynthesis` داخل WebView اندروید روی بسیاری از دستگاه‌ها بی‌صداست. راه‌حل: **پل بومی TextToSpeech اندروید** (`LabelVoiceTts` در MainActivity — speak/stop/ready/langStatus با اولویت صدای فارسی `fa-IR`). ترتیب در `app.js`: پل بومی APK ← speechSynthesis مرورگر (PWA) ← پیام راهنمای شفاف. برای صدای فارسی در هر دستگاهی، «بستهٔ صوتی فارسی» را در تنظیمات «موتور متن‌به‌گفتار» سیستم نصب کنید.

### ۳) هدر جدید — پالت سفارشی شما ✅
هدر تصویری حذف و به‌جای آن هدر با **پالت سفید + آبی کمرنگ + آبی پررنگ + سبز + قرمز** در هر سه رابط (دسکتاپ، موبایل/PWA، START-HERE) پیاده شد — با نوار چهاررنگ هماهنگ و تیتر آبی پررنگ؛ در حالت تاریک همان گرادیان سرمه‌ای.

#### تغییرات فنی
- `label_reader/bridge.py` (جدید): سرور استاندارد-کتابخانه‌ای (`GET /ping`, `POST /ocr?engine=…`) با CORS، سقف ۲۰MB و پاک‌سازی فوری تصویر از حافظه
- `app.py`: بخش «🛰️ پل OCR برای موبایل/وب» در سایدبار (شروع/توقف + پورت + IP محلی)
- `mobile-app`: انتخاب‌گر دوگروهی با `optgroup` + کادر پل (آدرس + بررسی اتصال + وضعیت) + ذخیرهٔ فوری انتخاب
- `MainActivity.java`: `TextToSpeech` + `JavascriptInterface` + پاک‌سازی در `onDestroy`
- `css/style.css`: هدر پالتی + استایل‌های کادر پل · `sw.js` → کش `lbr-mobile-v18` · versionCode 17
- آزمون‌ها: **۱۳۱ pytest + ۶۴ Node + AppTest + ۱۸/۱۸ E2E رابط + ۵/۵ E2E چرخهٔ کامل پل (مرورگر → پل → Tesseract → فیلد → پاسخ فارسی)**

#### نکتهٔ نصب APK
> ⚠️ اگر نسخهٔ ۲.۳.۰ یا قدیمی‌تر نصب دارید، ابتدا **Uninstall** کنید (کلید امضا در ریست محیط عوض شده است)؛ از ۲.۴.۰ به بعد کلید یکسان است و به‌روزرسانی مستقیم ممکن است.
> اگر پس از نصب پخش صوتی باز هم صدایی نداد: در تنظیمات اندروید ← «موتور متن‌به‌گفتار» بستهٔ صوتی فارسی (مثلاً Google TTS ← فارسی) را نصب کنید.
"""

API = f"https://api.github.com/repos/{REPO}"


def req(method: str, url: str, data=None, headers=None, raw=False):
    h = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}
    if headers:
        h.update(headers)
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(r, timeout=300) as resp:
        body = resp.read()
        return body if raw else (json.loads(body) if body else {})


def upload(url: str, path: Path, name: str) -> None:
    mime = "application/octet-stream"
    for attempt in range(1, 4):
        try:
            data = path.read_bytes()
            req("POST", url + f"?name={name}", data=data,
                headers={"Content-Type": mime, "Content-Length": str(len(data))})
            print(f"  ✓ {name} ({len(data)//1024//1024}MB)")
            return
        except Exception as exc:  # noqa: BLE001
            print(f"  ! تلاش {attempt} ناموفق: {exc}")
            time.sleep(4 * attempt)
    raise SystemExit(f"آپلود {name} ناموفق ماند")


def main() -> None:
    # ۱) تگ
    tag_ref = f"https://api.github.com/repos/{REPO}/git/refs"
    commits = req("GET", f"{API}/commits/main")
    sha = commits["sha"]
    try:
        req("POST", f"{tag_ref}", data=json.dumps({
            "ref": f"refs/tags/v{VERSION}", "sha": sha}).encode())
        print(f"✓ تگ v{VERSION} روی {sha[:9]}")
    except Exception as exc:  # noqa: BLE001
        print(f"! تگ: {exc}")

    # ۲) Release
    rel = req("POST", f"{API}/releases", data=json.dumps({
        "tag_name": f"v{VERSION}",
        "name": f"LabelVoice v{VERSION} — پل OCR + رفع پخش صوتی اندروید + هدر پالتی",
        "body": BODY,
        "draft": False,
        "prerelease": False,
    }).encode())
    print(f"✓ Release id={rel['id']}: {rel['html_url']}")

    # ۳) دارایی‌ها
    up_url = rel["upload_url"].split("{")[0]
    for local, name, _note in ASSETS:
        p = Path(local)
        assert p.exists(), f"یافت نشد: {p}"
        upload(up_url, p, name)

    print("تمام شد:", rel["html_url"])


if __name__ == "__main__":
    main()

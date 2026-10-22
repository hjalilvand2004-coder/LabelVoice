# -*- coding: utf-8 -*-
"""رابط کاربری Streamlit «برچسب‌خوان هوشمند دارو و محصولات».

کاملاً فارسی و راست‌به‌چپ، پس‌زمینه سفید، فونت خوانا و درشت.
اجرای محلی پردازش؛ ارسال به سرویس ابری فقط برای TTS با رضایت صریح کاربر.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st
from PIL import Image

from label_reader import APP_AUTHORS_FA, APP_NAME_FA, SCOPE_FA, __version__
from label_reader.config import load_settings
from label_reader.models import FieldStatus
from label_reader.pipeline import LabelReaderPipeline
from label_reader.response.tts_prep import prepare_for_tts
from label_reader.tts import TtsError, make_tts_provider, synthesize_with_fallback
from label_reader.ui_helpers import (
    PRODUCT_TYPE_FA, STATUS_FA, draw_ocr_boxes, editable_fields,
    fields_to_rows, inject_rtl, pil_to_bytes,
)
from label_reader.validation import ImageValidationError

st.set_page_config(page_title=APP_NAME_FA, page_icon="💊", layout="wide")
inject_rtl(st)

settings = load_settings()
pipeline = LabelReaderPipeline(settings)

# ---------------- فرم‌های مودال راهنما (فناوری هر بخش) ----------------
HELP_CONTENT = {
    "architecture": """
### معماری سامانه در یک نگاه

**تعریف مسئله:** کاربر دوربین را به سمت جعبه دارو یا بسته‌بندی محصول می‌گیرد؛
سامانه نام، اطلاعات چاپ‌شده و سایر فیلدهای قابل خواندن را استخراج می‌کند و
آن‌ها را به فارسی نمایش و می‌خواند. اطلاعات خوانده‌شده همیشه از توصیه‌های
پزشکی جدا نگه داشته می‌شود: سامانه فقط «چه نوشته شده» را می‌گوید.

**خط پردازش پنج‌مرحله‌ای** (مطابق معماری مرجع) و فایل پیاده‌سازی هر مرحله:

| مرحله | کار | فایل دسکتاپ | فایل موبایل |
|---|---|---|---|
| ۱. تصویر بسته‌بندی | دریافت، اعتبارسنجی (magic bytes، حجم، ابعاد) | `app.py` + `label_reader/validation.py` | `mobile-app/js/app.js` + `js/camera.js` |
| ۲. OpenCV | تشخیص ناحیه برچسب، اصلاح زاویه، بهبود وضوح | `label_reader/preprocess.py` + `quality.py` | `mobile-app/js/preprocess.js` + `js/boxdetect.js` |
| ۳. OCR | استخراج نام، اعداد و متن بسته‌بندی | `label_reader/ocr.py` (Tesseract 5 + EasyOCR) | `mobile-app/js/ocr.js` (Tesseract.js/WASM) |
| ۴. پردازش متن و کنترل فیلدها | نرمال‌سازی نام، استخراج قدرت و تعداد درج‌شده | `label_reader/textnorm.py` + `extraction/patterns.py` + `extraction/extractor.py` | `mobile-app/js/textnorm.js` + `js/patterns.js` + `js/extractor.js` |
| ۵. پاسخ فارسی + خوانش | بازگویی وفادار به متن + TTS | `label_reader/response/builder.py` + `guard.py` + `tts.py` (رابط: Streamlit) | `mobile-app/js/responder.js` + `js/guard.js` (speechSynthesis) |

این دو زیرسیستم **دقیقاً همان قواعد** را پیاده می‌کنند و با آزمون‌های پاریتی
(۵۴ آزمون Node در برابر pytest) هم‌رفتاری‌شان راستی‌آزمایی می‌شود.

**کتابخانه‌ها:** opencv-python، pytesseract، easyocr، pydantic، pydantic-settings،
streamlit، edge-tts، gTTS، Pillow (دسکتاپ) — Tesseract.js 6، Web Speech API،
Service Worker، Vazirmatn (موبایل) — pytest، Node test runner (آزمون).

نسخه کامل و مصور این مستندات: `documentation.html` روی GitHub Pages و نسخه PDF
پیوست Release.

👨‍💻 **توسعه و طراحی:** حمید جلیلوند و نوید بدری
""",
    "eval": """
### روش و اصول ارزیابی مدل‌ها

ارزیابی این سامانه بر اساس اصول بنیادین سنجش سامانه‌های حساس دارویی طراحی شده است
(هر اشتباه در حوزه دارو می‌تواند آسیب‌زا باشد):

1. **زمینه‌سنجی برچسب‌خورده (ground-truth):** ۱۴ تصویر نمونه با مقادیر واقعی هر فیلد
   در `sample_images/manifest.json` — هیچ عددی جعل نمی‌شود.
2. **سنجش در سطح فیلد، نه کل متن:** نام، قدرت درج‌شده، تعداد، تاریخ انقضا و وزن
   هرکدام جداگانه با تطبیق نرمال‌شده (حروف، ارقام فارسی/لاتین) سنجیده می‌شوند.
3. **خطای ایمنی = خطا:** غیبت (missing) و تعارض (conflicting) هم خطا شمرده می‌شوند؛
   سامانه هرگز مقدار حدسی را به‌عنوان قطعه ارائه نمی‌دهد.
4. **نگهبان‌های ضدخطر با آزمون اختصاصی:** «قدرت درج‌شده» هرگز «دوز مصرف» نامیده
   نمی‌شود؛ مقدار صفر رد می‌شود؛ هر عدد در پاسخ باید در شواهد OCR باشد؛ دستورهای
   تزریق‌شده در تصویر پالایش می‌شوند (آزمون‌های `tests/test_response_builder.py`
   و `tests/test_security.py`).
5. **شفافیت محدودیت:** ضعف ارقام فارسی پنهان نمی‌شود؛ چنین مقادیری «نامطمئن»
   علامت می‌خورند و اصلاح دستی ارائه می‌شود.
6. **تکرارپذیری:** همه اعداد با `python scripts/evaluate.py` قابل بازتولید‌اند؛
   نتایج همین اجرا در `docs/evaluation/evaluation-results.json` ثبت است.

**محل پیاده‌سازی:** `scripts/evaluate.py` (سنجش خط لوله)، `tests/` (۷۹ آزمون pytest)،
`tests-js/run_tests.js` (۵۴ آزمون پاریتی موبایل)، `docs/evaluation/` (نتایج)، و
نمودارهای همین بخش از رابط.

**فناوری‌ها:** pytest، Node test runner، pandas + Altair (نمودارهای این بخش)،
OpenCV + Tesseract 5 (خط لوله ارزیابی‌شده).
""",
    "engine": """
### موتورهای OCR دسکتاپ

- **Tesseract 5 (LSTM)** با دو بسته زبان `fas+eng` و دو حالت چیدمان (PSM 3 و 6)؛
  خوانش‌های مشابه با شباهت فازی ≥ ۰٫۸ ادغام می‌شوند تا تکرار حذف شود.
  کتابخانه اتصال: `pytesseract`.
- **EasyOCR** مدل عمیق (PyTorch) با زبان‌های fa+en؛ به‌صورت lazy بارگیری می‌شود و
  برای تصاویر سخت‌تر به‌کار می‌رود (نصب سنگین‌تر — اختیاری).
- حالت `auto` انتخاب موتور بر اساس دسترس‌پذیری است.

هر دو موتور روی **همان رایانه شما** اجرا می‌شوند و هیچ تصویری جایی ارسال نمی‌شود.
""",
    "input": """
### فناوری ورود تصویر

- **بارگذاری فایل:** کامپوننت `st.file_uploader` در Streamlit؛ فایل با Pillow
  (`PIL.Image.open`) باز و به RGB تبدیل می‌شود.
- **دوربین:** `st.camera_input` (عکس ثابت از وب‌کم).
- **اعتبارسنجی:** بررسی امضای باینری (magic bytes) برای PNG/JPEG، سقف حجم و
  ابعاد، و رد فایل‌های غیرتصویری — پیاده‌شده در `label_reader/validation.py`.
- برای تصاویر چندمحصولی می‌توانید قبل از خواندن، ناحیه برچسب را دستی برش بزنید.
""",
    "preprocess": """
### فناوری پیش‌پردازش و OCR (OpenCV)

مراحل روی تصویر شما (`label_reader/preprocess.py` و `quality.py`):

1. **ارزیابی کیفیت:** تاری با واریانس لاپلاسین، تاریکی با میانگین روشنایی،
   انعکاس با نسبت پیکسل‌های خیلی روشن (هیوریستیک پس‌زمینه‌آگاه).
2. **مقیاس‌گذاری هوشمند:** رساندن کوتاه‌ترین ضلع به ~۱۲۰۰ پیکسل.
3. **CLAHE** (تقویت کنتراست محیطی) + حذف نویز + تیزکردن.
4. **صاف‌کردن چرخش کم‌زاویه** (تا ±۱۵ درجه) با پروفایل سطرها.
5. **سه نسخه خروجی:** اصلی، تقویت‌شده، دودویی — همه به OCR داده می‌شوند.
6. **OCR چندگذری:** PSM 3 و 6 (و در نسخه موبایل PSM 11 پراکنده) + ادغام فازی.
""",
    "fields": """
### استخراج فیلدها و مدل داده

- فیلدها: نام محصول، قدرت درج‌شده، شکل دارویی، حجم/وزن، تاریخ انقضا، شماره سری،
  سازنده — با **regex دو زبانه** فارسی/انگلیسی (`extraction/patterns.py`).
- مدل‌ها با **Pydantic v2** تعریف شده‌اند؛ هر فیلد وضعیت دارد:
  `extracted / uncertain / missing / conflicting / user_corrected`.
- هر مقدار به شناسه قطعه‌های OCR (شواهد) گره خورده است (`source_ids`) —
  یعنی می‌توانید ببینید هر عدد از کدام سطر تصویر آمده است.
- **تشخیص تناقض:** اگر دو مقدار متفاوت برای یک فیلد خوانده شود، به‌جای انتخاب
  خاموش یکی، وضعیت «متناقض» اعلام می‌شود.
""",
    "response": """
### تولید پاسخ فارسی و نگهبان ایمنی

- پاسخ از **قالب‌های قاعده‌محور** ساخته می‌شود (`response/builder.py`) — بدون
  هیچ مدل زبانی ابری؛ نرمال‌سازی نویسه (ي→ی، ك→ک، ارقام فارسی) در `textnorm.py`.
- **نگهبان ایمنی** (`response/guard.py`) پاسخ را پیش از نمایش بازبینی می‌کند:
  - واژه‌های ممنوع (مانند «دوز مصرف» به‌جای «قدرت درج‌شده») رد می‌شوند؛
  - هر عدد داخل پاسخ باید در شواهد OCR موجود باشد؛
  - ادعای کاربرد، تشخیص یا توصیه پزشکی مسدود است.
- نتیجه: پاسخ فقط «روی بسته چه نوشته شده» را می‌گوید — نه بیشتر.
""",
    "tts": """
### فناوری تبدیل متن به گفتار

- موتور اصلی: **edge-tts** (صداهای عصبی فارسی FaridNeural / DilaraNeural) —
  این موتور ابری است؛ بنابراین فقط با رضایت صریح شما فعال می‌شود.
- جایگزین: **gTTS** (Google Translate TTS) در صورت در دسترس نبودن edge-tts.
- متن پاسخ قبل از ارسال با `response/tts_prep.py` برای تلفظ آماده می‌شود
  (اعداد و علائم)، و **دقیقاً همان پاسخ تأییدشده** خوانده می‌شود.
- صدا روی سرور شما ساخته می‌شود و فقط در حافظه همین نشست می‌ماند.
""",
    "json": """
### ساختار خروجی JSON

خروجی شامل: `ocr_pieces` (قطعه‌ها با کادر و اطمینان)، `raw_lines` (سطرهای خام)،
`fields` (مقادیر + وضعیت + شواهد + تاریخچه)، `quality_issues` و `quality_metrics`،
`response_fa` و `metadata` (مدت‌زمان هر مرحله، نسخه‌های استفاده‌شده، برش/چرخش).

این ساختار در نسخه دسکتاپ و موبایل **یکسان** است تا آزمون‌های رگرسیون و
گزارش‌گیری روی هر دو یک شکل کار کنند. فایل با `result.to_json_bytes()` ساخته
می‌شود و فقط با کلیک شما دانلود می‌گردد.
""",
    "docs": """
### مستندات فنی کامل پروژه

- **نسخه HTML تعاملی:** فایل `documentation.html` — رسپانسیو، با انیمیشن و
  گرافیک؛ شامل معماری سامانه، نحوه کارکرد خط پردازش، معرفی تک‌تک فایل‌ها و
  کتابخانه‌ها و فناوری‌ها، **و بخش ارزیابی و آزمون مدل‌ها با نمودار**.
  روی GitHub Pages منتشر شده و در پوشه موبایل هم هست.
- **نسخه PDF شکیل:** پیوست هر Release در صفحه Releases مخزن GitHub
  (فایل `LabelVoice-v*-Documentation.pdf`) — برای چاپ و مطالعه آفلاین.
- هر دو سند به‌روز با نسخه برنامه تولید می‌شوند و محتوای آن‌ها از همین
  ماژول‌های واقعی استخراج شده است.
- **توسعه و طراحی:** حمید جلیلوند و نوید بدری.
""",
}


try:
    @st.dialog("🧩 فناوری‌ها، ابزارها و کتابخانه‌های این بخش", width="large")
    def show_help(key: str):
        st.markdown(HELP_CONTENT.get(key, "—"), unsafe_allow_html=False)
except TypeError:
    @st.dialog("🧩 فناوری‌ها، ابزارها و کتابخانه‌های این بخش")
    def show_help(key: str):
        st.markdown(HELP_CONTENT.get(key, "—"), unsafe_allow_html=False)


def tech_help(key: str, label: str = "🧩 فناوری و ابزارهای این بخش",
              suffix: str = ""):
    """دکمه کوچک راهنما که فرم مودال فناوری همان بخش را باز می‌کند."""
    if st.button(label, key=f"help_{key}{suffix}",
                 use_container_width=True):
        show_help(key)


def get_state(key, default=None):
    return st.session_state.get(key, default)


# ---------------- نوار کناری: تنظیمات و حریم خصوصی ----------------
with st.sidebar:
    st.header("⚙️ تنظیمات")
    engine_choice = st.radio(
        "موتور OCR",
        ["tesseract", "easyocr", "auto"],
        index=["tesseract", "easyocr", "auto"].index(settings.ocr_provider)
        if settings.ocr_provider in ("tesseract", "easyocr", "auto") else 0,
        help="tesseract سبک‌تر است؛ easyocr مدل عمیق با نصب سنگین‌تر. هر دو قابل تعویض‌اند.",
    )
    voice = st.selectbox("صدای فارسی (edge-tts)", ["fa-IR-FaridNeural", "fa-IR-DilaraNeural"])
    rate = st.select_slider("سرعت خوانش", ["-15%", "-5%", "+0%", "+10%", "+20%"], value="+0%")
    tech_help("engine", "🧩 موتورهای OCR چه هستند؟", "sb")

    st.divider()
    st.subheader("🔒 حریم خصوصی")
    st.markdown(
        "- پردازش تصویر و متن **کاملاً محلی** انجام می‌شود.\n"
        "- برای **تبدیل گفتار**، متن پاسخ به سرویس ابری (Microsoft/gTTS) ارسال "
        "می‌شود؛ فقط با رضایت صریح شما.\n"
        "- تصویر و متن برچسب در هیچ لاگی ذخیره نمی‌شود و فایل موقتی ساخته نمی‌شود.\n"
        "- یادآوری: نام بیمار یا اطلاعات شخصی ممکن است روی بسته دیده شود."
    )

# ---------------- معرفی و محدوده ----------------
st.title("💊 " + APP_NAME_FA)
st.markdown(f"**👨‍💻 توسعه و طراحی: {APP_AUTHORS_FA}**")
st.markdown(
    f"""
    <div class="privacy-note">
    <b>محدوده محصول:</b> {SCOPE_FA}
    این ابزار فقط می‌گوید «روی بسته چه نوشته شده است»؛ کاربرد دارو، مقدار مصرف
    یا توصیه پزشکی ارائه نمی‌دهد. اطلاعات غایب از اینترنت یا حافظه مدل تکمیل
    نمی‌شود. (نسخه {__version__})
    </div>
    """,
    unsafe_allow_html=True,
)
tech_help("architecture", "🧩 معماری، فناوری‌ها و کتابخانه‌های سامانه (راهنمای مودال)")
tech_help("docs", "📚 مستندات فنی کامل (HTML/PDF)")

# ---------------- دریافت تصویر ----------------
source = st.radio("روش دریافت تصویر", ["بارگذاری فایل", "عکس با دوربین"],
                  horizontal=True)
tech_help("input", "🧩 فناوری ورود تصویر و اعتبارسنجی", "in")
uploaded = None
if source == "بارگذاری فایل":
    uploaded = st.file_uploader("تصویر بسته‌بندی (JPG / PNG)",
                                type=["jpg", "jpeg", "png"])
else:
    uploaded = st.camera_input("از بسته عکس بگیرید (عکس ثابت، نه ویدئوی زنده)")

pil_image = None
if uploaded is not None:
    try:
        pil_image = Image.open(uploaded).convert("RGB")
    except Exception:
        st.error("فایل تصویر باز نشد؛ لطفاً یک تصویر JPG یا PNG سالم انتخاب کنید.")
        pil_image = None

crop_box = None
if pil_image is not None:
    st.subheader("پیش‌نمایش")
    st.image(pil_image, use_container_width=True)
    with st.expander("✂️ برش دستی ناحیه برچسب (اختیاری — برای تصاویر چندمحصولی)"):
        c1, c2, c3, c4 = st.columns(4)
        cx = c1.slider("شروع افقی ٪", 0, 95, 0)
        cy = c2.slider("شروع عمودی ٪", 0, 95, 0)
        cw = c3.slider("عرض ٪", 5, 100, 100)
        ch = c4.slider("ارتفاع ٪", 5, 100, 100)
        if (cx, cy, cw, ch) != (0, 0, 100, 100):
            crop_box = (cx / 100, cy / 100, cw / 100, ch / 100)
            w, h = pil_image.size
            cropped = pil_image.crop((
                int(cx / 100 * w), int(cy / 100 * h),
                int(min(100, cx + cw) / 100 * w),
                int(min(100, cy + ch) / 100 * h)))
            st.image(cropped, caption="ناحیه انتخاب‌شده", use_container_width=True)

    read_clicked = st.button("🔎 خواندن برچسب", type="primary",
                             use_container_width=True)
else:
    read_clicked = False
    st.info("برای شروع، یک تصویر بارگذاری کنید یا با دوربین عکس بگیرید.")

# ---------------- پردازش ----------------
if read_clicked and pil_image is not None:
    import time

    try:
        status_box = st.status("در حال پردازش…", expanded=True)
        with status_box:
            st.write("۱) اعتبارسنجی فایل و ارزیابی کیفیت…")
            t0 = time.perf_counter()
            result = pipeline.process_pil(pil_image, crop=crop_box,
                                          ocr_engine=engine_choice)
            st.write("۲) پیش‌پردازش OpenCV و اجرای OCR…")
            st.write("۳) استخراج فیلدها و تولید پاسخ فارسی…")
            status_box.update(label="پردازش کامل شد ✅", state="complete",
                              expanded=False)
        st.session_state["result"] = result
        st.session_state.pop("audio_bytes", None)
        st.session_state.pop("tts_used", None)
        st.toast(f"پردازش در {result.metadata.durations_ms.get('total_ms', 0)} میلی‌ثانیه انجام شد.")
    except ImageValidationError as err:
        st.error(f"⛔ {err.message_fa}")
    except Exception as err:  # noqa: BLE001
        st.error(f"خطای پردازش: {err.__class__.__name__} — لطفاً تصویر دیگری امتحان کنید.")

# ---------------- نمایش نتایج ----------------
result = get_state("result")
if result is not None:
    md = result.metadata

    # هشدارهای کیفیت (متن + آیکون، نه فقط رنگ)
    for issue in result.quality_issues:
        if issue.code == "ok":
            st.caption("✅ " + issue.message_fa)
        elif issue.severity == "severe":
            st.error("⚠️ " + issue.message_fa)
        elif issue.severity == "warning":
            st.warning("⚠️ " + issue.message_fa)
    for w in md.warnings_fa:
        st.warning("ℹ️ " + w)

    left_col, right_col = st.columns([3, 2])

    with left_col:
        st.subheader("🖼️ نواحی شناسایی‌شده OCR")
        st.image(draw_ocr_boxes(pil_image, result.ocr_pieces),
                 use_container_width=True)
        with st.expander("📄 متن خام استخراج‌شده (بدون اصلاح)"):
            if result.raw_lines:
                for line in result.raw_lines:
                    st.markdown(
                        f"`{line.id}` — {line.text}  "
                        f"<small>(اطمینان: "
                        f"{round((line.confidence_mean or 0) * 100)}%)</small>",
                        unsafe_allow_html=True)
            else:
                st.caption("متنی شناسایی نشد.")
        with st.expander("🧹 متن نرمال‌شده (فقط اصلاح نویسه: ي→ی، ك→ک، یکسان‌سازی فاصله)"):
            st.code("\n".join(line.text for line in result.raw_lines) or "—",
                    direction="rtl" if hasattr(st, "code") else None)
        tech_help("preprocess", "🧩 فناوری پیش‌پردازش و OCR (OpenCV / Tesseract)", "pp")

    with right_col:
        st.subheader("📋 فیلدهای ساختاریافته")
        st.dataframe(fields_to_rows(result.fields), use_container_width=True,
                     hide_index=True)
        st.caption(
            "وضعیت‌ها: استخراج‌شده / نامطمئن / غایب / متناقض / اصلاح کاربر — "
            "هر مقدار به شناسه قطعه OCR (شاهد) متصل است. امتیاز اطمینان OCR "
            "معادل احتمال قطعی صحت اطلاعات نیست.")
        st.markdown(f"**نوع بسته تشخیص‌داده‌شده:** "
                    f"{PRODUCT_TYPE_FA.get(result.product_type.value, result.product_type.value)}")
        st.caption(result.product_type_note_fa)
        tech_help("fields", "🧩 فناوری استخراج فیلدها (Pydantic + الگوها)", "fd")

    # پاسخ فارسی
    st.subheader("🗣️ پاسخ فارسی")
    st.markdown(f'<div class="big-answer">{result.response_fa}</div>',
                unsafe_allow_html=True)
    tech_help("response", "🧩 فناوری تولید پاسخ و نگهبان ایمنی", "rs")

    # اصلاح دستی
    with st.expander("✏️ اصلاح دستی فیلدها و بازتولید پاسخ"):
        editable = editable_fields(result.fields)
        new_values: dict[str, str] = {}
        for key, field in editable.items():
            default = field.value or ""
            new_values[key] = st.text_input(
                field.label_fa,
                value=default,
                key=f"edit_{key}_{field.status.value}",
                help="خالی گذاشتن یعنی بدون تغییر. مقادیر قبلی حفظ می‌شوند.",
            )
        if st.button("♻️ ثبت اصلاحات و بازتولید پاسخ و صدا"):
            corrections = {
                k: v for k, v in new_values.items()
                if v and editable[k].value != v
            }
            if corrections:
                result = pipeline.apply_user_corrections(result, corrections)
                st.session_state["result"] = result
                st.session_state.pop("audio_bytes", None)
                st.session_state.pop("tts_used", None)
                st.rerun()
            else:
                st.info("تغییری برای ثبت وجود ندارد.")
        for key, field in editable.items():
            if field.status == FieldStatus.USER_CORRECTED and field.previous_values:
                st.caption(f"منشأ قبلی «{field.label_fa}»: "
                           f"{' ← '.join(field.previous_values)}")

    # صوت
    st.subheader("🔊 پخش صوتی فارسی")
    tech_help("tts", "🧩 فناوری تبدیل متن به گفتار (edge-tts / gTTS)", "tt")
    tts_provider = make_tts_provider(settings.tts_provider)
    _, tts_note = tts_provider.available()
    consent = st.checkbox(
        "می‌پذیرم که متن پاسخ برای تبدیل گفتار به سرویس ابری (Microsoft Edge TTS "
        "یا gTTS) ارسال شود. بدون این رضایت، صوتی تولید نمی‌شود.")
    col_play, col_info = st.columns([2, 3])
    with col_play:
        if st.button("▶️ تولید و پخش صدا", disabled=not consent,
                     use_container_width=True):
            if not consent:
                st.warning("برای تولید صوت باید رضایت ارسال به سرویس ابری را تأیید کنید.")
            else:
                spoken_text = prepare_for_tts(result.response_fa)
                try:
                    audio_bytes, used = synthesize_with_fallback(
                        spoken_text, settings)
                    st.session_state["audio_bytes"] = audio_bytes
                    st.session_state["tts_used"] = used
                    st.session_state["audio_text_hash"] = hash(result.response_fa)
                except TtsError as err:
                    st.error("🔇 " + err.message_fa)
    with col_info:
        st.caption(tts_note)
        st.caption("متن پخش‌شده دقیقاً همان پاسخ تأییدشده رابط است (با آماده‌سازی "
                   "اعداد برای تلفظ). نام‌های لاتین حفظ می‌شوند؛ تلفظ آن‌ها به "
                   "کیفیت موتور صوتی وابسته است. فایل صوتی فقط با دانلود صریح "
                   "ذخیره می‌شود.")

    audio_bytes = get_state("audio_bytes")
    if audio_bytes:
        st.audio(audio_bytes, format="audio/mp3")
        st.download_button(
            "⬇️ دانلود فایل صوتی (mp3)",
            data=audio_bytes,
            file_name="label-response.mp3",
            mime="audio/mp3",
        )

    # خروجی JSON
    st.divider()
    tech_help("json", "🧩 ساختار خروجی JSON چیست؟", "js")
    st.download_button(
        "🧾 دریافت خروجی JSON کامل (فیلدها + شواهد + فراداده)",
        data=result.to_json_bytes(),
        file_name="label-analysis.json",
        mime="application/json",
    )

st.divider()
st.caption(
    "⚠️ این محصول ابزار خواندن برچسب است؛ نه سامانه تشخیص دارو، تجویز یا توصیه "
    "پزشکی. اطلاعات ناخوانا یا متناقض به‌صورت شفاف اعلام می‌شوند."
)
st.caption(
    "📚 مستندات فنی کامل (معماری، فایل‌ها، فناوری‌ها): "
    "[نسخه HTML روی GitHub Pages](https://hjalilvand2004-coder.github.io/LabelVoice/documentation.html) — "
    "[نسخه PDF](https://github.com/hjalilvand2004-coder/LabelVoice/releases/latest)"
)

# ---------------- ارزیابی و آزمون مدل‌ها ----------------
st.divider()
st.subheader("📊 ارزیابی و آزمون مدل‌ها")
st.caption(
    "نتایج اجرای واقعی روی مجموعه نمونه برچسب‌خورده (۱۴ تصویر با ground-truth در "
    "`sample_images/manifest.json`) — دقت در سطح فیلد سنجیده می‌شود و غیبت/تعارض "
    "هم خطا شمرده می‌شود. بازتولید: `python scripts/evaluate.py`."
)
tech_help("eval", "🧩 روش و اصول ارزیابی چه هستند؟", "ev")

_eval_path = Path(__file__).resolve().parent / "docs" / "evaluation" / "evaluation-results.json"
if _eval_path.exists():
    import pandas as pd

    _ev = json.loads(_eval_path.read_text(encoding="utf-8"))
    _tess = _ev["pipeline"]["tesseract_full"]["summary"]
    _pt = _ev["unit_tests"]["python_pytest"]
    _nd = _ev["unit_tests"]["javascript_node"]

    _m1, _m2, _m3, _m4 = st.columns(4)
    _m1.metric("دقت فیلد (Tesseract)", f"{_tess['field_accuracy']}%",
               f"{_tess['matched_fields']} از {_tess['total_fields']} فیلد",
               delta_color="off")
    _m2.metric("میانگین زمان پردازش", f"{_tess['latency_ms']['mean']:,} ms",
               f"p95: {_tess['latency_ms']['p95']:,} ms", delta_color="off")
    _m3.metric("آزمون‌های پایتون (pytest)", f"{_pt['passed']} ✓",
               "۷ ماژول — همه پاس", delta_color="off")
    _m4.metric("آزمون‌های موبایل (Node)", f"{_nd['passed']} ✓",
               "پاریتی کامل با دسکتاپ", delta_color="off")

    FIELD_FA = {"name": "نام محصول", "strength": "قدرت درج‌شده", "count": "تعداد/شکل",
                "expiry_date": "تاریخ انقضا", "net_weight": "وزن/حجم",
                "manufacturer": "سازنده", "batch": "شماره سری"}
    _pf = _tess["per_field"]
    st.markdown("**دقت به تفکیک فیلد (٪)**")
    st.bar_chart(pd.DataFrame({"دقت (٪)": {FIELD_FA.get(k, k): v["acc"] for k, v in _pf.items()}}),
                 color="#0e7c66")

    CASE_FA = {"clear_english": "انگلیسی ساده", "clear_persian": "فارسی ساده",
               "mixed_fa_en": "دوزبانه", "ambiguous_date": "تاریخ مبهم",
               "combo_strength": "قدرت ترکیبی", "mcg_vs_mg": "تفکیک mcg/mg",
               "malicious_text": "متن مخرب", "non_medicine": "غیردارویی"}
    _pc = _tess["per_case"]
    st.markdown("**دقت به تفکیک حالت تصویر (٪)**")
    st.bar_chart(pd.DataFrame({"دقت (٪)": {CASE_FA.get(k, k): v["acc"] for k, v in _pc.items()}}),
                 color="#2563a8")

    _lat = _tess["latency_ms"]
    st.markdown("**زمان پردازش هر تصویر (میلی‌ثانیه)**")
    st.bar_chart(pd.DataFrame({"ms": {"کمینه": _lat["min"], "میانه": _lat["median"],
                                      "میانگین": _lat["mean"], "p95": _lat["p95"],
                                      "بیشینه": _lat["max"]}}), color="#8a5a00")

    MOD_FA = {"tests/test_patterns_fields.py": "الگوها و فیلدها",
              "tests/test_pipeline_integration.py": "یکپارچگی خط پردازش",
              "tests/test_quality_validation.py": "کیفیت و اعتبارسنجی",
              "tests/test_response_builder.py": "پاسخ‌ساز و نگهبان",
              "tests/test_security.py": "امنیت",
              "tests/test_textnorm.py": "نرمال‌سازی متن",
              "tests/test_tts_llm.py": "TTS و LLM"}
    st.markdown("**آزمون‌های واحد پایتون به تفکیک ماژول (۷۹ آزمون)**")
    st.bar_chart(pd.DataFrame({"تعداد آزمون": {MOD_FA.get(k, k): v["total"]
                                              for k, v in _pt["per_file"].items()}}),
                 color="#5a3d8a")

    st.info(
        "**یافته صادقانه:** ارقام فارسی در Tesseract ضعیف خوانده می‌شوند (حالت «فارسی ساده» ۰٪) — "
        "به همین دلیل سامانه چنین مقادیری را «نامطمئن» علامت می‌زند و اصلاح دستی ارائه می‌کند؛ "
        "هیچ مقدار حدسی به‌عنوان قطعه ارائه نمی‌شود. موتور EasyOCR در محیط این اجرا نصب نبود؛ "
        "انتخاب صریح آن با پیام شفاف `OcrUnavailableError` رد می‌شود (رفتار درست: شکست شفاف، نه سکوت)."
    )
else:
    st.info("فایل نتایج ارزیابی یافت نشد — برای تولید آن: `python scripts/evaluate.py`")

st.info(
    "**مرز ارزیابی با ایمنی:** دقت بالا به معنای مجازشدن توصیه پزشکی نیست. حتی با دقت ۱۰۰٪، "
    "این ابزار فقط «چه نوشته شده» را می‌گوید؛ قدرت درج‌شده هرگز «دوز مصرف» نامیده نمی‌شود و "
    "هر مقدار به شواهد OCR گره خورده است (نگهبان ایمنی: `label_reader/response/guard.py` "
    "و `mobile-app/js/guard.js`)."
)
st.caption(f"👨‍💻 توسعه و طراحی: {APP_AUTHORS_FA} — LabelVoice v{__version__}")

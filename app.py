# -*- coding: utf-8 -*-
"""رابط کاربری Streamlit «برچسب‌خوان هوشمند دارو و محصولات».

کاملاً فارسی و راست‌به‌چپ، پس‌زمینه سفید، فونت خوانا و درشت.
اجرای محلی پردازش؛ ارسال به سرویس ابری فقط برای TTS با رضایت صریح کاربر.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st
from PIL import Image

from label_reader import APP_NAME_FA, SCOPE_FA, __version__
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

# ---------------- دریافت تصویر ----------------
source = st.radio("روش دریافت تصویر", ["بارگذاری فایل", "عکس با دوربین"],
                  horizontal=True)
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

    # پاسخ فارسی
    st.subheader("🗣️ پاسخ فارسی")
    st.markdown(f'<div class="big-answer">{result.response_fa}</div>',
                unsafe_allow_html=True)

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

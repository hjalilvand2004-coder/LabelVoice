# -*- coding: utf-8 -*-
"""رابط کاربری Streamlit «برچسب‌خوان هوشمند دارو و محصولات» — v1.8.0.

کاملاً فارسی و راست‌به‌چپ؛ ناوبری سایدبار چهاربخشی، مراحل رنگی زنده و
گرافیک مدرن. اجرای محلی پردازش؛ ارسال به سرویس ابری فقط برای TTS با رضایت
صریح کاربر.

👨‍💻 توسعه و طراحی: حمید جلیلوند و نوید بدری
"""
from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2
import streamlit as st
from PIL import Image

from label_reader import APP_AUTHORS_FA, APP_NAME_FA, SCOPE_FA, __version__
from label_reader.config import load_settings
from label_reader.help_content import HELP_CONTENT
from label_reader.models import FieldStatus
from label_reader.models_info import (
    VLM_MIN_TRANSFORMERS, models_table_rows, vlm_available,
)
from label_reader.pipeline import LabelReaderPipeline
from label_reader.response.tts_prep import prepare_for_tts
from label_reader.stages import (
    PROBLEM_STATEMENT_FA, STAGE_DEFS, STAGE_TTS_KEY,
    STATUS_FA as STAGE_STATUS_FA,
    build_stage_item, report_json as stage_report_json,
    summary_rows as stage_summary_rows, tts_payload,
)
from label_reader.tts import TtsError, make_tts_provider, synthesize_with_fallback
from label_reader.ui_helpers import (
    PRODUCT_TYPE_FA, STATUS_FA, draw_boxes_from_dicts, draw_ocr_boxes,
    editable_fields, fields_to_rows, inject_rtl, pil_to_bytes,
)
from label_reader.ui_theme import (
    DARK_THEME_CSS,
    STAGE_COLORS,
    STAGE_ICONS,
    THEME_CSS,
    stage_timeline_html,
)
from label_reader.bridge import DEFAULT_PORT, lan_ip, start_bridge_server
from label_reader.validation import ImageValidationError

st.set_page_config(page_title=APP_NAME_FA, page_icon="💊", layout="wide")
inject_rtl(st)
st.markdown(THEME_CSS, unsafe_allow_html=True)

settings = load_settings()
pipeline = LabelReaderPipeline(settings)

PAGES = {
    "read": ("💊", "خواندن دارو"),
    "reports": ("📊", "گزارش‌ها و ارزیابی"),
    "docs": ("📚", "راهنما و مستندات فنی"),
    "about": ("👥", "دربارهٔ طراحان"),
}

# v2.4.0: برچسب فارسی موتور خوانش فعال برای نشان هیرو
_ENGINE_LABELS_FA = {
    "tesseract": "Tesseract 5 (fas+eng) — پیش‌فرض",
    "easyocr": "EasyOCR — CRNN",
    "surya": "Surya OCR — ترنسفورمری",
    "qwen3-vl": "Qwen/Qwen3-VL-2B-Instruct — مدل زبانی-بینایی",
    "auto": "خودکار (اولین موتور در دسترس)",
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
    if st.button(label, key=f"help_{key}{suffix}", use_container_width=True):
        show_help(key)


def get_state(key, default=None):
    return st.session_state.get(key, default)


# ================= سایدبار: برند + ناوبری + تنظیمات =================
with st.sidebar:
    st.markdown(
        f"""
        <div class="lv-brand">
          <div class="logo">💊</div>
          <h1>{APP_NAME_FA}</h1>
          <p>برچسب را می‌خواند؛ فقط چه نوشته شده</p>
          <span class="lv-version">نسخه {__version__}</span>
        </div>
        """, unsafe_allow_html=True)

    page = st.radio(
        "ناوبری",
        list(PAGES.keys()),
        format_func=lambda k: f"{PAGES[k][0]}  {PAGES[k][1]}",
        label_visibility="collapsed",
        key="nav_page",
    )

    st.divider()
    st.subheader("⚙️ تنظیمات پردازش")
    _engine_opts = ["tesseract", "easyocr", "surya", "qwen3-vl", "auto"]
    engine_choice = st.radio(
        "موتور OCR — مدل خوانندهٔ متن را انتخاب کنید",
        _engine_opts,
        index=_engine_opts.index(settings.ocr_provider)
        if settings.ocr_provider in _engine_opts else 0,
        format_func=lambda v: {
            "tesseract": "Tesseract 5 (سبک و سریع — پیش‌فرض)",
            "easyocr": "EasyOCR — CRNN (عمیق — اختیاری)",
            "surya": "Surya OCR — ترنسفورمری (اختیاری)",
            "qwen3-vl": "Qwen3-VL-2B-Instruct — مدل زبانی-بینایی (اختیاری)",
            "auto": "خودکار (اولین موتور در دسترس)",
        }.get(v, v),
        help="هر موتور کل متن را می‌خواند و خروجی‌اش از همان گیت کیفیت و "
             "رأی اجماعی عبور می‌کند: tesseract سبک و سریع است؛ easyocr مدل "
             "عمیق CRNN با نصب سنگین‌تر؛ surya موتور ترنسفورمری چندزبانه؛ "
             "qwen3-vl مدل زبانی-بینایی Qwen/Qwen3-VL-2B-Instruct است که کل "
             "تصویر را یکجا می‌خواند (اولین اجرا وزن مدل را دانلود می‌کند). "
             "در نسخهٔ مرورگر/موبایل همیشه Tesseract.js روی WASM اجرا می‌شود.",
    )
    voice = st.selectbox("صدای فارسی (edge-tts)", ["fa-IR-FaridNeural", "fa-IR-DilaraNeural"])
    rate = st.select_slider("سرعت خوانش", ["-15%", "-5%", "+0%", "+10%", "+20%"], value="+0%")

    st.subheader("📣 اعلام مراحل")
    st.checkbox(
        "اعلام مرحله‌به‌مرحله رنگی (۵ مرحله)",
        value=True, key="staged_mode",
        help="در حین پردازش، تکمیل هر مرحله با رنگ اختصاصی همان مرحله اعلام و "
             "خروجی و معیارهای ارزیابی کیفیت آن نمایش داده می‌شود.")
    tech_help("stages", "🧩 مراحل رنگی چگونه کار می‌کنند؟", "st")

    # ---------------- v2.0.0: شفافیت مدل‌ها ----------------
    st.subheader("🧠 مدل‌ها و موتورها")
    tech_help("models", "🧠 کدام مدل برای کدام بخش؟", "md")
    with st.expander("📋 جدول مدل‌ها (نسخهٔ همین دستگاه)", expanded=False):
        try:
            st.dataframe(models_table_rows(), hide_index=True,
                         use_container_width=True)
        except Exception:  # noqa: BLE001
            st.markdown(HELP_CONTENT.get("models", "—"), unsafe_allow_html=False)
    _vlm_ok, _vlm_note = vlm_available()
    vlm_on = st.toggle(
        "🤖 دستیار خوانش Qwen3-VL (اختیاری)",
        value=bool(get_state("vlm_assist", False)), key="vlm_assist",
        help=("مدل Qwen/Qwen3-VL-2B-Instruct به‌صورت کاملاً محلی سطرهایی که OCR "
              "از دست داده را مکمل می‌خواند (شناسهٔ شاهد vlm-*). نیازمند "
              f"transformers>={VLM_MIN_TRANSFORMERS}. " + _vlm_note))
    try:
        pipeline.settings.vlm_assist = bool(vlm_on)
    except Exception:  # noqa: BLE001
        pass
    if vlm_on and not _vlm_ok:
        st.caption("⛔ " + _vlm_note)
    elif vlm_on and engine_choice == "qwen3-vl":
        st.caption("ℹ️ چون Qwen3-VL را به‌عنوان موتور اصلی خوانش انتخاب کرده‌اید، "
                   "دستیار مکمل اجرای دوباره نمی‌شود — کل تصویر یکجا با همین مدل خوانده شده است.")

    st.subheader("🛰️ پل OCR برای موبایل/وب (v2.5.0)")
    st.caption(
        "انتخاب موتور در رابط وب/موبایل واقعی است: Tesseract.js داخل مرورگر "
        "اجرا می‌شود؛ موتورهای سنگین (EasyOCR، Surya، Qwen3-VL) از طریق این "
        "پل روی همین رایانه خوانده می‌شوند. تصویر فقط بین دستگاه شما و همین "
        "رایانه در شبکهٔ محلی رد و بدل می‌شود؛ ذخیره‌سازی یا لاگ محتوایی وجود ندارد.")
    bridge_port_sb = st.number_input(
        "پورت پل", min_value=1024, max_value=65535,
        value=DEFAULT_PORT, step=1, key="bridge_port_input")
    bridge_on = st.toggle(
        "🚀 شروع پل OCR در این رایانه",
        value=bool(st.session_state.get("bridge_running", False)),
        key="bridge_toggle",
        help="سرور کوچک محلی (پیش‌فرض پورت 8770) بالا می‌آید تا نسخهٔ وب/موبایل "
             "بتواند با موتور انتخابیِ همین رایانه بخواند. برای توقف، همین "
             "کلید را خاموش کنید (سرور در نخ پس‌زمینه متوقف می‌شود).")
    if bridge_on:
        if "bridge_server" not in st.session_state or \
                st.session_state.get("bridge_port") != bridge_port_sb:
            try:
                if st.session_state.get("bridge_server") is not None:
                    try:
                        st.session_state["bridge_server"].shutdown()
                    except Exception:  # noqa: BLE001
                        pass
                st.session_state["bridge_server"] = start_bridge_server(
                    port=bridge_port_sb, host="0.0.0.0", settings=settings)
                st.session_state["bridge_server_thread"] = threading.Thread(
                    target=st.session_state["bridge_server"].serve_forever,
                    daemon=True)
                st.session_state["bridge_server_thread"].start()
                st.session_state["bridge_port"] = bridge_port_sb
            except OSError as exc:
                st.session_state["bridge_server"] = None
                st.error(f"راه‌اندازی پل ناموفق بود: {exc}")
        if st.session_state.get("bridge_server") is not None:
            st.session_state["bridge_running"] = True
            st.success(
                f"پل فعال است — از گوشی/مرورگر دیگر این آدرس را در انتخاب‌گر "
                f"«موتور OCR» وارد کنید:  \n"
                f"`http://{lan_ip()}:{bridge_port_sb}`  \n"
                f"روی همین رایانه: `http://127.0.0.1:{bridge_port_sb}/ping`")
    else:
        st.session_state["bridge_running"] = False
        _srv = st.session_state.get("bridge_server")
        if _srv is not None:
            try:
                _srv.shutdown()
            except Exception:  # noqa: BLE001
                pass
            st.session_state["bridge_server"] = None
            st.caption("پل متوقف شد.")

    st.subheader("🎨 نمایش")
    if st.toggle("🌙 حالت تاریک", key="dark_mode",
                 help="پالت تیرهٔ سرمه‌ای برای محیط کم‌نور؛ چیدمان و رنگ مراحل "
                      "بدون تغییر می‌ماند. موبایل/PWA به‌طور خودکار از تنظیم "
                      "سیستم پیروی می‌کند."):
        st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)

    st.divider()
    st.subheader("🔒 حریم خصوصی")
    st.markdown(
        "- پردازش تصویر و متن **کاملاً محلی** انجام می‌شود.\n"
        "- برای **تبدیل گفتار**، متن پاسخ به سرویس ابری ارسال می‌شود؛ فقط با "
        "رضایت صریح شما.\n"
        "- تصویر و متن برچسب در هیچ لاگی ذخیره نمی‌شود.\n"
        "- یادآوری: نام بیمار یا اطلاعات شخصی ممکن است روی بسته دیده شود."
    )
    st.caption(f"👨‍💻 {APP_AUTHORS_FA}")


# ================= صفحه ۱: خواندن دارو =================
if page == "read":
    st.markdown(
        f"""
        <div class="lv-hero">
          <h1>💊 خواندن دارو و محصولات</h1>
          <p>تصویر بسته را بارگذاری کنید یا با دوربین عکس بگیرید؛ سامانه متن
          قابل‌خواندن روی برچسب را با موتور دوموتوره استخراج، فیلدها را با رأی
          اجماعی تأیید و به فارسی نمایش و خوانش می‌کند.</p>
          <span class="authors">👨‍💻 توسعه و طراحی: {APP_AUTHORS_FA}</span>
        </div>
        <div class="lv-ribbon"></div>
        """, unsafe_allow_html=True)
    # v2.4.0: نشان «موتور و مدل خوانش فعال» — شفافیت انتخاب کاربر در بالای صفحه
    st.markdown(
        f"""
        <div class="lv-engine-badge">🧠 موتور و مدل خوانش فعال: <b>{_ENGINE_LABELS_FA.get(engine_choice, engine_choice)}</b>
        &nbsp;·&nbsp; تغییر از منوی «موتور OCR» سایدبار — مدل/زبان وب و موبایل هم از انتخاب‌گر همان صفحه انتخاب می‌شود</div>
        """, unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="lv-scope"><b>محدوده محصول:</b> {SCOPE_FA}
        این ابزار فقط می‌گوید «روی بسته چه نوشته شده است»؛ کاربرد دارو، مقدار مصرف
        یا توصیه پزشکی ارائه نمی‌دهد. اطلاعات غایب از اینترنت یا حافظه مدل تکمیل
        نمی‌شود.</div>
        """, unsafe_allow_html=True)

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

    # ---------------- پردازش با مراحل رنگی زنده ----------------
    if read_clicked and pil_image is not None:
        staged_mode = get_state("staged_mode", True)
        stage_records: list[dict] = []
        stage_images: dict[str, object] = {}
        current_stage: dict[str, str | None] = {"key": None}
        # v2.6.0: مسیر گام‌به‌گام OpenCV و خوانش خام OCR — هر پردازش از صفر
        st.session_state["opencv_trace"] = []
        st.session_state["ocr_readings"] = []

        timeline_slot = st.empty()
        status_slot = st.empty()

        def render_timeline():
            timeline_slot.markdown(
                stage_timeline_html(stage_records, current_stage["key"]),
                unsafe_allow_html=True)

        def on_stage(key: str, payload: dict) -> None:
            """اعلام زنده: در پایان هر مرحله فراخوانی می‌شود."""
            item = build_stage_item(key, payload)
            stage_records.append(item)
            img_bgr = payload.pop("image_bgr", None)
            if img_bgr is not None:
                stage_images[key] = Image.fromarray(
                    cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
            # v2.6.0: خروجی گام‌به‌گام OpenCV (تصویر هر عملیات) و خوانش
            # خام هر نسخهٔ پردازشی در session نگه‌داری می‌شود تا بخش
            # «دیدن کار OpenCV و خوانش خام OCR» پس از پردازش رندر شود.
            trace = payload.pop("opencv_trace", None)
            if trace:
                conv_trace = []
                for entry in trace:
                    t_img = entry.pop("image_bgr", None)
                    entry["image"] = (
                        Image.fromarray(cv2.cvtColor(t_img, cv2.COLOR_BGR2RGB))
                        if t_img is not None else None)
                    conv_trace.append(entry)
                st.session_state["opencv_trace"] = conv_trace
            readings = payload.pop("variant_readings", None)
            if readings is not None:
                st.session_state["ocr_readings"] = readings
            current_stage["key"] = None
            render_timeline()

        # نقشه رنگ‌ها برای اعلام شروع مرحله بعد
        stage_titles = {s["key"]: s["title_fa"] for s in STAGE_DEFS}
        order_keys = [s["key"] for s in STAGE_DEFS]

        if staged_mode:
            _legend = " · ".join(
                f'<span style="color:{STAGE_COLORS[k]};font-weight:700">'
                f'{STAGE_ICONS[k]} {stage_titles[k]}</span>'
                for k in order_keys)
            status_slot.markdown(
                f"""
                <div class="lv-scope" style="border-right-color:#43a047">
                🚀 <b>پردازش مرحله‌به‌مرحله (۵ مرحله) شروع شد.</b><br/>
                هر مرحله با رنگ اختصاصی خودش نمایش داده می‌شود: {_legend}<br/>
                📌 تعریف مسئله: {PROBLEM_STATEMENT_FA}
                </div>
                """, unsafe_allow_html=True)

        try:
            class StageAnnouncer:
                """اعلام زندهٔ مرحله در حال اجرا (v1.8.0).

                callback خط لوله در «پایان» هر مرحله فراخوانی می‌شود؛ بنابراین
                بلافاصله پس از پایان مرحله i، مرحله i+1 در حال اجراست و با
                رنگ اختصاصی و انیمیشن نبض نمایش داده می‌شود. پیش از اولین
                callback، مرحله ۱ در حال اجراست.
                """

                def __init__(self, order: list[str]):
                    self.order = order
                    self.seen: set[str] = set()
                    current_stage["key"] = order[0]
                    render_timeline()

                def __call__(self, key: str, payload: dict) -> None:
                    self.seen.add(key)
                    idx = self.order.index(key) if key in self.order else -1
                    current_stage["key"] = (
                        self.order[idx + 1] if 0 <= idx < len(self.order) - 1
                        else None)
                    on_stage(key, payload)

            t0 = time.perf_counter()
            result = pipeline.process_pil(
                pil_image, crop=crop_box, ocr_engine=engine_choice,
                stage_callback=StageAnnouncer(order_keys))

            current_stage["key"] = None

            # مرحله ۵ (TTS + نمایش): در لایه رابط کاربری اعلام می‌شود
            try:
                _prov = make_tts_provider(settings.tts_provider)
                _ok, _note = _prov.available()
                spoken = prepare_for_tts(result.response_fa)
                stage_records.append(build_stage_item(STAGE_TTS_KEY, tts_payload(
                    provider=(f"{getattr(_prov, 'name', settings.tts_provider)} — "
                              f"مدل صوت: {settings.tts_voice}"),
                    note_fa=_note or ("در دسترس است" if _ok else
                                      "در دسترس نیست؛ جایگزین به‌صورت خودکار آزمایش می‌شود"),
                    spoken_text=spoken, synthesized=False)))
            except Exception:  # noqa: BLE001
                stage_records.append(build_stage_item(STAGE_TTS_KEY, tts_payload(
                    provider=settings.tts_provider, note_fa="وضعیت نامشخص",
                    spoken_text=result.response_fa, synthesized=False)))
            render_timeline()
            status_slot.success(
                "✅ هر ۵ مرحله پردازش تکمیل شد — خروجی و ارزیابی هر مرحله در "
                "خط‌زمان بالا و بخش نتایج قابل مشاهده است.")

            st.session_state["result"] = result
            st.session_state["stage_records"] = stage_records
            st.session_state["stage_images"] = stage_images
            st.session_state.pop("audio_bytes", None)
            st.session_state.pop("tts_used", None)
            st.toast(f"پردازش در {result.metadata.durations_ms.get('total_ms', 0)} میلی‌ثانیه انجام شد.")
        except ImageValidationError as err:
            status_slot.error(f"⛔ {err.message_fa}")
        except Exception as err:  # noqa: BLE001
            status_slot.error(
                f"خطای پردازش: {err.__class__.__name__} — لطفاً تصویر دیگری امتحان کنید.")

    # ---------------- نمایش نتایج ----------------
    result = get_state("result")
    if result is not None:
        md = result.metadata

        for issue in result.quality_issues:
            if issue.code == "ok":
                st.caption("✅ " + issue.message_fa)
            elif issue.severity == "severe":
                st.error("⚠️ " + issue.message_fa)
            elif issue.severity == "warning":
                st.warning("⚠️ " + issue.message_fa)
        for w in md.warnings_fa:
            st.warning("ℹ️ " + w)

        # اعلام مراحل (expanderهای تفصیلی زیر خط‌زمان زنده)
        _stage_records = get_state("stage_records") or []
        _stage_images = get_state("stage_images") or {}
        if _stage_records:
            st.divider()
            st.subheader("🧭 جزئیات و ارزیابی هر مرحله")
            for item in _stage_records:
                color = STAGE_COLORS.get(item["key"], "#64748b")
                icon = STAGE_STATUS_FA.get(item["status"], "")
                dur = (f" · {item['duration_ms']} ms" if item.get("duration_ms")
                       is not None else "")
                with st.expander(
                        f"{STAGE_ICONS.get(item['key'], '')} مرحله {item['num_fa']} — "
                        f"{item['title_fa']}{dur}", expanded=False):
                    st.markdown(
                        f'<div style="border-right:4px solid {color};'
                        f'padding:6px 12px;background:#fff;border-radius:10px;">'
                        f"<b>الزام استاد:</b> {item['requirement_fa']}<br/>"
                        f"<b>پیام اعلام‌شده:</b> {item['done_message_fa']}</div>",
                        unsafe_allow_html=True)
                    st.caption(
                        f"🛠 فایل پیاده‌سازی — دسکتاپ: `{item['files_desktop_fa']}` · "
                        f"موبایل: `{item['files_mobile_fa']}`")
                    st.markdown("**خروجی این مرحله:**")
                    for out in item["outputs_fa"]:
                        st.write("- " + out)
                    if item["key"] == "opencv" and _stage_images.get("opencv") is not None:
                        st.image(_stage_images["opencv"],
                                 caption="خروجی مرحله ۱: تصویر بهبودیافته پس از "
                                         "پیش‌پردازش OpenCV",
                                 use_container_width=True)
                    st.markdown("**معیارهای ارزیابی کیفیت این مرحله:**")
                    for m in item["metrics"]:
                        icon2 = "✅" if m["status"] == "ok" else (
                            "⚠️" if m["status"] == "warn" else
                            "⛔" if m["status"] == "fail" else "⏳")
                        note = f" — {m['note_fa']}" if m["note_fa"] else ""
                        st.write(f"{icon2} **{m['name_fa']}:** {m['value']}{note}")
            st.dataframe(stage_summary_rows(_stage_records), hide_index=True,
                         use_container_width=True)
            st.download_button(
                "⬇️ دریافت گزارش ارزیابی مرحله‌ای (JSON)",
                data=stage_report_json(
                    _stage_records,
                    {"engine": md.engine, "languages": md.languages,
                     "durations_ms": md.durations_ms,
                     "deskew_applied": md.deskew_applied,
                     "variants_used": md.variants_used,
                     "timestamp_utc": md.timestamp_utc}),
                file_name="stage-evaluation-report.json",
                mime="application/json",
            )

            # v2.0.0 — شفافیت مدل: کدام مدل چه کاری انجام داد؟
            with st.expander("🧠 کدام مدل چه کاری انجام داد؟ (نسخهٔ همین دستگاه)",
                             expanded=False):
                st.dataframe(models_table_rows(), hide_index=True,
                             use_container_width=True)
                st.caption(
                    "این جدول در زمان اجرا از `label_reader/models_info.py` ساخته "
                    "می‌شود؛ هر فیلد استخراج‌شده به شناسهٔ شاهد (ocr_* از موتورهای "
                    "OCR یا vlm-* از دستیار بینایی) متصل است.")

        # v2.6.0 — بخش «دیدن کار OpenCV و خوانش خام OCR»: خروجی تصویری هر
        # عملیات پیش‌پردازش + متن/کادر خوانش هر نسخه، قبل از ادغام و رأی‌گیری
        _opencv_trace = get_state("opencv_trace") or []
        _ocr_readings = get_state("ocr_readings") or []
        if _opencv_trace or _ocr_readings:
            st.divider()
            st.subheader("🔬 دیدن کار OpenCV و خوانش خام OCR (گام‌به‌گام)")
            tech_help("trace", "🧩 چرا چند نسخه ساخته می‌شود و این بخش چیست؟", "tr")
            st.caption(
                "هر تغییری که OpenCV روی تصویر شما می‌دهد، گام‌به‌گام با توضیح "
                "عین عملیات (نام تابع cv2 و پارامترها) نمایش داده می‌شود؛ سپس "
                "خوانش خام هر نسخهٔ پردازشی را می‌بینید — یعنی OCR دقیقاً از کجای "
                "تصویر چه متنی خوانده، قبل از آنکه نتایج ادغام و رأی‌گیری شوند. "
                "این بخش فقط برای شفافیت است و تغییری در نتیجه ایجاد نمی‌کند.")

            if _opencv_trace:
                st.markdown("**۱) مسیر تصویر در پیش‌پردازش — خروجی هر عملیات:**")
                _tcols = st.columns(2)
                for _i, _entry in enumerate(_opencv_trace):
                    with _tcols[_i % 2]:
                        st.markdown(
                            f'<div style="font-weight:700;color:#0d47a1;'
                            f'font-size:1.02rem;">{_i + 1}. '
                            f'{_entry.get("title_fa", "")}</div>',
                            unsafe_allow_html=True)
                        st.caption(_entry.get("desc_fa", ""))
                        if _entry.get("image") is not None:
                            st.image(_entry["image"], use_container_width=True)
                        _m = _entry.get("metrics") or {}
                        st.caption(
                            f"📊 تیزی {_m.get('sharpness', '—')} · "
                            f"کنتراست {_m.get('contrast', '—')} · "
                            f"روشنایی {_m.get('brightness', '—')}")

            if _ocr_readings:
                st.markdown("**۲) خوانش خام هر نسخه — OCR دقیقاً چه خواند؟**")
                st.caption(
                    "به‌ازای هر نسخهٔ پردازشی، قطعه‌های نگه‌داشته‌شده پس از گیت "
                    "کیفیت (و شمار قطعه‌های ردشده) با کادر سبز روی همان تصویر "
                    "نشان داده می‌شود؛ این همان خوانشی است که بعداً با رأی "
                    "اجماعی ادغام می‌شود.")
                _variant_img = {
                    e.get("step"): e.get("image")
                    for e in _opencv_trace if e.get("image") is not None}
                for _r in _ocr_readings:
                    _name = _r.get("variant", "؟")
                    _engs = " + ".join(_r.get("engines") or []) or "—"
                    _pieces = _r.get("pieces") or []
                    _dropped = _r.get("dropped", 0)
                    with st.expander(
                            f"🔤 نسخهٔ «{_name}» — موتور {_engs} — "
                            f"{len(_pieces)} قطعه نگه‌داشته‌شده · "
                            f"{_dropped} قطعه ردشده"):
                        _vimg = _variant_img.get(_name)
                        if _vimg is not None and _pieces:
                            st.image(
                                draw_boxes_from_dicts(_vimg, _pieces),
                                caption=(f"کادر سبز = نواحی خوانده‌شده روی "
                                         f"نسخهٔ {_name}"),
                                use_container_width=True)
                        if _pieces:
                            _joined = " / ".join(p["text"] for p in _pieces)
                            st.markdown(
                                '<div class="lv-scope">📄 متن پیوستهٔ خوانش '
                                f'این نسخه: {_joined}</div>',
                                unsafe_allow_html=True)
                            st.dataframe(
                                [{"متن خام": p["text"],
                                  "اطمینان": ("—" if p.get("confidence") is None
                                              else f"{round(p['confidence'] * 100)}٪"),
                                  "موتور": p.get("engine") or "—",
                                  "مکان (x,y)": f"({p.get('x', 0)}, {p.get('y', 0)})",
                                  "اندازه (w×h)": f"{p.get('w', 0)}×{p.get('h', 0)}"}
                                 for p in _pieces],
                                hide_index=True, use_container_width=True)
                        else:
                            st.caption("این نسخه قطعهٔ قابل‌قبولی تولید نکرد "
                                       "(همه توسط گیت کیفیت رد شدند).")

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
                    st.caption("شناسه‌های `ocr_*` خوانش موتورهای OCR (Tesseract/EasyOCR) و "
                               "شناسه‌های `vlm-*` خوانش مکمل دستیار بینایی "
                               "(Qwen3-VL-2B-Instruct — در صورت فعال‌بودن) هستند.")
                else:
                    st.caption("متنی شناسایی نشد.")
            tech_help("preprocess", "🧩 فناوری پیش‌پردازش و OCR", "pp")

        with right_col:
            st.subheader("📋 فیلدهای ساختاریافته")
            st.dataframe(fields_to_rows(result.fields), use_container_width=True,
                         hide_index=True)
            st.caption(
                "وضعیت‌ها: استخراج‌شده / نامطمئن / غایب / متناقض / اصلاح کاربر — "
                "هر مقدار به شناسه قطعه OCR (شاهد) متصل است.")
            st.markdown(f"**نوع بسته تشخیص‌داده‌شده:** "
                        f"{PRODUCT_TYPE_FA.get(result.product_type.value, result.product_type.value)}")
            st.caption(result.product_type_note_fa)
            tech_help("fields", "🧩 فناوری استخراج فیلدها", "fd")

        # پاسخ فارسی
        st.subheader("🗣️ پاسخ فارسی")
        st.markdown(f'<div class="lv-big-answer">{result.response_fa}</div>',
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
        tech_help("tts", "🧩 فناوری تبدیل متن به گفتار", "tt")
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
                        _recs = st.session_state.get("stage_records") or []
                        for _i, _r in enumerate(_recs):
                            if _r.get("key") == STAGE_TTS_KEY:
                                _recs[_i] = build_stage_item(STAGE_TTS_KEY, tts_payload(
                                    provider=used,
                                    note_fa="صوت با موفقیت تولید شد",
                                    spoken_text=spoken_text, synthesized=True))
                        st.session_state["stage_records"] = _recs
                    except TtsError as err:
                        st.error("🔇 " + err.message_fa)
        with col_info:
            st.caption(tts_note)
            st.caption("متن پخش‌شده دقیقاً همان پاسخ تأییدشده رابط است. فایل صوتی "
                       "فقط با دانلود صریح ذخیره می‌شود.")

        audio_bytes = get_state("audio_bytes")
        if audio_bytes:
            st.audio(audio_bytes, format="audio/mp3")
            st.download_button(
                "⬇️ دانلود فایل صوتی (mp3)",
                data=audio_bytes,
                file_name="label-response.mp3",
                mime="audio/mp3",
            )

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
        "پزشکی. اطلاعات ناخوانا یا متناقض به‌صورت شفاف اعلام می‌شوند.")
    st.caption(
        "📚 مستندات فنی کامل: "
        "[نسخه HTML](https://hjalilvand2004-coder.github.io/LabelVoice/documentation.html) — "
        "[نسخه PDF](https://github.com/hjalilvand2004-coder/LabelVoice/releases/latest)")


# ================= صفحه ۲: گزارش‌ها و ارزیابی =================
elif page == "reports":
    st.markdown(
        """
        <div class="lv-hero" style="background:linear-gradient(135deg,#0d47a1 0%,#1565c0 55%,#1e88e5 120%)">
          <h1>📊 گزارش‌ها، تحلیل‌ها و ارزیابی</h1>
          <p>دقت سامانه در سطح فیلد روی مجموعه نمونه برچسب‌خورده سنجیده می‌شود؛
          غیبت و تعارض هم خطا شمرده می‌شود چون هر اشتباه دارویی می‌تواند آسیب‌زا باشد.</p>
        </div>
        <div class="lv-ribbon"></div>
        """, unsafe_allow_html=True)

    tech_help("eval", "🧩 روش و اصول ارزیابی مدل‌ها", "ev")

    _eval_path = Path(__file__).resolve().parent / "docs" / "evaluation" / "evaluation-results.json"
    if _eval_path.exists():
        import pandas as pd

        _ev = json.loads(_eval_path.read_text(encoding="utf-8"))
        _tess = _ev["pipeline"]["tesseract_full"]["summary"]
        _pt = _ev["unit_tests"]["python_pytest"]
        _nd = _ev["unit_tests"]["javascript_node"]

        _m1, _m2, _m3, _m4 = st.columns(4)
        for tile, val, sub in (
                (_m1, f"{_tess['field_accuracy']}%", "دقت فیلد (Tesseract)"),
                (_m2, f"{_tess['latency_ms']['mean']:,} ms", "میانگین زمان پردازش"),
                (_m3, f"{_pt['passed']} ✓", "آزمون‌های پایتون (pytest)"),
                (_m4, f"{_nd['passed']} ✓", "آزمون‌های موبایل (Node)")):
            tile.markdown(
                f'<div class="lv-metric-tile"><div class="v">{val}</div>'
                f'<div class="k">{sub}</div></div>', unsafe_allow_html=True)

        FIELD_FA = {"name": "نام محصول", "strength": "قدرت درج‌شده",
                    "count": "تعداد/شکل", "expiry_date": "تاریخ انقضا",
                    "net_weight": "وزن/حجم", "manufacturer": "سازنده",
                    "batch": "شماره سری"}
        _pf = _tess["per_field"]
        st.markdown("#### 🎯 دقت به تفکیک فیلد (٪)")
        st.bar_chart(pd.DataFrame(
            {"دقت (٪)": {FIELD_FA.get(k, k): v["acc"] for k, v in _pf.items()}}),
            color="#43a047")

        CASE_FA = {"clear_english": "انگلیسی ساده", "clear_persian": "فارسی ساده",
                   "mixed_fa_en": "دوزبانه", "ambiguous_date": "تاریخ مبهم",
                   "combo_strength": "قدرت ترکیبی", "mcg_vs_mg": "تفکیک mcg/mg",
                   "malicious_text": "متن مخرب", "non_medicine": "غیردارویی"}
        _pc = _tess["per_case"]
        st.markdown("#### 🖼️ دقت به تفکیک حالت تصویر (٪)")
        st.bar_chart(pd.DataFrame(
            {"دقت (٪)": {CASE_FA.get(k, k): v["acc"] for k, v in _pc.items()}}),
            color="#1e88e5")

        _lat = _tess["latency_ms"]
        st.markdown("#### ⏱️ زمان پردازش هر تصویر (میلی‌ثانیه)")
        st.bar_chart(pd.DataFrame(
            {"ms": {"کمینه": _lat["min"], "میانه": _lat["median"],
                    "میانگین": _lat["mean"], "p95": _lat["p95"],
                    "بیشینه": _lat["max"]}}), color="#ef6c00")

        MOD_FA = {"tests/test_patterns_fields.py": "الگوها و فیلدها",
                  "tests/test_pipeline_integration.py": "یکپارچگی خط پردازش",
                  "tests/test_quality_validation.py": "کیفیت و اعتبارسنجی",
                  "tests/test_response_builder.py": "پاسخ‌ساز و نگهبان",
                  "tests/test_security.py": "امنیت",
                  "tests/test_textnorm.py": "نرمال‌سازی متن",
                  "tests/test_tts_llm.py": "TTS و LLM"}
        st.markdown("#### 🧪 آزمون‌های واحد پایتون به تفکیک ماژول")
        st.bar_chart(pd.DataFrame(
            {"تعداد آزمون": {MOD_FA.get(k, k): v["total"]
                             for k, v in _pt["per_file"].items()}}),
            color="#00acc1")

        st.info(
            "**یافته صادقانه (v1.8.0):** در نسخه ۱.۸٫۰ موتور فارسی بازطراحی شد — "
            "گذر زبانی جدا + رأی اجماعی + موتور دوم. روی نمونه واقعی «جعبه لانزول ۳۰»، "
            "ماده مؤثره (لانسوپرازول)، قدرت (۳۰ میلی‌گرم)، تعداد (۲۸ کپسول) و شکل "
            "دارویی (کپسول) به‌درستی خوانده شد؛ نام خوش‌نویسیِ برند به‌صورت صادقانه "
            "«خوانده نشد» اعلام گردید. عدد جعلی جایگزین نمی‌شود."
        )
    else:
        st.info("فایل نتایج ارزیابی یافت نشد — برای تولید آن: `python scripts/evaluate.py`")

    st.divider()
    st.subheader("🔬 ارزیابی درون‌سامانه — آخرین پردازش شما")
    _result = get_state("result")
    _recs = get_state("stage_records") or []
    if _result is not None and _recs:
        md = _result.metadata
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("زمان کل پردازش",
                  f"{md.durations_ms.get('total_ms', 0):,} ms")
        confs = [p.confidence for p in _result.ocr_pieces
                 if p.confidence is not None]
        c2.metric("میانگین اطمینان OCR",
                  f"{round(100 * sum(confs) / len(confs))}%" if confs else "—")
        extracted = sum(1 for f in _result.fields.values()
                        if f.status.value in ("extracted", "user_corrected"))
        c3.metric("فیلدهای استخراج‌شده", str(extracted))
        c4.metric("موتورها", md.engine)
        st.dataframe(stage_summary_rows(_recs), hide_index=True,
                     use_container_width=True)
        st.caption("این معیارها از پردازش واقعی آخرین تصویر شما تولید شده‌اند؛ "
                   "برای ارزیابی تکرارپذیر روی مجموعه نمونه، `scripts/evaluate.py` را ببینید.")
    else:
        st.info("هنوز پردازشی در این نشست انجام نشده — از صفحه «خواندن دارو» شروع کنید.")

    st.info(
        "**مرز ارزیابی با ایمنی:** دقت بالا به معنای مجازشدن توصیه پزشکی نیست. حتی با دقت ۱۰۰٪، "
        "این ابزار فقط «چه نوشته شده» را می‌گوید؛ قدرت درج‌شده هرگز «دوز مصرف» نامیده نمی‌شود و "
        "هر مقدار به شواهد OCR گره خورده است.")


# ================= صفحه ۳: راهنما و مستندات =================
elif page == "docs":
    st.markdown(
        """
        <div class="lv-hero" style="background:linear-gradient(135deg,#1b5e20 0%,#2e7d32 50%,#43a047 120%)">
          <h1>📚 راهنما و مستندات فنی</h1>
          <p>معماری سامانه، ملزومات استاد، فناوری هر بخش و مستندات کامل HTML/PDF.</p>
        </div>
        <div class="lv-ribbon"></div>
        """, unsafe_allow_html=True)

    with st.expander("🏗️ معماری سامانه در یک نگاه", expanded=True):
        st.markdown(HELP_CONTENT["architecture"])

    with st.expander("📌 ملزومات طرح‌شده توسط استاد (استاد قربانی) — جدول انطباق"):
        st.markdown(HELP_CONTENT["reqs"])

    with st.expander("🧭 اعلام مرحله‌به‌مرحله پردازش (۵ مرحله رنگی)"):
        st.markdown(HELP_CONTENT["stages"])

    for _key, _title in (
            ("input", "📥 ورود تصویر و اعتبارسنجی"),
            ("preprocess", "🖼️ پیش‌پردازش OpenCV"),
            ("engine", "🔤 موتورهای OCR (v1.8.0)"),
            ("fields", "📋 استخراج فیلدها و مدل داده"),
            ("response", "💬 پاسخ فارسی و نگهبان ایمنی"),
            ("tts", "🔊 تبدیل متن به گفتار"),
            ("json", "🧾 ساختار خروجی JSON"),
            ("eval", "📊 روش ارزیابی مدل‌ها")):
        with st.expander(_title):
            st.markdown(HELP_CONTENT[_key])

    st.divider()
    st.subheader("📄 مستندات کامل")
    st.markdown(
        "- **نسخه HTML تعاملی:** [documentation.html روی GitHub Pages]"
        "(https://hjalilvand2004-coder.github.io/LabelVoice/documentation.html) — "
        "رسپانسیو و مصور؛ نسخه موبایل هم در `mobile-app/documentation.html`.\n"
        "- **نسخه PDF:** پیوست [Releases مخزن GitHub]"
        "(https://github.com/hjalilvand2004-coder/LabelVoice/releases/latest).\n"
        "- **راهنمای نصب:** `docs/INSTALL.md` · **محدودیت‌ها:** `docs/LIMITATIONS.md`.")
    tech_help("docs", "🧩 دربارهٔ مستندات", "dc")


# ================= صفحه ۴: دربارهٔ طراحان =================
else:
    st.markdown(
        """
        <div class="lv-hero" style="background:linear-gradient(135deg,#0d47a1 0%,#1e88e5 60%,#43a047 140%)">
          <h1>👥 دربارهٔ طراحان</h1>
          <p>پروژهٔ LabelVoice — برچسب‌خوان هوشمند دارو و محصولات؛ طراحی و توسعهٔ
          دو-نفره با تمرکز بر ایمنی، شفافیت و وفاداری به شواهد.</p>
        </div>
        <div class="lv-ribbon"></div>
        """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            """
            <div class="lv-author">
              <div class="avatar">👨‍💻</div>
              <h3>حمید جلیلوند</h3>
              <div class="role">توسعه‌دهنده و طراح</div>
              <p style="font-size:13px;color:#475569">طراحی و پیاده‌سازی خط پردازش
              OCR دوموتوره، استراتژی خوانش فارسی و موتور اجماعی، و رابط کاربری.</p>
            </div>
            """, unsafe_allow_html=True)
    with c2:
        st.markdown(
            """
            <div class="lv-author">
              <div class="avatar">👨‍💻</div>
              <h3>نوید بدری</h3>
              <div class="role">توسعه‌دهنده و طراح</div>
              <p style="font-size:13px;color:#475569">طراحی و پیاده‌سازی نسخه موبایل
              (PWA)، دوربین زنده، تشخیص جعبه و آزمون‌های پاریتی دو-سامانه.</p>
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    st.subheader("💡 داستان پروژه")
    st.markdown(
        """
این پروژه با یک پرسش ساده شروع شد: «اگر نتوانید روی جعبه دارو را بخوانید چه؟»
کاربر ممکن است کم‌بینا باشد، دستش بلرزد، یا برچسب خراب باشد. LabelVoice متنِ
«واقعاً قابل خواندن» روی بسته را استخراج می‌کند و دقیقاً همان را به فارسی
نمایش می‌دهد و می‌خواند — نه یک کلمه بیشتر.

خط قرمز پروژه شفافیت است: مقداری که خوانده نشد «غایب» اعلام می‌شود؛ مقداری که
بین دو خوانش مردد است «متناقض» اعلام می‌شود؛ و هیچ عددی از حافظه مدل یا اینترنت
تکمیل نمی‌شود. قدرت درج‌شده روی بسته هرگز «دوز مصرف» نامیده نمی‌شود؛ سامانه
تشخیص دارو، تجویزکننده یا مشاور پزشکی نیست.
        """)
    st.subheader("🧰 فناوری‌ها")
    st.markdown(
        "- **دسکتاپ:** Python · Streamlit · OpenCV · Tesseract 5 (fas/eng گذر جدا) · "
        "EasyOCR (موتور دوم) · Pydantic v2 · edge-tts / gTTS\n"
        "- **موبایل:** PWA · Tesseract.js 6 (WASM) · Web Speech API · Vazirmatn\n"
        "- **کیفیت:** pytest (۱۰۶ آزمون) · Node test runner (۵۴ آزمون پاریتی) · "
        "۱۴ نمونه زمینه‌سنجی‌شده")
    st.caption(f"LabelVoice v{__version__} — 👨‍💻 توسعه و طراحی: {APP_AUTHORS_FA}")

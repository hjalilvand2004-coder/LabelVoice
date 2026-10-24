# -*- coding: utf-8 -*-
"""رجیستری مرکزی مدل‌ها و موتورها (v2.0.0) — تک‌منبع حقیقت شفافیت.

کاربر باید همیشه بداند «برای هر بخش از چه مدلی استفاده می‌شود». این ماژول:
- فهرست رسمی همهٔ مدل‌ها/موتورهای خط پردازش را نگه می‌دارد (دسکتاپ + وب)؛
- نسخهٔ واقعی نصب‌شده روی همین دستگاه را در زمان اجرا تشخیص می‌دهد؛
- سطرهای جدول نمایش (st.dataframe) و متن راهنما را می‌سازد؛
- عین همین داده‌ها در مستندات (README، documentation.html، راهنمای درون‌اپی) می‌آید.

هیچ نسخه‌ای اینجا «حدس زده» نمی‌شود؛ هر مقدار یا در زمان اجرا خوانده می‌شود
یا صریحاً «نصب نشده / نامشخص» اعلام می‌گردد.
"""
from __future__ import annotations

import importlib.metadata as _ilmd

# شناسهٔ رسمی دستیار بینایی اختیاری — عین نام مخزن Hugging Face
VLM_MODEL_ID = "Qwen/Qwen3-VL-2B-Instruct"
VLM_MIN_TRANSFORMERS = "4.57"

# نسخه‌های پین‌شدهٔ وب (عین mobile-app/js/ocr.js)
TESSERACT_JS_VERSION = "6.0.1"
TESSERACT_CORE_VERSION = "6.1.2"


def _pkg_version(name: str) -> str | None:
    try:
        return _ilmd.version(name)
    except Exception:  # noqa: BLE001
        return None


def detect_versions() -> dict[str, str]:
    """تشخیص زندهٔ نسخهٔ موتورها روی همین دستگاه — هرگز نمی‌شکند."""
    out: dict[str, str] = {}

    try:
        import cv2
        out["opencv"] = cv2.__version__
    except Exception:  # noqa: BLE001
        out["opencv"] = "نامشخص"

    try:
        import pytesseract
        out["tesseract"] = str(pytesseract.get_tesseract_version())
    except Exception:  # noqa: BLE001
        out["tesseract"] = "نصب نشده"

    try:
        import easyocr  # lazy
        out["easyocr"] = str(getattr(easyocr, "__version__", "نصب شده"))
    except Exception:  # noqa: BLE001
        out["easyocr"] = "نصب نشده (اختیاری)"

    try:  # v2.2.0: موتور سوم اختیاری Surya
        out["surya"] = _pkg_version("surya-ocr") or "نصب نشده (اختیاری)"
    except Exception:  # noqa: BLE001
        out["surya"] = "نصب نشده (اختیاری)"

    out["edge_tts"] = _pkg_version("edge-tts") or "نصب نشده"
    out["gtts"] = _pkg_version("gtts") or "نصب نشده"
    out["streamlit"] = _pkg_version("streamlit") or "نامشخص"
    out["pytesseract"] = _pkg_version("pytesseract") or "نامشخص"
    out["transformers"] = _pkg_version("transformers") or "نصب نشده"

    try:
        import torch
        out["torch"] = torch.__version__
    except Exception:  # noqa: BLE001
        out["torch"] = "نصب نشده"
    return out


def vlm_available() -> tuple[bool, str]:
    """(در دسترس بودن دستیار Qwen3-VL، توضیح فارسی)."""
    ver = detect_versions()
    if ver["transformers"] == "نصب نشده":
        return False, (f"برای فعال‌سازی: pip install \"transformers>={VLM_MIN_TRANSFORMERS}\" "
                       "accelerate — مدل در اولین اجرا از Hugging Face دانلود می‌شود.")
    try:
        import transformers  # noqa: F401
        from transformers import Qwen3VLForConditionalGeneration  # noqa: F401
        return True, "در دسترس است (اجرای کاملاً محلی)"
    except Exception:  # noqa: BLE001
        return False, (f"نسخهٔ transformers نصب‌شده ({ver['transformers']}) کلاس "
                       f"Qwen3VL ندارد؛ به نسخه >={VLM_MIN_TRANSFORMERS} نیاز است.")


# ---------------------------------------------------------------------------
# رجیستری رسمی — هر ردیف: یک مدل/موتور برای یک نقش مشخص
#   runtime: کلید detect_versions برای ستون «نسخه روی همین دستگاه»
#   optional: نصب/فعال‌سازی اختیاری است
# ---------------------------------------------------------------------------
MODEL_REGISTRY: list[dict] = [
    {
        "stage_fa": "۱. پیش‌پردازش تصویر",
        "model": "OpenCV (بینایی ماشین کلاسیک — بدون مدل یادگیری)",
        "runtime": "opencv",
        "role_fa": "بهبود وضوح (CLAHE)، صاف‌کردن زاویه، ساخت نسخه‌های "
                   "original/gray_clahe/binarized/white_on_dark/ink_isolated",
        "where": "label_reader/preprocess.py ⇄ mobile-app/js/preprocess.js",
        "privacy_fa": "کاملاً آفلاین",
        "optional": False,
    },
    {
        "stage_fa": "۲. خواندن متن (OCR — موتور اول)",
        "model": "Tesseract 5 — موتور متن‌باز گوگل (دادهٔ زبان fas+eng)",
        "runtime": "tesseract",
        "role_fa": "خوانش چندگذری با PSMهای 3/6/11 و گذرهای زبانی جداگانهٔ فارسی/انگلیسی",
        "where": "label_reader/ocr/tesseract_provider.py",
        "privacy_fa": "کاملاً آفلاین",
        "optional": False,
    },
    {
        "stage_fa": "۲. خواندن متن (OCR — موتور دوم مکمل)",
        "model": "EasyOCR — شبکهٔ عمیق CRNN (زبان fa+en)",
        "runtime": "easyocr",
        "role_fa": "پر کردن نواحی‌ای که تسراکت ضعیف خوانده؛ خروجی با همان گیت کیفیت و رأی اجماعی ادغام می‌شود",
        "where": "label_reader/ocr/easyocr_provider.py",
        "privacy_fa": "کاملاً آفلاین (پس از دانلود اولیهٔ وزن‌ها)",
        "optional": True,
    },
    {
        "stage_fa": "۲. خواندن متن (OCR — موتور سوم به انتخاب کاربر)",
        "model": "Surya — موتور OCR متن‌باز (تشخیص خط + بازشناسی ترنسفورمری؛ چندزبانه شامل فارسی)",
        "runtime": "surya",
        "role_fa": "گزینهٔ سوم خوانش به انتخاب صریح کاربر؛ خروجی با همان گیت کیفیت و رأی اجماعی ادغام می‌شود (فقط دسکتاپ)",
        "where": "label_reader/ocr/surya_provider.py",
        "privacy_fa": "کاملاً آفلاین (پس از دانلود اولیهٔ وزن‌ها از Hugging Face)",
        "optional": True,
    },
    {
        "stage_fa": "۲. خواندن متن (OCR — موتور چهارم به انتخاب کاربر)",
        "model": f"مدل زبانی-بینایی {VLM_MODEL_ID}",
        "runtime": "qwen3-vl",
        "role_fa": "گزینهٔ چهارم خوانش به انتخاب صریح کاربر (v2.3.0)؛ کل تصویر را یکجا سطر به سطر می‌خواند؛ خروجی با همان گیت کیفیت و رأی اجماعی ادغام می‌شود (فقط دسکتاپ)",
        "where": "label_reader/ocr/vlm_provider.py",
        "privacy_fa": "اجرای کاملاً محلی (پس از دانلود اولیهٔ وزن از Hugging Face)",
        "optional": True,
    },
    {
        "stage_fa": "۲. دستیار خوانش دوم (اختیاری)",
        "model": f"مدل زبانی-بینایی {VLM_MODEL_ID}",
        "runtime": "vlm",
        "role_fa": "خوانش مکمل سطرهایی که OCR از دست داده؛ فقط سطرهای تازه (بدون تکرار) با شناسهٔ شاهد vlm-* اضافه می‌شود؛ وقتی همین مدل موتور اصلی است دوباره اجرا نمی‌شود",
        "where": "label_reader/ocr/vlm_provider.py",
        "privacy_fa": "اجرای کاملاً محلی؛ پیش‌فرض خاموش",
        "optional": True,
    },
    {
        "stage_fa": "۳. پردازش متن و کنترل فیلدها",
        "model": "قواعد و الگوهای فارسی/انگلیسی (Regex + نرمال‌سازی) — بدون مدل زبانی",
        "runtime": None,
        "role_fa": "نرمال‌سازی نام، استخراج قدرت/تعداد/انقضا/سری، تشخیص تناقض، گیت کیفیت قطعه‌ها و رأی اجماعی",
        "where": "label_reader/textnorm.py + extraction/* + quality.py",
        "privacy_fa": "کاملاً آفلاین",
        "optional": False,
    },
    {
        "stage_fa": "۴. تولید پاسخ فارسی",
        "model": "قالب‌ساز قاعده‌محور + نگهبان ایمنی (بدون مدل ابری)",
        "runtime": None,
        "role_fa": "ساخت پاسخ فارسی فقط از فیلدهای تأییدشده؛ (اختیاری) بازنویسی با هر LLM سازگار با OpenAI API از طریق تنظیمات LBR_LLM_* و عبور اجباری از نگهبان",
        "where": "label_reader/response/builder.py + guard.py (+ llm/rewriter.py اختیاری)",
        "privacy_fa": "آفلاین؛ مسیر اختیاری LLM فقط با تنظیم صریح کاربر",
        "optional": False,
    },
    {
        "stage_fa": "۵. خوانش صوتی (TTS)",
        "model": "edge-tts — صداهای فارسی fa-IR-FaridNeural / fa-IR-DilaraNeural (مایکروسافت)",
        "runtime": "edge_tts",
        "role_fa": "خواندن همان پاسخ تأییدشده؛ جایگزین خودکار: gTTS (گوگل)",
        "where": "label_reader/tts/edge_provider.py + gtts_provider.py",
        "privacy_fa": "فقط متن پاسخ، با رضایت صریح کاربر ارسال می‌شود",
        "optional": False,
    },
    {
        "stage_fa": "وب / PWA / تک‌فایل",
        "model": f"Tesseract.js {TESSERACT_JS_VERSION} (WebAssembly) + Web Speech API",
        "runtime": None,
        "role_fa": "همان خط پردازش داخل مرورگر: OCR با دادهٔ fas+eng تعبیه‌شده، پاسخ قاعده‌محور، خوانش صوتی روی خود دستگاه",
        "where": "mobile-app/js/ocr.js + pipeline.js + responder.js",
        "privacy_fa": "کاملاً آفلاین (تک‌فایل) / پس از بار اول (PWA)",
        "optional": False,
    },
    {
        "stage_fa": "رابط کاربری دسکتاپ",
        "model": "Streamlit + فونت وزیرمتن (Vazirmatn)",
        "runtime": "streamlit",
        "role_fa": "رابط فارسی راست‌به‌چپ، خط‌زمان مراحل رنگی، حالت تاریک",
        "where": "app.py + label_reader/ui_theme.py",
        "privacy_fa": "کاملاً محلی",
        "optional": False,
    },
]


def models_table_rows() -> list[dict]:
    """سطرهای جدول «مدل‌ها و موتورها» برای نمایش در رابط کاربری."""
    ver = detect_versions()
    rows = []
    for m in MODEL_REGISTRY:
        if m["runtime"] is None:
            version = "— (قاعده‌محور، بدون مدل)"
        elif m["runtime"] in ("vlm", "qwen3-vl"):
            ok, note = vlm_available()
            version = ("نصب و آماده ✅" if ok else
                       f"نصب نشده (اختیاری) — {note}")
        else:
            version = ver.get(m["runtime"], "نامشخص")
        if m["runtime"] in ("easyocr", "surya", "qwen3-vl") and version.startswith("نصب نشده"):
            version = "اختیاری — " + version
        rows.append({
            "مرحله": m["stage_fa"],
            "مدل / موتور": m["model"],
            "نقش در سامانه": m["role_fa"],
            "نسخه روی این دستگاه": version,
            "محل پیاده‌سازی": m["where"],
            "حریم خصوصی": m["privacy_fa"],
        })
    return rows


def models_markdown_fa() -> str:
    """نسخهٔ Markdown رجیستری برای راهنماهای متنی (HELP_CONTENT و README)."""
    ver = detect_versions()
    lines = [
        "| مرحله | مدل / موتور | نقش | نسخه روی این دستگاه |",
        "|---|---|---|---|",
    ]
    for m in MODEL_REGISTRY:
        if m["runtime"] is None:
            version = "قاعده‌محور (بدون مدل)"
        elif m["runtime"] in ("vlm", "qwen3-vl"):
            ok, _ = vlm_available()
            version = "نصب و آماده" if ok else "اختیاری — نصب نشده"
        else:
            version = ver.get(m["runtime"], "نامشخص")
        if m["runtime"] in ("easyocr", "surya", "qwen3-vl") and version.startswith("نصب نشده"):
            version = "اختیاری — نصب نشده"
        lines.append(f"| {m['stage_fa']} | {m['model']} | {m['role_fa']} | {version} |")
    return "\n".join(lines)

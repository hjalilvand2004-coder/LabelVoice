# -*- coding: utf-8 -*-
"""اعلام مرحله‌به‌مرحله پردازش و ارزیابی کیفیت هر مرحله (v1.6.0).

مطابق ملزومات استاد قربانی، خط پردازش پنج‌مرحله‌ای است:
    OpenCV ← OCR ← پردازش متن و کنترل فیلدها ← تولید پاسخ فارسی ← TTS + Streamlit

این ماژول برای هر مرحله:
- عین متن الزام استاد را نگه می‌دارد (ردیابی‌پذیری)؛
- پیام «شروع» و پیام «انجام شد — این بخش از نیازمندی استاد برآورده شد» می‌سازد؛
- خروجی مرحله و معیارهای ارزیابی کیفیت همان مرحله را قالب‌بندی می‌کند؛
- گزارش نهایی JSON-سازگار (بدون تصویر) برای دانلود تولید می‌کند.

مرحله‌های ۱ تا ۴ داخل `pipeline.process_pil` با callback اعلام می‌شوند؛
مرحله ۵ (TTS + نمایش) در لایه رابط کاربری (app.py) تکمیل می‌شود.
"""
from __future__ import annotations

import cv2
import numpy as np

STAGE_TTS_KEY = "tts"

STATUS_FA = {"done": "✅ انجام شد", "warn": "⚠️ انجام شد (با هشدار)",
             "fail": "⛔ ناموفق", "pending": "⏳ در انتظار اقدام کاربر"}

# ---------------------------------------------------------------------------
# تعریف پنج مرحله — عین متن ملزومات استاد (دسته ۲: نمودار معماری)
# ---------------------------------------------------------------------------
STAGE_DEFS: list[dict] = [
    {
        "key": "opencv",
        "num_fa": "۱",
        "title_fa": "پیش‌پردازش OpenCV",
        "requirement_fa": "OpenCV (تشخیص ناحیه برچسب، اصلاح زاویه و بهبود وضوح)",
        "files_desktop_fa": "label_reader/preprocess.py + quality.py + validation.py",
        "files_mobile_fa": "mobile-app/js/boxdetect.js + preprocess.js",
    },
    {
        "key": "ocr",
        "num_fa": "۲",
        "title_fa": "موتور OCR",
        "requirement_fa": "OCR (استخراج نام، اعداد و متن بسته‌بندی)",
        "files_desktop_fa": "label_reader/ocr/tesseract_provider.py + easyocr_provider.py",
        "files_mobile_fa": "mobile-app/js/ocr.js (Tesseract.js/WASM)",
    },
    {
        "key": "fields",
        "num_fa": "۳",
        "title_fa": "پردازش متن و کنترل فیلدها",
        "requirement_fa": (
            "پردازش متن و کنترل فیلدها (نرمال‌سازی نام، استخراج قدرت و تعداد درج‌شده)"),
        "files_desktop_fa": (
            "label_reader/textnorm.py + extraction/patterns.py + extraction/fields.py"),
        "files_mobile_fa": "mobile-app/js/textnorm.js + patterns.js + extractor.js",
    },
    {
        "key": "response",
        "num_fa": "۴",
        "title_fa": "تولید پاسخ فارسی",
        "requirement_fa": (
            "تولید پاسخ فارسی (منطق استخراج اطلاعات یا LLM برای بازنویسی وفادار به متن)"),
        "files_desktop_fa": (
            "label_reader/response/builder.py + response/guard.py (+ llm/rewriter.py اختیاری)"),
        "files_mobile_fa": "mobile-app/js/responder.js + guard.js",
    },
    {
        "key": STAGE_TTS_KEY,
        "num_fa": "۵",
        "title_fa": "خوانش صوتی و نمایش (TTS + رابط کاربری)",
        "requirement_fa": "TTS + Streamlit (خواندن اطلاعات و نمایش متن استخراج‌شده)",
        "files_desktop_fa": "label_reader/tts/* + response/tts_prep.py + app.py (Streamlit)",
        "files_mobile_fa": "mobile-app/js/app.js (speechSynthesis) + index.html",
    },
]

STAGE_BY_KEY: dict[str, dict] = {s["key"]: s for s in STAGE_DEFS}

# تعریف مسئله (دسته ۱ ملزومات استاد) — در پیام شروع هر پردازش اعلام می‌شود
PROBLEM_STATEMENT_FA = (
    "کاربر دوربین را به سمت جعبه دارو یا بسته‌بندی یک محصول می‌گیرد. سامانه نام، "
    "اطلاعات چاپ‌شده و سایر فیلدهای قابل خواندن را استخراج می‌کند و آن‌ها را به "
    "زبان فارسی می‌خواند. سامانه اطلاعات خوانده‌شده را از توصیه‌های پزشکی جدا نگه می‌دارد."
)


def start_message(num_fa: str, title_fa: str) -> str:
    return f"⏳ مرحله {num_fa} از ۵ در حال اجرا: {title_fa}…"


def done_message(num_fa: str, title_fa: str, status: str = "done") -> str:
    if status == "fail":
        return (f"⛔ مرحله {num_fa} از ۵ ({title_fa}) نتیجه مطلوب نداد؛ "
                f"جزئیات در معیارهای ارزیابی همین مرحله.")
    base = (f"✅ مرحله {num_fa} از ۵ انجام شد: {title_fa} — "
            f"این بخش از نیازمندی استاد برآورده شد.")
    if status == "warn":
        return base + " (با هشدار؛ به معیارهای ارزیابی توجه کنید.)"
    return base


# ---------------------------------------------------------------------------
# معیارهای تصویری
# ---------------------------------------------------------------------------
def image_quality_metrics(bgr: np.ndarray) -> dict:
    """تیزی (واریانس لاپلاسین)، کنتراست (انحراف معیار) و روشنایی تصویر."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    small = gray
    if gray.shape[1] > 800:
        scale = 800 / gray.shape[1]
        small = cv2.resize(gray, (800, max(1, int(gray.shape[0] * scale))),
                           interpolation=cv2.INTER_AREA)
    return {
        "sharpness": round(float(cv2.Laplacian(small, cv2.CV_64F).var()), 2),
        "contrast": round(float(gray.std()), 2),
        "brightness": round(float(gray.mean()), 2),
    }


# ---------------------------------------------------------------------------
# ساخت آیتم نمایش/گزارش از payload هر مرحله
# ---------------------------------------------------------------------------
def _metric(name_fa: str, value, status: str, note_fa: str = "") -> dict:
    return {"name_fa": name_fa, "value": value, "status": status,
            "note_fa": note_fa}


def _issue_note(issues: list) -> str:
    codes = [i.code for i in issues if i.code != "ok"]
    if not codes:
        return ""
    FA = {"blurry": "تاری", "dark": "نور کم", "bright": "بیش‌نوری",
          "glare": "انعکاس", "low_resolution": "رزولوشن پایین"}
    return "ملاحظات کیفیت: " + "، ".join(FA.get(c, c) for c in codes)


def build_stage_item(key: str, payload: dict) -> dict:
    """payload خام خط لوله → آیتم گزارش (JSON-سازگار؛ تصویر حذف می‌شود)."""
    sdef = STAGE_BY_KEY[key]
    metrics: list[dict] = []
    outputs: list[str] = []

    if key == "opencv":
        q_after = payload["quality_after"]
        q_before = payload["quality_before"]
        sharper = q_after["sharpness"] >= q_before["sharpness"] * 0.95
        metrics.append(_metric(
            "تیزی تصویر (واریانس لاپلاسین)",
            f"{q_before['sharpness']} ← {q_after['sharpness']}",
            "ok" if sharper else "warn",
            "پس از CLAHE/تیزکردن نباید افت محسوس داشته باشد"))
        metrics.append(_metric(
            "کنتراست", f"{q_before['contrast']} ← {q_after['contrast']}",
            "ok"))
        crop_note = ("برش دستی ناحیه برچسب اعمال شد"
                     if payload["crop_applied"]
                     else "بدون برش (کل تصویر پردازش شد)")
        metrics.append(_metric("ناحیه پردازش‌شده", crop_note, "ok"))
        metrics.append(_metric(
            "اصلاح زاویه چرخش",
            f"{payload['deskew_angle_deg']} درجه" if payload["deskew_applied"]
            else "لازم نبود", "ok"))
        metrics.append(_metric(
            "نسخه‌های پردازشی ساخته‌شده", "، ".join(payload["variants"]), "ok"))
        # v2.6.0 — مسیر گام‌به‌گام OpenCV در خروجی مرحله اعلام می‌شود
        _steps = payload.get("opencv_steps") or []
        if _steps:
            outputs.append(
                "🔬 مسیر گام‌به‌گام OpenCV: " + " ← ".join(_steps) +
                " — تصویر و توضیح هر گام در بخش «🔬 دیدن کار OpenCV و خوانش خام OCR» نمایش داده می‌شود.")
        outputs.append("🖼 خروجی این مرحله: تصویر بهبودیافته (پس از مقیاس، "
                       "CLAHE و تیزکردن) در بخش «مشاهده خروجی» نمایش داده می‌شود.")
        if payload["issues_note"]:
            outputs.append("⚠️ " + payload["issues_note"])
        status = "warn" if payload["issues_note"] else "done"

    elif key == "ocr":
        pieces = payload["pieces_count"]
        conf = payload["mean_confidence"]
        if pieces == 0:
            status = "fail"
            conf_status = "fail"
        elif conf is not None and conf < 0.6:
            status, conf_status = "warn", "warn"
        else:
            status, conf_status = "done", "ok"
        metrics.append(_metric(
            "قطعه‌های متنی خوانده‌شده", pieces,
            "ok" if pieces > 0 else "fail",
            "خروجی موتور پس از ادغام فازی نسخه‌های تکراری"))
        metrics.append(_metric(
            "میانگین اطمینان موتور OCR",
            "—" if conf is None else f"{round(conf * 100)}٪",
            conf_status,
            "اطمینان موتور معادل قطعیت صحت محتوا نیست"))
        metrics.append(_metric(
            "مجموع نویسه‌های خوانده‌شده", payload["chars_total"], "ok"))
        metrics.append(_metric(
            "سطرهای منطقی ساخته‌شده", payload["lines_count"], "ok"))
        # v2.0.0 — شفافیت مدل: کاربر می‌بیند کدام موتور/مدل خوانده است
        _engines = payload.get("engines_used") or [payload.get("engine", "—")]
        _engine_val = " + ".join(_engines)
        if "qwen3-vl" in _engines:
            _engine_val += " (دستیار Qwen3-VL-2B-Instruct)"
        if "surya" in _engines:
            _engine_val += " (Surya OCR — موتور سوم به انتخاب کاربر)"
        metrics.append(_metric(
            "موتور و مدل خوانش", _engine_val, "ok",
            "شرح کامل مدل‌ها در بخش «مدل‌ها و موتورها» راهنما"))
        # مقایسه نسخه‌های پردازشی (v1.7.0) — خروجی و دقت هر واریانت شفاف می‌شود
        vr_lines = []
        for vr in payload.get("variant_results", []) or []:
            conf_txt = ("—" if vr.get("mean_confidence") is None
                        else f"{round(vr['mean_confidence'] * 100)}٪")
            vr_lines.append(
                f"«{vr['variant']}»: {vr['pieces']} قطعه، "
                f"اطمینان {conf_txt}، امتیاز {vr['score']}")
        if vr_lines:
            outputs.append(
                "🔀 مقایسه نسخه‌های پردازشی (ادغام بهترین-اول): " +
                " | ".join(vr_lines))
        # v2.6.0 — خوانش خام هر نسخه (قبل از ادغام) شفاف می‌شود
        _readings = payload.get("variant_readings") or []
        if _readings:
            _total_dropped = sum(int(r.get("dropped", 0)) for r in _readings)
            _read_bits = []
            for r in _readings:
                _eng = (" + ".join(r.get("engines") or []) or "—")
                _read_bits.append(
                    f"«{r['variant']}»: {len(r.get('pieces') or [])} قطعه ({_eng})")
            outputs.append(
                "🔍 خوانش خام هر نسخه (قبل از ادغام و رأی‌گیری): " +
                " | ".join(_read_bits) +
                f" — مجموع قطعه‌های ردشدهٔ گیت کیفیت: {_total_dropped} — جزئیات و تصویر کادرها در بخش «🔬 دیدن کار OpenCV و خوانش خام OCR».")
        if payload.get("vlm_lines_added"):
            outputs.append(
                "🤖 " + (payload.get("vlm_note") or "دستیار بینایی سطرهای مکمل ارائه کرد")
                + " — شناسهٔ شاهد این سطرها vlm-* است.")
        outputs.append("📄 خروجی این مرحله: متن خام استخراج‌شده (سطر به سطر) — "
                       "در بخش «مشاهده خروجی» و در ناحیه «نواحی شناسایی‌شده OCR».")
        if payload.get("lines_preview"):
            outputs.append("نمونه سطرهای خوانده‌شده: " +
                           " / ".join(payload["lines_preview"]))

    elif key == "fields":
        cnt = payload["status_counts"]
        extracted = cnt.get("extracted", 0) + cnt.get("user_corrected", 0)
        if extracted == 0:
            status = "warn"
        else:
            status = "done"
        metrics.append(_metric(
            "فیلدهای استخراج‌شده", extracted, "ok" if extracted else "warn",
            "از مجموع ۷ فیلد مدل داده (نام، قدرت، تعداد، انقضا، وزن، سری، سازنده)"))
        metrics.append(_metric("فیلدهای نامطمئن", cnt.get("uncertain", 0),
                               "ok" if cnt.get("uncertain", 0) == 0 else "warn",
                               "مقادیر نامطمئن علامت می‌خورند و اصلاح دستی دارند"))
        metrics.append(_metric("فیلدهای غایب", cnt.get("missing", 0), "ok",
                               "روی برچسب خوانده نشده و از منبع دیگری تکمیل نمی‌شود"))
        metrics.append(_metric("فیلدهای متناقض", cnt.get("conflicting", 0),
                               "ok" if cnt.get("conflicting", 0) == 0 else "warn",
                               "به‌جای انتخاب خاموش یکی، تناقض اعلام می‌شود"))
        metrics.append(_metric(
            "پوشش شواهد (ردیابی‌پذیری)", f"{payload['evidence_coverage']}٪",
            "ok" if payload["evidence_coverage"] == 100 else "warn",
            "هر فیلد استخراج‌شده باید به شناسه قطعه OCR (شاهد) متصل باشد"))
        outputs.append("📋 خروجی این مرحله: جدول فیلدهای ساختاریافته با وضعیت "
                       "پنج‌گانه و اتصال هر مقدار به شواهد OCR.")
        outputs.append(f"نوع بسته تشخیص‌داده‌شده: {payload['product_type_fa']}")
        for w in payload.get("warnings_fa", []):
            outputs.append("ℹ️ " + w)

    elif key == "response":
        guard_ok = payload["guard_ok"]
        status = "done" if guard_ok else "fail"
        metrics.append(_metric(
            "نگهبان ایمنی (ممنوع‌واژه‌ها و ادعاها)",
            "عبور بدون نقض ✅" if guard_ok else
            "نقض: " + "؛ ".join(payload["guard_violations"]),
            "ok" if guard_ok else "fail",
            "اطلاعات خوانده‌شده از توصیه پزشکی جدا نگه داشته می‌شود — "
            "قدرت درج‌شده هرگز «دوز مصرف» نامیده نمی‌شود"))
        metrics.append(_metric(
            "مسیر تولید پاسخ",
            "LLM وفادار (اختیاری)" if payload["llm_used"]
            else "منطق استخراج قاعده‌محور (بدون مدل زبانی ابری)", "ok",
            "هر دو مسیر مطابق «یا»ی ملزومات استاد؛ هر دو از نگهبان عبور می‌کنند"))
        metrics.append(_metric("طول پاسخ (نویسه)", payload["length"], "ok"))
        outputs.append("🗣 خروجی این مرحله: پاسخ فارسی وفادار به متن بسته — "
                       "در بخش «پاسخ فارسی» نمایش داده می‌شود.")
        outputs.append("نمونه پاسخ: " + payload["preview"])

    elif key == STAGE_TTS_KEY:
        metrics.append(_metric(
            "موتور خوانش صوتی", payload["provider"], "ok", payload["note_fa"]))
        metrics.append(_metric(
            "آماده‌سازی متن برای تلفظ",
            f"{payload['spoken_chars']} نویسه (اعداد برای خوانش درست آماده شد)",
            "ok"))
        if payload["synthesized"]:
            metrics.append(_metric("وضعیت صوت", "تولید شد ✅", "ok"))
            status = "done"
        else:
            metrics.append(_metric(
                "وضعیت صوت", "در انتظار رضایت و دکمه پخش", "warn",
                "تولید صوت تنها با رضایت صریح شما انجام می‌شود"))
            status = "pending"
        outputs.append("🔊 خروجی این مرحله: متن آماده خوانش + پخش‌کننده صوتی — "
                       "در بخش «پخش صوتی فارسی».")

    else:  # pragma: no cover - کلید ناشناخته
        status = "done"

    return {
        "key": key,
        "num_fa": sdef["num_fa"],
        "title_fa": sdef["title_fa"],
        "requirement_fa": sdef["requirement_fa"],
        "files_desktop_fa": sdef["files_desktop_fa"],
        "files_mobile_fa": sdef["files_mobile_fa"],
        "status": status,
        "duration_ms": payload.get("duration_ms"),
        "start_label": start_message(sdef["num_fa"], sdef["title_fa"]),
        "done_label": f"مرحله {sdef['num_fa']} از ۵ {STATUS_FA.get(status, '')}".strip(),
        "done_message_fa": done_message(sdef["num_fa"], sdef["title_fa"], status),
        "outputs_fa": outputs,
        "metrics": metrics,
    }


def tts_payload(provider: str, note_fa: str, spoken_text: str,
                synthesized: bool) -> dict:
    return {
        "provider": provider, "note_fa": note_fa,
        "spoken_chars": len(spoken_text), "synthesized": synthesized,
        "duration_ms": None,
    }


def summary_rows(records: list[dict]) -> list[dict]:
    """سطرهای جدول خلاصه: مرحله | الزام | وضعیت | زمان."""
    rows = []
    for r in records:
        dur = r.get("duration_ms")
        rows.append({
            "مرحله": f"{r['num_fa']} — {r['title_fa']}",
            "الزام استاد": r["requirement_fa"],
            "وضعیت": STATUS_FA.get(r["status"], r["status"]),
            "زمان (ms)": "—" if dur is None else dur,
        })
    return rows


def report_json(records: list[dict], metadata: dict) -> str:
    """گزارش ارزیابی مرحله‌ای (JSON) برای دانلود — بدون تصویر و بدون متن کامل برچسب."""
    import json

    return json.dumps({
        "report": "stage_evaluation_report",
        "project": "برچسب‌خوان هوشمند دارو و محصولات (LabelVoice)",
        "requirement_basis": "ملزومات طرح‌شده توسط استاد قربانی — دسته ۲: نمودار معماری",
        "problem_statement": PROBLEM_STATEMENT_FA,
        "stages": [
            {k: v for k, v in r.items() if k != "outputs_fa" or True}
            for r in records
        ],
        "metadata": metadata,
    }, ensure_ascii=False, indent=2, default=str)

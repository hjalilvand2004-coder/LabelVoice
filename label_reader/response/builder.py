# -*- coding: utf-8 -*-
"""تولید پاسخ فارسی قالبی — فقط و فقط از فیلدهای استخراج‌شده با شواهد.

مسیر پیش‌فرض تولید پاسخ همانند این ماژول است؛ LLM (در صورت فعال‌سازی) فقط
برای بازنویسی وفادار به همین شواهد استفاده و توسط guard اعتبارسنجی می‌شود.
مرزهای کلیدی:
- قدرت درج‌شده هرگز «دوز مصرف» نامیده نمی‌شود.
- هیچ کاربرد درمانی، توصیه یا برنامه مصرفی اضافه نمی‌شود.
- اطلاعات نامطمئن قطعی بیان نمی‌شوند.
- نام لاتین بدون تغییر حفظ می‌شود.
"""
from __future__ import annotations

from ..models import FieldRecord, FieldStatus, QualityIssue
from ..textnorm import digits_to_persian

NO_TEXT_RESPONSE_FA = (
    "هیچ متن قابل خواندنی در این تصویر شناسایی نشد. "
    "لطفاً دوربین را ثابت نگه دارید، متن بسته را کامل در کادر قرار دهید، "
    "نور را بهتر کنید و از انعکاس نور جلوگیری کنید؛ سپس دوباره تلاش کنید."
)

DISCLAIMER_FA = (
    "این اطلاعات از متن قابل خواندن بسته استخراج شده‌اند و توصیه پزشکی "
    "یا تعیین مقدار مصرف نیستند."
)

UNIT_FA = {
    "mg": "میلی‌گرم", "mcg": "میکروگرم", "g": "گرم", "mL": "میلی‌لیتر",
    "L": "لیتر", "%": "درصد", "IU": "واحد بین‌المللی",
}

COUNT_UNIT_FA = {
    "tablets": "قرص", "capsules": "کپسول", "suppositories": "شیاف",
    "sachets": "ساشه", "vials": "ویال", "ampoules": "آمپول", "drops": "قطره",
    "قرص": "قرص", "کپسول": "کپسول", "عدد": "عدد", "ساشه": "ساشه",
    "ویال": "ویال", "آمپول": "آمپول", "شیاف": "شیاف", "قطره": "قطره",
}


def _is_present(field: FieldRecord) -> bool:
    return field.status in (
        FieldStatus.EXTRACTED, FieldStatus.UNCERTAIN,
        FieldStatus.CONFLICTING, FieldStatus.USER_CORRECTED,
    ) and field.value


def format_strength(field: FieldRecord) -> str:
    """قدرت درج‌شده؛ تفاوت «۵۰۰ میلی‌گرم» و «۲۵۰ میلی‌گرم در ۵ میلی‌لیتر» حفظ می‌شود."""
    v = (field.value or "").strip()
    if field.unit:
        return f"{digits_to_persian(v)} {UNIT_FA.get(field.unit, field.unit)}"
    parts = v.split()
    if len(parts) == 4 and parts[1] == "/" or " / " in v or "/" in v and " " in v:
        # قالب "250 mg/5 mL"
        try:
            num1, unit1 = parts[0], parts[1].split("/")[0]
            rest = v.split("/", 1)[1].strip()
            num2, unit2 = rest.split()
            return (f"{digits_to_persian(num1)} {UNIT_FA.get(unit1, unit1)} "
                    f"در {digits_to_persian(num2)} {UNIT_FA.get(unit2, unit2)}")
        except (ValueError, IndexError):
            pass
    return digits_to_persian(v)


def format_count(field: FieldRecord) -> str:
    unit = COUNT_UNIT_FA.get(field.unit or "", field.unit or "")
    return f"{digits_to_persian(field.value)} {unit}".strip()


def format_value(field: FieldRecord) -> str:
    return digits_to_persian(field.value or "")


def _field_sentence(field: FieldRecord) -> str | None:
    if not _is_present(field):
        return None
    label = field.label_fa
    if field.key == "strength":
        display = format_strength(field)
    elif field.key == "count":
        display = format_count(field)
    elif field.key in ("name",):
        display = field.value  # نام لاتین حفظ می‌شود
    elif field.key == "active_ingredient":
        display = field.value
    else:
        display = format_value(field)
    if field.status == FieldStatus.CONFLICTING:
        return (f"{label}: دو یا چند مقدار متفاوت خوانده شد و مقدار قطعی اعلام "
                f"نمی‌شود ({display} یکی از خوانش‌ها است). {field.note_fa or ''}").strip()
    if field.status == FieldStatus.UNCERTAIN:
        if field.key in ("strength", "count", "expiry_date", "production_date"):
            return (f"{label}: مقدار به‌طور واضح خوانده نشد؛ خوانش احتمالی «{display}» "
                    f"است و به‌عنوان مقدار قطعی خوانده نمی‌شود.")
        return f"{label}: «{display}» (با اطمینان پایین OCR)."
    if field.status == FieldStatus.USER_CORRECTED:
        return f"{label}: {display} (اصلاح‌شده توسط شما)."
    if field.key == "name":
        return f"{label}: {display}."
    if field.key in ("storage", "warnings", "ingredients", "manufacturer",
                     "printed_directives"):
        return f"{label}: «{display}»."
    return f"{label}: {display}."


def _quality_sentence(issues: list[QualityIssue]) -> str | None:
    severe = [i for i in issues if i.severity in ("warning", "severe")
              and i.code != "ok"]
    if not severe:
        return None
    msgs = " ".join(i.message_fa for i in severe)
    return f"هشدار کیفیت تصویر: {msgs}"


def build_response(
    fields: dict[str, FieldRecord],
    quality_issues: list[QualityIssue],
    extraction_warnings: list[str],
    ocr_piece_count: int,
) -> str:
    """پاسخ فارسی قالبی وفادار به شواهد."""
    if ocr_piece_count == 0:
        return NO_TEXT_RESPONSE_FA

    present_any = any(_is_present(f) for f in fields.values())
    if not present_any:
        return (NO_TEXT_RESPONSE_FA.split("، سپس")[0] + ". " + DISCLAIMER_FA)

    sentences: list[str] = []
    q = _quality_sentence(quality_issues)
    if q:
        sentences.append(q)

    order = ["name", "active_ingredient", "strength", "count", "dosage_form",
             "net_weight", "ingredients", "manufacturer", "batch",
             "production_date", "expiry_date", "storage", "warnings"]
    for key in order:
        f = fields.get(key)
        if f is None:
            continue
        if key == "storage" and not _is_present(f):
            continue
        s = _field_sentence(f)
        if s:
            sentences.append(s)

    directives = fields.get("printed_directives")
    if directives and _is_present(directives):
        sentences.append(
            f"متن دستور چاپ‌شده روی بسته: «{directives.value}». این صرفاً "
            f"بازخوانی متن چاپ‌شده است و توصیه شخصی به شما نیست.")

    for w in extraction_warnings:
        sentences.append(w)

    missing_keys_note = []
    for key in ("strength", "count"):
        f = fields.get(key)
        if f is not None and f.status == FieldStatus.MISSING:
            missing_keys_note.append(f.label_fa)
    if missing_keys_note and ocr_piece_count > 0:
        sentences.append(
            f"برای {' و '.join(missing_keys_note)} مقدار واضحی روی برچسب خوانده نشد؛ "
            f"مقدار غایب از هیچ منبع دیگری تکمیل نمی‌شود.")

    sentences.append(DISCLAIMER_FA)
    return " ".join(sentences)

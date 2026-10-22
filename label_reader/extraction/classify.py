# -*- coding: utf-8 -*-
"""طبقه‌بندی نوع بسته: medicine | general_product | unknown.

این طبقه‌بندی فقط برای انتخاب قالب فیلدهاست و به هیچ عنوان تأیید هویت یا
اصالت محصول محسوب نمی‌شود.
"""
from __future__ import annotations

import re

from ..models import ProductType

_MEDICINE_KEYWORDS = [
    "قرص", "کپسول", "میلی گرم", "میکروگرم", "دارو", "ماده م[وؤ]ثره", "م[وؤ]ثره",
    "شربت", "سوسپانسیون", "آمپول", "ویال", "شیاف", "قطره چشم", "ساشه دارویی",
    "tablets", "tablet", "capsules", "capsule", "syrup", "suspension",
    "injection", "suppository", "ointment", "active ingredient", "dose",
    "medicine", "pharmaceutical",
]

# نشانه‌های قوی دارویی با مرز واژه (mg در وسط کلمات دیگر نیست)
_MEDICINE_STRONG_RE = re.compile(
    r"\bmg\b|\bmcg\b|\btablets?\b|\bcapsules?\b|\bml\b", re.IGNORECASE)

_GENERAL_KEYWORDS = [
    "وزن خالص", "حجم خالص", "خالص", "ترکیبات", "مواد تشکیل دهنده", "محصول",
    "net wt", "net weight", "ingredients", "product", "biscuit", "chocolate",
    "شامپو", "صابون", "کیک", "بیسکویت", "شکلات", "نوشیدنی", "juice", "shampoo",
]


def classify_product_type(lines_text: list[str]) -> tuple[ProductType, str]:
    """امتیازدهی واژگانی؛ بازگشت (نوع، توضیح فارسی)."""
    joined = " | ".join(lines_text)
    medicine_hits = sum(1 for kw in _MEDICINE_KEYWORDS if kw in joined)
    if _MEDICINE_STRONG_RE.search(joined):
        medicine_hits += 2  # واحد mg/mcg/tablet نشانه قوی دارو است
    general_hits = sum(1 for kw in _GENERAL_KEYWORDS if kw in joined)

    if medicine_hits >= 2 and medicine_hits >= general_hits:
        return ProductType.MEDICINE, "بر اساس واژه‌های دارویی روی برچسب (قرص، میلی‌گرم و مانند آن)."
    if general_hits >= 2 and general_hits > medicine_hits:
        return (ProductType.GENERAL_PRODUCT,
                "بر اساس واژه‌های محصول عمومی روی برچسب (وزن خالص، ترکیبات و مانند آن).")
    return ProductType.UNKNOWN, "نشانه کافی برای طبقه‌بندی یافت نشد؛ قالب عمومی استفاده می‌شود."

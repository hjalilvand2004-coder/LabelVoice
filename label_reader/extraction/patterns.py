# -*- coding: utf-8 -*-
"""الگوهای قابل آزمون برای استخراج فیلدها (Regex + قواعد صریح).

همه الگوها روی «متن نرمال‌شده برای مطابقه» اجرا می‌شوند (ارقام لاتین،
ي/ی و ك/ک یکسان، نیم‌فاصله به فاصله). واحدها بدون تغییر معنایی حفظ می‌شوند؛
تفاوت mg و mcg و «میلی‌گرم» و «میلی‌گرم در میلی‌لیتر» رعایت می‌شود.
هیچ حدسی برای رفع ابهام 0/O، 1/I یا mg/mcg زده نمی‌شود.
"""
from __future__ import annotations

import re

RE_NUM = r"\d+(?:[.,]\d+)?"

# واحدها: لاتین + فارسی (بعد از نرمال‌سازی، نیم‌فاصله فاصله است)
_UNIT_TOKENS = [
    r"mg\.", "mg", "mcg", r"µg", r"μg", "ug", "ml", "iu", "g", "l", "%",
    "میلی گرم", "میل گرم", "میکروگرم", "میکرو گرم", "گرم", "میلی لیتر",
    "میلی لیتر", "درصد",
]
_UNIT_ALT = "|".join(re.escape(u) if u not in ("%",) else "%" for u in _UNIT_TOKENS)
_UNIT_GROUP = rf"(?P<unit>{_UNIT_ALT})"

# الگوی قدرت؛ نسخه ترکیبی مثل 250 mg/5 mL هم پوشش داده می‌شود
RE_STRENGTH = re.compile(
    rf"(?P<num>{RE_NUM})\s*{_UNIT_GROUP}"
    rf"(?:\s*/\s*(?P<num2>{RE_NUM})\s*(?P<unit2>{_UNIT_ALT}))?(?![A-Za-z])",
    re.IGNORECASE,
)

RE_COUNT = re.compile(
    rf"(?P<num>\d+)\s*(?P<noun>tablets?|tabs|capsules?|caps|suppositor\w*|"
    rf"sachets?|vials?|ampoules?|amps?|drops|قرص|کپسول|عدد|ساشه|ویال|آمپول|شیاف|قطره)",
    re.IGNORECASE,
)
RE_COUNT_REV = re.compile(
    rf"(?P<noun>قرص|کپسول|ساشه|ویال|آمپول|شیاف|قطره|عدد)\s*(?P<num>\d+)"
)

RE_DATE_VALUE = re.compile(
    r"(?<!\d)(?P<d1>\d{1,4})[/\-.](?P<d2>\d{1,2})(?:[/\-.](?P<d3>\d{2,4}))?(?!\d)")
RE_YEAR_ONLY = re.compile(r"(?<![\d/])(\d{4})(?![\d/])")

RE_EXPIRY_LABEL = re.compile(
    r"exp(?:iry)?\.?(?:\s*date)?|best\s*before|use\s*by|see\s*(?:base|bottle)|"
    r"تاریخ\s*انقضا|انقضا|سرسید", re.IGNORECASE)
RE_PRODUCTION_LABEL = re.compile(
    r"mfg|mfd|m\.?f\.?g|man(?:ufactur\w*)?|prod(?:uction|\.)?|"
    r"تاریخ\s*تولید|تاریخ\s*پroduction|تولید", re.IGNORECASE)
RE_BATCH_LABEL = re.compile(
    r"batch|lot(?:\s*no)?|b\.?no\.?|b/n|ch\.?/?b|سری\s*ساخت|شماره\s*سری|سری",
    re.IGNORECASE)
RE_BATCH_VALUE = re.compile(r"(?P<val>[A-Za-z0-9][A-Za-z0-9/\-.]{2,24})")

RE_WARNING_KEYWORD = re.compile(
    r"دور از دسترس|کودکان|طبق دستور پزشک|باردار|شیرده|احتیاط|keep\s*out\s*of\s*reach|"
    r"keep\s+away\s+from\s+children|out\s+of\s+the\s+reach|warning|caution",
    re.IGNORECASE)

# دستورهای چاپ‌شده روی بسته (فقط به‌عنوان «متن چاپ‌شده» بازخوانی می‌شوند)
RE_DIRECTIVE_KEYWORD = re.compile(
    r"مصرف کنید|خورده شود|هر\s*\d+\s*(ساعت|روز)|روزانه\s*\d+|\d+\s*بار\s*(در|در)\s*روز|"
    r"بعد\s*از\s*غذا|قبل\s*از\s*غذا|با\s*آب|take\s+\d+|every\s+\d+\s*(hours?|days?)|"
    r"daily|orally|after\s+meal|before\s+meal|with\s+water|with\s+food",
    re.IGNORECASE)

RE_INGREDIENT_KEYWORD = re.compile(
    r"ماده\s*م[وؤ]ثره|م[وؤ]ثره|ترکیب|حاوی|active\s+ingredient|contains|composition",
    re.IGNORECASE)

RE_MANUFACTURER_KEYWORD = re.compile(
    r"company|corporation|\bcorp\b|\bco\.|pharma\w*|laborator\w*|industr\w*|"
    r"gmbh|ltd|\binc\b|"
    r"شرکت|داروسازی|سازنده|تولید\s*کننده|تولیدکننده",
    re.IGNORECASE)

RE_STORAGE_KEYWORD = re.compile(
    r"نگهداری|دمای\s*اتاق|دور\s*از\s*نور|یخچال|store|storage|keep\s+below|"
    r"below\s+\d+\s*°?c|protect\s+from\s+light",
    re.IGNORECASE)

RE_DOSAGE_FORM = re.compile(
    r"tablets?|tabs|capsules?|caps|syrup|suspension|solution|injection|cream|"
    r"ointment|drops|suppositor\w*|sachet|vial|ampoule|قرص|کپسول|شربت|سوسپانسیون|"
    r"محلول|آمپول|کرم|پماد|قطره|شیاف|ساشه",
    re.IGNORECASE)

RE_NET_WEIGHT_KEYWORD = re.compile(
    r"net\s*(?:wt|weight)|وزن\s*خالص|حجم\s*خالص|خالص|bottle|tube", re.IGNORECASE)

# نقشه یکسان‌سازی املا واحد برای نگهداشت بدون تغییر معنایی
UNIT_CANONICAL = {
    "mg.": "mg", "mg": "mg", "میلی گرم": "mg", "میل گرم": "mg",
    "mcg": "mcg", "µg": "mcg", "μg": "mcg", "ug": "mcg",
    "میکروگرم": "mcg", "میکرو گرم": "mcg",
    "g": "g", "گرم": "g",
    "ml": "mL", "میلی لیتر": "mL",
    "l": "L",
    "%": "%", "درصد": "%",
    "iu": "IU",
}

COUNT_NOUN_CANONICAL = {
    "tablet": "tablets", "tablets": "tablets", "tabs": "tablets",
    "capsule": "capsules", "capsules": "capsules", "caps": "capsules",
    "suppositories": "suppositories", "suppository": "suppositories",
    "sachet": "sachets", "sachets": "sachets",
    "vial": "vials", "vials": "vials",
    "ampoule": "ampoules", "ampoules": "ampoules", "amps": "ampoules",
    "drop": "drops", "drops": "drops",
    "قرص": "قرص", "کپسول": "کپسول", "عدد": "عدد", "ساشه": "ساشه",
    "ویال": "ویال", "آمپول": "آمپول", "شیاف": "شیاف", "قطره": "قطره",
}

DOSAGE_FORM_FA = {
    "tablets": "قرص", "tablets.": "قرص", "capsules": "کپسول", "syrup": "شربت",
    "suspension": "سوسپانسیون", "solution": "محلول", "injection": "تزریقی",
    "cream": "کرم", "ointment": "پماد", "drops": "قطره",
    "suppositories": "شیاف", "sachet": "ساشه", "vial": "ویال",
    "ampoule": "آمپول", "قرص": "قرص", "کپسول": "کپسول", "شربت": "شربت",
    "سوسپانسیون": "سوسپانسیون", "محلول": "محلول", "آمپول": "آمپول",
    "کرم": "کرم", "پماد": "پماد", "قطره": "قطره", "شیاف": "شیاف",
    "ساشه": "ساشه",
}


def looks_like_date_value(text: str) -> bool:
    m = RE_DATE_VALUE.search(text)
    return m is not None


def infer_date_ambiguity(d1: str, d2: str, d3: str | None) -> tuple[str, bool]:
    """بازگشت (مقدار نرمال، مبهم؟). تاریخ مبهم بدون شواهد قطعی نمی‌شود."""
    if len(d1) == 4:  # YYYY/…
        val = f"{d1}/{d2}" + (f"/{d3}" if d3 else "")
        ambiguous = d3 is None and int(d2) > 12  # قطعه دوم ماه نیست
        return val, False if d3 else False
    if d3 is not None:  # DD/MM/YYYY یا MM/DD/YYYY → ترتیب قطعی نیست
        return f"{d1}/{d2}/{d3}", True
    # دو قطعه بدون سال چهاررقمی: مبهم (سال دو رقمی یا ماه/روز)
    return f"{d1}/{d2}", True

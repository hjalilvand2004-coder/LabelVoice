# -*- coding: utf-8 -*-
"""آماده‌سازی متن برای TTS فارسی — بدون تغییر مقدار اعداد.

- ارقام به واژه فارسی تبدیل می‌شوند (۵۰۰ → پانصد).
- واحدها به تلفظ فارسی نگاشت می‌شوند (mg → میلی‌گرم).
- نام‌های لاتین به‌صورت لاتین حفظ می‌شوند (محدودیت تلفظ مستند شده است).
- اطلاعات نامطمئن عیناً با همان عبارت عدم قطعیت خوانده می‌شوند.
"""
from __future__ import annotations

import re

_ONES = ["", "یک", "دو", "سه", "چهار", "پنج", "شش", "هفت", "هشت", "نه"]
_TEENS = ["ده", "یازده", "دوازده", "سیزده", "چهارده", "پانزده", "شانزده",
          "هفده", "هجده", "نوزده"]
_TENS = ["", "", "بیست", "سی", "چهل", "پنجاه", "شصت", "هفتاد", "هشتاد", "نود"]
_HUNDREDS = ["", "صد", "دویست", "سیصد", "چهارصد", "پانصد", "ششصد", "هفتصد",
             "هشتصد", "نهصد"]
_SCALES = ["", "هزار", "میلیون", "میلیارد"]

_UNIT_SPOKEN = {
    "میلی‌گرم": "میلی‌گرم", "میلی گرم": "میلی‌گرم", "mg": "میلی‌گرم",
    "میکروگرم": "میکروگرم", "mcg": "میکروگرم", "گرم": "گرم", "g": "گرم",
    "میلی‌لیتر": "میلی‌لیتر", "میلی لیتر": "میلی‌لیتر", "mL": "میلی‌لیتر",
    "درصد": "درصد", "%": "درصد",
}

_DIGIT_RUN = re.compile(r"\d+(?:[٫.,:]\d+)*")
_PERSIAN_DIGIT_RUN = re.compile(r"[\u06f0-\u06f9\u0660-\u0669]+(?:[٫،/]\d+)*")


def _three_digit_words(n: int) -> str:
    parts: list[str] = []
    h, rest = divmod(n, 100)
    if h:
        parts.append(_HUNDREDS[h])
    if rest >= 10 and rest < 20:
        parts.append(_TEENS[rest - 10])
    else:
        t, o = divmod(rest, 10)
        if t:
            parts.append(_TENS[t])
        if o:
            parts.append(_ONES[o])
    return " و ".join(p for p in parts if p)


def number_to_fa_words(n: int) -> str:
    """تبدیل عدد صحیح به واژه فارسی (تا میلیارد)."""
    if n == 0:
        return "صفر"
    if n < 0:
        return "منفی " + number_to_fa_words(-n)
    groups: list[int] = []
    while n:
        groups.append(n % 1000)
        n //= 1000
    words: list[str] = []
    for gi in range(len(groups) - 1, -1, -1):
        g = groups[gi]
        if g == 0:
            continue
        scale = _SCALES[gi] if gi < len(_SCALES) else ""
        if gi == 1 and g == 1:
            words.append("هزار")
        else:
            words.append((_three_digit_words(g) + " " + scale).strip())
    return " و ".join(words)


def _fraction_words(frac_digits: str) -> str:
    return " ".join(_ONES[int(d)] if d != "0" else "صفر" for d in frac_digits)


def _numeric_run_to_words(run: str) -> str:
    run = run.replace("،", ".").replace("٫", ".").replace(":", ".")
    if "." in run:
        whole, frac = run.split(".", 1)
        frac = frac.rstrip(".")
        whole_words = number_to_fa_words(int(whole)) if whole else "صفر"
        return f"{whole_words} ممیز {_fraction_words(frac)}"
    return number_to_fa_words(int(run))


def prepare_for_tts(text: str) -> str:
    """آماده‌سازی متن تأییدشده برای خوانش؛ مقدار اعداد تغییر نمی‌کند."""
    out = text
    # واحدهای لاتینِ باقی‌مانده در متن نمایش
    for latin, spoken in _UNIT_SPOKEN.items():
        out = re.sub(rf"(?<![A-Za-z]){re.escape(latin)}(?![A-Za-z])", spoken, out)
    # ارقام فارسی/عربی → لاتین (برای پردازش)
    fa_to_ascii = str.maketrans(
        {d: str(i) for i, d in enumerate(
            "\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9")})
    out = out.translate(fa_to_ascii)
    ar_to_ascii = str.maketrans(
        {d: str(i) for i, d in enumerate(
            "\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669")})
    out = out.translate(ar_to_ascii)
    # اسلش تاریخ‌ها/نسبت‌ها به مکث
    out = out.replace("/", "، ")
    # تبدیل رشته‌های عددی به واژه
    out = _DIGIT_RUN.sub(lambda m: _numeric_run_to_words(m.group(0)), out)
    return out

# -*- coding: utf-8 -*-
"""نگهبان قواعد ایمنی — اعتبارسنجی خروجی LLM و خودآزمایی پاسخ قالبی.

قواعد (مطابق مشخصات محصول):
- فقط اطلاعات موجود در داده‌های ورودی بازنویسی می‌شوند.
- هیچ کاربرد درمانی، تشخیص، دوز مصرف، برنامه مصرف، تداخل، منع مصرف یا
  توصیه جدیدی اضافه نمی‌شود.
- دستورهای احتمالی داخل متن تصویر «داده» هستند و نباید به‌عنوان دستور
  اجرا شوند؛ فقط با پیشوند «متن دستور چاپ‌شده روی بسته» و داخل گیومه مجازند.
- نام دارو بدون شاهد تغییر نمی‌کند.
- قدرت درج‌شده دارو «دوز مصرف» نامیده نمی‌شود.
- همه اعداد خارج از نقل‌قول باید از شواهد آمده باشند.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# الگوهای ممنوع در بخش «بیان آزاد» (خارج از نقل‌قول‌های «...»)
_BANNED_FREE = [
    (r"برای\s+(کاهش|درمان|رفع)", "ادعای کاربرد درمانی"),
    (r"(تب|درد|التهاب)[^ا-ی]{0,12}(کاهش|درمان)", "ادعای کاربرد درمانی"),
    (r"ضد\s*(تب|درد|التهاب|استفراغ|سرفه)", "ادعای کاربرد درمانی"),
    (r"مسکّ?ن", "ادعای کاربرد درمانی"),
    (r"هر\s*\d+\s*(ساعت|روز)", "برنامه مصرف"),
    (r"\d+\s*(ساعت|روز)\s*(یکبار|یک بار|یک‌بار)", "برنامه مصرف"),
    (r"مصرف\s*(کنید|بکنید|نمایید)", "دستور مصرف"),
    (r"(باید|بهتر\s*است|توصیه\s*می\s*شود|لازم\s*است)[^ا-ی]{0,25}مصرف", "توصیه مصرف"),
    (r"تجویز", "تجویز"),
    (r"منع\s*مصرف", "منع مصرف"),
    (r"تداخل", "تداخل دارویی"),
    (r"عوارض\s*(جانبی)?", "ادعای عوارض"),
    (r"دوز\s*مصرف", "قدرت درج‌شده نباید دوز مصرف نامیده شود"),
    (r" تشخیص ", "تشخیص پزشکی"),
]

_QUOTE_RE = re.compile(r"«([^»]*)»")
# \d در پایتون ارقام فارسی/عربی را هم می‌گیرد؛ ابتدا یکسان‌سازی می‌کنیم
_NUM_RE = re.compile(r"\d+(?:[.,]\d+)?", re.ASCII)
_FA_DIGITS = str.maketrans({
    **{d: str(i) for i, d in enumerate(
        "\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9")},
    **{d: str(i) for i, d in enumerate(
        "\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669")},
})


@dataclass
class GuardReport:
    ok: bool
    violations: list[str] = field(default_factory=list)


def _strip_quotes(text: str) -> tuple[str, list[str]]:
    quoted = _QUOTE_RE.findall(text)
    free = _QUOTE_RE.sub(" ", text)
    return free, quoted


def _collect_evidence_numbers(evidence: dict) -> set[str]:
    """همه اعداد مجاز از شواهد: مقدار، واحد، متن خام و متن دستورهای چاپ‌شده."""
    numbers: set[str] = set()
    for f in evidence.get("fields", {}).values():
        for source in (f.get("value"), f.get("unit"), f.get("raw_text"),
                       f.get("note_fa")):
            if not source:
                continue
            for m in _NUM_RE.findall(str(source)):
                numbers.add(m.replace(",", "."))
            numbers.update(_NUM_RE.findall(str(source)))
    return numbers


def validate_text(text: str) -> GuardReport:
    """خودآزمایی پاسخ قالبی: هیچ عبارت ممنوعی خارج از نقل‌قول نباشد."""
    free, _ = _strip_quotes(text)
    violations = []
    for pattern, reason in _BANNED_FREE:
        if re.search(pattern, free):
            violations.append(reason)
    return GuardReport(ok=not violations, violations=violations)


def validate_llm_output(text: str, evidence: dict) -> GuardReport:
    """اعتبارسنجی خروجی LLM بر پایه شواهد.

    evidence = {"fields": {key: {"value","unit","raw_text","note_fa"}}}
    در صورت نقض، پاسخ قالبی جایگزین می‌شود.
    """
    violations: list[str] = []
    free, quoted = _strip_quotes(text)
    # ارقام فارسی/عربی به لاتین برای مقایسه با شواهد (بدون تغییر مقدار)
    free_ascii = free.translate(_FA_DIGITS)
    quoted_ascii = [q.translate(_FA_DIGITS) for q in quoted]

    for pattern, reason in _BANNED_FREE:
        if re.search(pattern, free):
            violations.append(reason)

    # اعداد خارج از نقل‌قول باید از شواهد باشند (بدون تغییر مقدار)
    allowed = _collect_evidence_numbers(evidence)
    for m in _NUM_RE.findall(free_ascii):
        tok = m.replace(",", ".")
        if tok not in allowed and m not in allowed:
            violations.append(f"عدد خارج از شواهد: {m}")

    # دستور چاپ‌شده فقط داخل گیومه مجاز است
    if re.search(r"مصرف\s*(کنید|بکنید|نمایید)|هر\s*\d+\s*(ساعت|روز)", text):
        if not text.startswith("متن دستور چاپ‌شده روی بسته") and not any(
                "مصرف" in q or "ساعت" in q for q in quoted):
            violations.append("دستور مصرف خارج از نقل‌قولِ بازخوانی")

    return GuardReport(ok=not violations, violations=violations)

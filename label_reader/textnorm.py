# -*- coding: utf-8 -*-
"""نرمال‌سازی متن فارسی/انگلیسی برای پردازش داخلی.

مرزهای مهم:
- فقط اصلاح‌های نویسه‌ای مجاز است: «ي→ی»، «ك→ک»، یکسان‌سازی ارقام فارسی/عربی/لاتین.
- نام دارو یا برند به‌صورت خودکار و بدون شواهد تصحیح نمی‌شود.
- ابهام‌های 0/O، 1/I و mg/mcg با حدس پنهان برطرف نمی‌شود.
- متن خام جدا نگه داشته می‌شود؛ این ماژول فقط برای «مطابقه» به کار می‌رود.
"""
from __future__ import annotations

import re
import unicodedata

# --- نگاشت نویسه‌های عربی به فارسی ---
CHAR_MAP = {
    "\u064a": "\u06cc",  # ي -> ی
    "\u0649": "\u06cc",  # ى -> ی
    "\u0643": "\u06a9",  # ك -> ک
    "\u0629": "\u0647",  # ة -> ه
    "\u0623": "\u0627",  # أ -> ا
    "\u0625": "\u0627",  # إ -> ا
    "\u0622": "\u0627",  # آ -> ا (فقط برای مطابقه؛ نمایش خام جدا است)
    "\u0640": "",        # کشیده (tatweel) حذف
}

# --- ارقام ---
ARABIC_DIGITS = "\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669"  # ۰..۹ عربی
PERSIAN_DIGITS = "\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9"  # ۰..۹ فارسی

_TO_ASCII = str.maketrans(
    {**{d: str(i) for i, d in enumerate(PERSIAN_DIGITS)},
     **{d: str(i) for i, d in enumerate(ARABIC_DIGITS)}}
)
_TO_PERSIAN = str.maketrans({str(i): d for i, d in enumerate(PERSIAN_DIGITS)})

_ZWNJ = "\u200c"
_ZWJ = "\u200d"
_RLM = "\u200f"
_LRM = "\u200e"

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_chars(text: str) -> str:
    """اصلاح نویسه‌های مجاز بدون تغییر معنا (برای نمایش نرمال‌شده هم به کار می‌رود)."""
    if not text:
        return text
    out = text.translate(str.maketrans(CHAR_MAP))
    return out


def normalize_digits_ascii(text: str) -> str:
    """ارقام فارسی/عربی به لاتین (برای پردازش داخلی و regex)."""
    if not text:
        return text
    return text.translate(_TO_ASCII)


def digits_to_persian(text: str) -> str:
    """ارقام لاتین به فارسی (فقط برای نمایش/خوانش)."""
    if not text:
        return text
    return text.translate(_TO_PERSIAN)


def normalize_for_matching(text: str) -> str:
    """نرمال‌سازی کامل برای مطابقه الگوها:
    اصلاح نویسه + یکسان‌سازی ارقام به لاتین + تبدیل نیم‌فاصله به فاصله +
    حذف کنترل‌های جهت + فشرده‌سازی فاصله‌ها.
    مقدار واحد (500) تغییر نمی‌کند؛ فقط قالب متن.
    """
    if not text:
        return text
    t = unicodedata.normalize("NFC", text)
    t = normalize_chars(t)
    t = t.translate(_TO_ASCII)
    t = t.replace(_ZWNJ, " ").replace(_ZWJ, " ").replace(_RLM, " ").replace(_LRM, " ")
    t = _WHITESPACE_RE.sub(" ", t)
    return t.strip()


def cleaned_display_text(text: str) -> str:
    """نرمال‌سازی ملایم برای «نمایش متن نرمال‌شده»: اصلاح نویسه + فشرده‌سازی فاصله،
    بدون تبدیل ارقام و بدون حذف نیم‌فاصله."""
    if not text:
        return text
    t = unicodedata.normalize("NFC", text)
    t = normalize_chars(t)
    t = t.replace(_ZWJ, "").replace(_RLM, " ").replace(_LRM, " ")
    t = _WHITESPACE_RE.sub(" ", t)
    return t.strip()


def is_mostly_latin(text: str) -> bool:
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return False
    latin = sum(1 for ch in letters if "\u0000" <= ch <= "\u024f")
    return latin / len(letters) > 0.5


def is_mostly_persian(text: str) -> bool:
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return False
    fa = sum(1 for ch in letters if "\u0600" <= ch <= "\u06ff")
    return fa / len(letters) > 0.5


# ---------------------------------------------------------------------------
# اصلاح محافظه‌کارانهٔ واژه‌های ساختاری برچسب (v1.8.0)
# ---------------------------------------------------------------------------
# فقط واژه‌های «ساختاری» پرتکرار برچسب (شکل دارویی، واحد، فعل بسته‌بندی) اصلاح
# می‌شوند؛ نام دارو/برند/ماده مؤثره هرگز خودکار تصحیح نمی‌شود (خط قرمز ایمنی:
# هویت دارو باید دقیقاً همان باشد که موتور OCR خوانده است).
#
# نگاشت: واژه استاندارد → فهرست خوانش‌های غلط رایج تسراکت فارسی.
# منبع خوانش‌ها: آزمون واقعی روی جعبه لانزول و جعبه‌های نمونه پروژه.
_LABEL_WORD_FIXES: dict[str, tuple[str, ...]] = {
    "کپسول": ("کیسول", "کپسو", "کسول", "کیپسول", "کيسول", "سیسول"),
    "انتریک": ("انتریگک", "انتريك", "انتیریک", "انتریکی", "انتریک"),
    "کوتد": ("کوند", "کوتید", "کوتئد", "كوتد", "کوسد"),
    "شربت": ("شربط", "شربت"),
    "آمپول": ("امپول", "آمبول", "امبول"),
    "سوسپانسیون": ("سوسپانشین", "سوسپانسيون"),
    "قطره": ("قطه",),
    "میلی‌گرم": ("میلی گرم", "میلیگرم", "میلی‌كرم", "میلی‌گیرم"),
    "میلی‌لیتر": ("میلی لیتر", "میلیلیتر", "میلی‌لیتر"),
    "میکروگرم": ("میکرو گرم", "میکروگرم"),
    "حاوی": ("هاوی", "حاوي", "حاوی"),
    "تأسیس": ("تاسیس", "تأسيس"),
    "انقضا": ("انقضأ", "انقضاع"),
    "نگهداری": ("نگهداري", "نگهداری"),
}

# حداقل شباهت فازی برای جانشینی (کلمهٔ خوانده‌شده باید به اندازهٔ کافی به
# واژهٔ استاندارد نزدیک باشد؛ با این کار تصحیح تصادفی کلمات دیگر رخ نمی‌دهد)
_LABEL_FIX_SIMILARITY = 0.80

_PUNCT = "\u060c.:؛!؟()«»\u200f\u200e"


def _split_token(tok: str) -> tuple[str, str, str]:
    """تفکیک پیشوند/هسته/پسوند علائم نگارشی یک واژه."""
    stripped_left = tok.lstrip(_PUNCT)
    prefix = tok[:len(tok) - len(stripped_left)]
    core = stripped_left.rstrip(_PUNCT)
    suffix = stripped_left[len(core):]
    return prefix, core, suffix


def fix_common_label_words(text: str) -> tuple[str, list[str]]:
    """اصلاح واژه‌های ساختاری برچسب با نگاشت محدود + شباهت فازی (v1.8.0).

    قواعد:
    - فقط واژه‌های تک‌خطی فارسی (بدون حرف لاتین) بررسی می‌شوند؛
    - تطابق دقیق با خوانش‌های غلط شناخته‌شده (فهرست wrongs) با شباهت ≥ ۰٫۷۵؛
    - یا نزدیک‌ترین واژهٔ استاندارد با شباهت ≥ ۰٫۸۰ (پوشش غلط‌های دیده‌نشده)؛
    - نام دارو/برند در این واژه‌نامه نیست و هرگز تغییر نمی‌کند.
    خروجی: (متن اصلاح‌شده، فهرست اصلاحات به شکل «غلط ← درست»)
    """
    if not text or " " not in text and len(text) < 3:
        return text, []
    import difflib

    fixes: list[str] = []
    out_tokens: list[str] = []
    for tok in text.split(" "):
        prefix, core, suffix = _split_token(tok)
        if not core or len(core) < 3 or \
                any("\u0000" <= ch <= "\u024f" for ch in core):
            out_tokens.append(tok)
            continue
        core_norm = normalize_chars(core)
        if not core_norm:
            out_tokens.append(tok)
            continue
        best_canon, best_sim = None, 0.0
        for canonical, wrongs in _LABEL_WORD_FIXES.items():
            canon_norm = normalize_chars(canonical)
            if core_norm == canon_norm:
                best_canon, best_sim = None, 0.0
                break  # خودِ واژهٔ درست است؛ هیچ تغییری لازم نیست
            if core_norm in wrongs:
                sim = difflib.SequenceMatcher(
                    None, core_norm, canon_norm).ratio()
                if sim >= 0.75 and sim > best_sim:
                    best_canon, best_sim = canonical, sim
            else:
                sim = difflib.SequenceMatcher(
                    None, core_norm, canon_norm).ratio()
                if sim >= _LABEL_FIX_SIMILARITY and sim > best_sim:
                    best_canon, best_sim = canonical, sim
        if best_canon:
            out_tokens.append(prefix + best_canon + suffix)
            fixes.append(f"{core} ← {best_canon}")
        else:
            out_tokens.append(tok)
    return " ".join(out_tokens), fixes

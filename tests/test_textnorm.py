# -*- coding: utf-8 -*-
"""آزمون نرمال‌سازی متن فارسی."""
from label_reader.textnorm import (
    cleaned_display_text, digits_to_persian, is_mostly_latin,
    is_mostly_persian, normalize_chars, normalize_digits_ascii,
    normalize_for_matching,
)


def test_arabic_to_persian_chars():
    assert normalize_chars("\u064a\u0643") == "\u06cc\u06a9"  # يك -> یک


def test_digits_ascii():
    assert normalize_digits_ascii("\u06f5\u06f0\u06f0") == "500"   # ۵۰۰
    assert normalize_digits_ascii("\u0662\u0660") == "20"          # ٢٠ عربی
    assert normalize_digits_ascii("500 mg") == "500 mg"


def test_digits_to_persian_display():
    assert digits_to_persian("500") == "\u06f5\u06f0\u06f0"
    assert digits_to_persian("2027/06") == "\u06f2\u06f0\u06f2\u06f7/\u06f0\u06f6"


def test_zwnj_and_tatweel_in_matching():
    assert normalize_for_matching("\u0645\u06cc\u0644\u06cc\u200c\u06af\u0631\u0645") == \
        "\u0645\u06cc\u0644\u06cc \u06af\u0631\u0645"  # نیم‌فاصله → فاصله
    assert "\u0640" not in normalize_for_matching("abc\u0640def")


def test_whitespace_collapse():
    assert normalize_for_matching("  a   b\tc \n") == "a b c"


def test_no_autocorrect_of_meaning():
    # 0/O و 1/I نباید اصلاح شوند
    assert normalize_for_matching("O1l0") == "O1l0"


def test_language_detection():
    assert is_mostly_persian("\u0627\u0633\u062a\u0627\u0645\u06cc\u0646\u0648\u0641\u0646")
    assert is_mostly_latin("Paracetamol")
    assert not is_mostly_persian("Paracetamol")


def test_cleaned_display_keeps_zwnj():
    out = cleaned_display_text("\u0645\u06cc\u200c\u06af\u0631\u0645")
    assert "\u200c" in out  # نیم‌فاصله در نمایش حفظ می‌شود

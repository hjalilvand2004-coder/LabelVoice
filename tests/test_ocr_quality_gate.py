# -*- coding: utf-8 -*-
"""آزمون‌های v1.7.0: گیت کیفیت قطعه، ادغام بهترین-اول، دروازه نام، هشدار شستگی.

پیشینه: کاربر روی تصویر جعبه کمک‌دستی، خروجی «RIE [SE ۱ ES {= ray WE» و
هشدار کاذب «تصویر بیش از حد روشن» گرفت. این آزمون‌ها جلوی بازگشت آن خطاها
را می‌گیرند.
"""
import pytest

from label_reader.config import Settings
from label_reader.extraction.fields import _plausible_name
from label_reader.models import BoundingBox
from label_reader.ocr.base import OcrRaw
from label_reader.pipeline import LabelReaderPipeline
from label_reader.preprocess import build_variants, white_on_dark


def _raw(text, conf, x, y, w, h, variant="original"):
    return OcrRaw(text=text, confidence=conf, x=x, y=y, w=w, h=h,
                  variant=variant, engine="fake")


class _TinyProvider:
    name = "fake"

    def __init__(self, by_variant):
        self.by_variant = by_variant

    def available(self):
        return True, ""

    def run(self, image_bgr, variant):
        return self.by_variant.get(variant, [])


def _settings():
    s = Settings(_env_file=None)
    s.use_binarized_variant = False
    return s


# ---------- دروازه نام معتبر ----------

def test_plausible_name_rejects_ocr_garbage():
    """خوانش آشغال کاربر هرگز نام نمی‌شود (باگ گزارش‌شده v1.6.0)."""
    assert not _plausible_name("RIE [SE ۱ ES {= ray WE")
    assert not _plausible_name("@ » °")
    assert not _plausible_name("__import__('os').system('echo hacked')")


def test_plausible_name_accepts_real_names():
    assert _plausible_name("MEDICINE")
    assert _plausible_name("استامینوفن")
    assert _plausible_name("Paracetamol")


# ---------- گیت کیفیت قطعه ----------

def test_filter_drops_pure_symbols_and_giant_short_pieces():
    pipe = LabelReaderPipeline(_settings())
    raws = [
        _raw("@", 0.9, 0, 0, 10, 10),          # نماد محض → حذف
        _raw("MEDICINE", 0.96, 0, 0, 400, 90),  # سالم → ماند
        _raw("3", 0.56, 10, 10, 431, 394),      # کوتاه + کادر غول‌پیکر → حذف
    ]
    kept = pipe._filter_pieces(raws, image_area=1000 * 1000)
    texts = [p.text for p in kept]
    assert texts == ["MEDICINE"]


def test_filter_keeps_low_conf_short_unit():
    """واحد معنی‌دار کم‌اطمینان (مثل mg با conf 0.3) حذف نمی‌شود."""
    pipe = LabelReaderPipeline(_settings())
    kept = pipe._filter_pieces([_raw("mg", 0.30, 0, 0, 20, 24)],
                               image_area=1000 * 1000)
    assert [p.text for p in kept] == ["mg"]


# ---------- ادغام بهترین-اول ----------

def test_best_first_merge_prefers_complete_read():
    """خوانش جزئی «CINE» داخل «MEDICINE» ادغام و حذف می‌شود."""
    pipe = LabelReaderPipeline(_settings())
    by_variant = {
        "gray_clahe": [_raw("MEDICINE", 0.96, 348, 247, 418, 125)],
        "binarized": [_raw("CINE", 0.71, 575, 247, 190, 141)],
    }
    pieces = pipe._merge_pieces_best_first(by_variant)
    assert [p.text for p in pieces] == ["MEDICINE"]


def test_merge_partial_junk_does_not_replace_full_word():
    """«DA» با اطمینان بالاتر، جای «BOX» را نمی‌گیرد (متنی غیرمرتبط).

    DA به‌عنوان قطعه جدا می‌ماند (در سطرسازی جدا می‌نشیند) اما هرگز متن
    BOX را بازنویسی نمی‌کند — همان خطای v1.6.0 که نام را خراب می‌کرد.
    """
    pipe = LabelReaderPipeline(_settings())
    by_variant = {
        "white_on_dark": [_raw("BOX", 0.88, 499, 372, 126, 65)],
        "binarized": [_raw("DA", 0.92, 576, 375, 50, 53)],
    }
    pieces = pipe._merge_pieces_best_first(by_variant)
    texts = [p.text for p in pieces]
    assert "BOX" in texts
    assert texts.index("BOX") == 0  # خوانش اصلی دست‌نخورده


def test_merge_text_containment_higher_conf_wins():
    """«MEDICINES» زباله (conf پایین) با «MEDICINE» واقعی جانشین می‌شود."""
    pipe = LabelReaderPipeline(_settings())
    by_variant = {
        "white_on_dark": [_raw("MEDICINES", 0.42, 350, 189, 458, 183)],
        "gray_clahe": [_raw("MEDICINE", 0.96, 348, 247, 418, 125)],
    }
    pieces = pipe._merge_pieces_best_first(by_variant)
    assert [p.text for p in pieces] == ["MEDICINE"]


def test_merge_neighbor_words_not_merged():
    """کلمات همسایه با کادر همپوشان (چیدمان متراکم) یکی نمی‌شوند."""
    pipe = LabelReaderPipeline(_settings())
    by_variant = {
        "original": [
            _raw("__import__('os').system('echo", 0.9, 20, 30, 110, 24),
            _raw("hacked')", 0.9, 140, 30, 80, 24),
        ],
    }
    pieces = pipe._merge_pieces_best_first(by_variant)
    assert len(pieces) == 2


# ---------- هشدار شستگی ----------

def test_white_product_photo_no_false_bright_warning():
    """عکس محصول روی میز روشن هشدار «شسته‌شده» کاذب نمی‌گیرد."""
    import cv2
    import numpy as np
    from label_reader.quality import assess_quality
    # پس‌زمینه روشن (~215) + جعبه تیره + متن — کنتراست سراسری بالا
    img = np.full((400, 400, 3), 215, dtype=np.uint8)
    cv2.rectangle(img, (80, 80), (320, 320), (90, 90, 90), -1)
    cv2.putText(img, "MEDICINE", (100, 200), cv2.FONT_HERSHEY_SIMPLEX,
                1.2, (255, 255, 255), 3)
    _, issues = assess_quality(img, _settings())
    assert all(i.code != "bright" for i in issues)


def test_white_on_dark_variant_builds():
    """واریانت متن-روشن-روی-تیره در build_variants تولید و بزرگ‌نمایی می‌شود.

    v2.10.0: در مسیر قدیمی (conditional_variants=False) همیشه ساخته می‌شود؛
    در مسیر مشروط فقط وقتی پس‌زمینهٔ تیره تشخیص داده شود.
    """
    import numpy as np
    img = np.full((120, 120, 3), 150, dtype=np.uint8)
    s = _settings()
    s.conditional_variants = False
    variants = build_variants(img, s)
    assert "white_on_dark" in variants
    assert variants["white_on_dark"].shape[0] >= img.shape[0]
    assert variants["white_on_dark"].shape[1] >= img.shape[1]
    # مسیر مشروط: خاکستری ۱۵۰ تیرهٔ معتبر نیست (آستانهٔ ۰٫۳۰) ⇒ ساخته نمی‌شود
    s.conditional_variants = True
    assert "white_on_dark" not in build_variants(img, s)


def test_white_on_dark_threshold_keeps_bright_text_as_ink():
    """در white_on_dark: متن روشن جوهر (سفید) و جعبه تیره زمینه (سیه) می‌شود."""
    import cv2
    import numpy as np
    img = np.full((90, 90, 3), 200, dtype=np.uint8)   # میز روشن
    img[15:75, 15:75] = 130                            # جعبه تیره
    img[30:60, 30:60] = 245                            # متن سفید فرضی
    out = white_on_dark(img)
    gray = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
    assert gray[45, 45] == 255   # متن روشن → جوهر
    assert gray[20, 20] == 0     # جعبه تیره → زمینه سیاه (کنتراست برای OCR)

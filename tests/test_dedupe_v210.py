# -*- coding: utf-8 -*-
"""آزمون‌های v2.10.0 — اصلاحات ممیزی مهندسی.

پوشش:
۱) F1 — ایمنی عدد در dedupe: «۵۰» هرگز با «۵۰۰» ادغام نمی‌شود (بدون هندسه)؛
   خوانش جزئی با قرینهٔ هندسی همچنان ادغام می‌شود («2» داخل «B12»).
۲) F2 — حذف دوقلوی سرگردان: دو خوانش هم‌متن مجاور (کادر جدا) ادغام می‌شوند؛
   تکرار واقعی با فاصلهٔ واژگانی معمول و دوقلوی هر دو با رأی تکرارشده
   دست‌نخورده می‌مانند.
۳) F6 — رکورد کامل اجرا در variant_readings (زبان/PSM/ابعاد/زمان/دلیل رد).
۴) شفافیت پردازش مشروط در payload مرحلهٔ OpenCV.
"""
import io

import numpy as np
import pytest
from PIL import Image

from label_reader.config import Settings
from label_reader.models import BoundingBox, OcrPiece
from label_reader.pipeline import LabelReaderPipeline
from label_reader.preprocess import (
    VARIANT_SHADOW_FREE, build_variants_traced,
)
from tests.conftest import FakeOcrProvider


def _piece(text: str, x: int, y: int, w: int, h: int,
           conf: float = 0.9, support: int = 1,
           variant: str = "original") -> OcrPiece:
    return OcrPiece(
        id="", text=text, normalized_text=text,
        bbox=BoundingBox(x=x, y=y, w=w, h=h),
        confidence=conf, variant=variant, engine="fake", support=support,
        vote_variants=[variant] * support,
    )


def _pipe() -> LabelReaderPipeline:
    return LabelReaderPipeline(Settings(_env_file=None),
                               ocr_provider=FakeOcrProvider([]))


# ---------------------------------------------------------------------------
# F1 — ایمنی عدد در dedupe
# ---------------------------------------------------------------------------
class TestNumericSafety:
    def test_50_not_absorbed_by_500(self):
        """«۵۰» و «۵۰۰» دو مقدار متفاوت‌اند؛ بدون قرینهٔ هندسی هر دو می‌مانند."""
        group = [
            _piece("50", 20, 100, 40, 24, conf=0.9),
            _piece("500", 200, 100, 70, 24, conf=0.5),
        ]
        out = LabelReaderPipeline._dedupe_similar_pieces(group)
        texts = {p.text for p in out}
        assert {"50", "500"} <= texts, (
            f"عدد کوتاه حذف/جایگزین شد: {texts}")

    def test_50_replacement_requires_confidence(self):
        """حتی با قرینهٔ هندسی، خوانش کم‌اطمینان جای خوانش پراطمینان را نمی‌گیرد."""
        # کادر هم‌پوشان (قرینهٔ هندسی هست) اما اطمینان خوانش بلندتر خیلی کمتر
        group = [
            _piece("50", 20, 100, 40, 24, conf=0.9),
            _piece("500", 20, 100, 70, 24, conf=0.3),
        ]
        out = LabelReaderPipeline._dedupe_similar_pieces(group)
        assert any(p.text == "50" for p in out)
        assert all(p.confidence >= 0.85 for p in out)

    def test_partial_read_with_geometry_still_merges(self):
        """خوانش جزئی با احتوای فیزیکی همچنان ادغام می‌شود («2» داخل «B12»)."""
        group = [
            _piece("B12", 20, 100, 60, 24, conf=0.9),
            _piece("12", 40, 100, 30, 20, conf=0.6),   # داخل کادر B12
        ]
        out = LabelReaderPipeline._dedupe_similar_pieces(group)
        assert len(out) == 1 and out[0].text == "B12"

    def test_partial_number_with_geometry_merges(self):
        """«50» داخل کادر «500» (خوانش جزئی همان عدد) با هندسه ادغام می‌شود."""
        group = [
            _piece("500", 20, 100, 70, 24, conf=0.7),
            _piece("50", 20, 100, 45, 20, conf=0.6),   # زیرکادر 500
        ]
        out = LabelReaderPipeline._dedupe_similar_pieces(group)
        assert len(out) == 1

    def test_5_and_150_both_kept(self):
        """«5» و «۱۵۰» در یک سطر با کادر مجزا: هر دو حفظ می‌شوند."""
        group = [
            _piece("5", 20, 100, 16, 24, conf=0.9),
            _piece("150", 300, 100, 60, 24, conf=0.8),
        ]
        out = LabelReaderPipeline._dedupe_similar_pieces(group)
        texts = {p.text for p in out}
        assert {"5", "150"} <= texts


# ---------------------------------------------------------------------------
# F2 — حذف دوقلوی سرگردان
# ---------------------------------------------------------------------------
class TestGhostDuplicates:
    def test_ghost_twin_collapsed(self):
        """دو خوانش هم‌متن مجاور (کادر جدا) ادغام می‌شوند — ریشهٔ «Keeping Keeping»."""
        pieces = [
            _piece("Keeping", 100, 100, 70, 20, conf=0.88),
            _piece("Keeping", 174, 101, 68, 20, conf=0.72),  # شکاف 4 ≤ 0.3×20
            _piece("Bones", 260, 100, 60, 20, conf=0.9),
        ]
        removed = _pipe()._collapse_location_duplicates(pieces)
        assert removed == 1
        texts = [p.text for p in pieces]
        assert texts.count("Keeping") == 1
        # قوی‌تر می‌ماند
        kept = [p for p in pieces if p.text == "Keeping"][0]
        assert abs(kept.confidence - 0.88) < 1e-9

    def test_real_repeated_words_kept(self):
        """تکرار واقعی روی برچسب (فاصلهٔ واژگانی معمول) حذف نمی‌شود."""
        pieces = [
            _piece("Bones", 100, 100, 60, 20, conf=0.9, support=2),
            _piece("Bones", 260, 100, 60, 20, conf=0.9, support=2),  # شکاف 100
        ]
        removed = _pipe()._collapse_location_duplicates(pieces)
        assert removed == 0 and len(pieces) == 2

    def test_both_supported_twins_kept(self):
        """اگر هر دو رأی تکرارشده (support≥2) دارند، تکرار واقعی تلقی می‌شوند."""
        pieces = [
            _piece("Strong", 100, 100, 60, 20, conf=0.9, support=2),
            _piece("Strong", 170, 100, 60, 20, conf=0.9, support=2),
        ]
        removed = _pipe()._collapse_location_duplicates(pieces)
        assert removed == 0 and len(pieces) == 2

    def test_different_rows_not_merged(self):
        """هم‌متن در دو سطر مختلف (اختلاف y بزرگ) ادغام نمی‌شود."""
        pieces = [
            _piece("Mg", 100, 100, 40, 20, conf=0.9),
            _piece("Mg", 100, 300, 40, 20, conf=0.9),
        ]
        removed = _pipe()._collapse_location_duplicates(pieces)
        assert removed == 0 and len(pieces) == 2

    def test_flag_off_keeps_everything(self):
        """با فلگ خاموش (مسیر قدیمی) هیچ ادغامی انجام نمی‌شود."""
        s = Settings(_env_file=None)
        s.dedupe_ghost_duplicates = False
        pipe = LabelReaderPipeline(s, ocr_provider=FakeOcrProvider([]))
        pieces = [
            _piece("Keeping", 100, 100, 70, 20, conf=0.88),
            _piece("Keeping", 174, 101, 68, 20, conf=0.72),
        ]
        assert pipe._collapse_location_duplicates(pieces) == 0
        assert len(pieces) == 2

    def test_line_no_more_word_doubling(self):
        """سناریوی گزارش‌شده: خط نهایی «Keeping Bones Strong» است نه دوبرابر."""
        pipe = _pipe()
        pieces = [
            _piece("Keeping", 100, 100, 70, 20, conf=0.88),
            _piece("Keeping", 174, 101, 68, 20, conf=0.72),
            _piece("Bones", 260, 100, 60, 20, conf=0.9),
            _piece("Strong", 330, 100, 62, 20, conf=0.85),
        ]
        pipe._collapse_location_duplicates(pieces)
        lines = pipe._build_lines(pieces)
        assert len(lines) == 1
        words = lines[0].text.split()
        assert words == ["Keeping", "Bones", "Strong"], lines[0].text


# ---------------------------------------------------------------------------
# F6 — رکورد کامل اجرا در خوانش خام
# ---------------------------------------------------------------------------
def _png_bytes() -> bytes:
    import io
    buf = io.BytesIO()
    Image.new("RGB", (640, 420), (240, 244, 248)).save(buf, "PNG")
    return buf.getvalue()


def test_variant_readings_have_full_run_record():
    """هر رکورد خوانش خام باید زمان اجرا و تفکیک دلیل رد داشته باشد."""
    pipe = LabelReaderPipeline(Settings(_env_file=None), ocr_provider=FakeOcrProvider(
        [("Paracetamol", 0.9), ("500 mg", 0.9)]))
    result = pipe.process_bytes(_png_bytes())
    readings = result.metadata  # فقط برای اطمینان از اجرا
    assert readings is not None
    pipe2 = LabelReaderPipeline(Settings(_env_file=None), ocr_provider=FakeOcrProvider(
        [("Paracetamol", 0.9), ("500 mg", 0.9)]))
    payloads: dict = {}
    pipe2.process_pil(Image.open(io.BytesIO(_png_bytes())),
                      stage_callback=lambda k, p: payloads.__setitem__(k, p))
    for r in payloads["ocr"]["variant_readings"]:
        assert "langs" in r and "psm_list" in r
        assert "input_dims" in r and "duration_ms" in r
        assert "raw_pieces" in r and "drop_reasons" in r
        assert isinstance(r["drop_reasons"], dict)


def test_ghost_count_reported_in_ocr_stage():
    """شمار دوقلوی حذف‌شده در payload مرحلهٔ OCR اعلام می‌شود."""
    pipe = LabelReaderPipeline(Settings(_env_file=None), ocr_provider=FakeOcrProvider(
        [("Keeping Bones Strong", 0.9)]))
    payloads: dict = {}
    pipe.process_pil(Image.open(io.BytesIO(_png_bytes())),
                     stage_callback=lambda k, p: payloads.__setitem__(k, p))
    assert "ghost_duplicates_removed" in payloads["ocr"]
    assert payloads["ocr"]["ghost_duplicates_removed"] >= 0


# ---------------------------------------------------------------------------
# شفافیت پردازش مشروط در payload مرحلهٔ OpenCV
# ---------------------------------------------------------------------------
def test_conditional_skips_in_opencv_payload():
    pipe = LabelReaderPipeline(Settings(_env_file=None), ocr_provider=FakeOcrProvider([]))
    payloads: dict = {}
    pipe.process_pil(Image.open(io.BytesIO(_png_bytes())),
                     stage_callback=lambda k, p: payloads.__setitem__(k, p))
    ov = payloads["opencv"]
    assert "conditional_skips" in ov and "diagnostics" in ov
    names = {s["variant"] for s in ov["conditional_skips"]}
    assert "white_on_dark" in names  # پس‌زمینهٔ روشن فیکسچر
    assert "shadow_free" in names
    for s in ov["conditional_skips"]:
        assert s["reason_fa"]


def test_legacy_flag_builds_all_variants():
    """فلگ بازگشت: LBR_CONDITIONAL_VARIANTS=0 ⇒ همهٔ واریانت‌ها مثل قبل ساخته می‌شوند."""
    s = Settings(_env_file=None)
    s.conditional_variants = False
    img = np.full((120, 120, 3), 150, dtype=np.uint8)
    variants, _trace = build_variants_traced(img, s, collect_trace=False)
    for name in ("original", "gray_clahe", "shadow_free", "sharpened",
                 "white_on_dark", "ink_isolated"):
        assert name in variants, f"مسیر قدیمی باید «{name}» را بسازد"


def test_shadow_free_built_only_for_shadowed_image():
    """سنجهٔ سایه: تصویر سایه‌دار shadow_free می‌گیرد، تصویر یکنواخت نمی‌گیرد."""
    flat = np.full((200, 300, 3), 235, dtype=np.uint8)
    assert VARIANT_SHADOW_FREE not in build_variants_traced(
        flat, Settings(_env_file=None), collect_trace=False)[0]
    grad = np.tile(np.linspace(120, 255, 300, dtype=np.uint8), (200, 1))
    shadowed = np.stack([grad] * 3, axis=-1)
    assert VARIANT_SHADOW_FREE in build_variants_traced(
        shadowed, Settings(_env_file=None), collect_trace=False)[0]

# -*- coding: utf-8 -*-
"""آزمون‌های اجزای خط پردازش — به‌روز برای معماری v2.x.

نسخه‌های قدیمی (تا ۱.۶) این فایل به StageRecord/stage_report و توابع کمکی
حذف‌شده (_arabic_script_fraction و…) وابسته بودند؛ از v2.0 مراحل به‌صورت
زنده با stage_callback اعلام می‌شوند (label_reader/stages.py) و شفافیت
گام‌به‌گام OpenCV در tests/test_stage_trace.py پوشش داده می‌شود.
"""
from __future__ import annotations

import numpy as np
import pytest
from PIL import Image, ImageDraw

from label_reader.config import Settings
from label_reader.preprocess import (
    VARIANT_WHITE_ON_DARK, build_variants, build_variants_traced, white_on_dark,
)
from label_reader.pipeline import LabelReaderPipeline
from label_reader.quality import assess_quality
from label_reader.textnorm import is_mostly_persian


def _settings() -> Settings:
    s = Settings(_env_file=None)
    s.target_min_side = 300  # سریع برای آزمون
    s.use_binarized_variant = False
    return s


def _label_image() -> Image.Image:
    """برچسب مصنوعی ساده با متن سفید روی زمینه آبی."""
    img = Image.new("RGB", (640, 420), (90, 140, 175))
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, 600, 380], fill=(70, 120, 155))
    d.text((120, 120), "MEDICINE", fill="white")
    d.text((180, 200), "BOX 20 mg", fill="white")
    return img


def test_white_on_dark_three_channel_and_variant_added():
    """نسخهٔ «متن روشن روی زمینهٔ تیره» سه‌کاناله است و در واریانت‌ها هست.

    v2.10.0: مسیر قدیمی (ساخت همیشگی) با فلگ آزموده می‌شود؛ در مسیر مشروط
    برچسب سفید، این واریانت با دلیل ساخته نمی‌شود.
    """
    bgr = np.asarray(_label_image())[:, :, ::-1].copy()
    s = _settings()
    out = white_on_dark(bgr)
    assert out.ndim == 3 and out.shape[2] == 3
    assert out.shape[:2] == bgr.shape[:2]
    s.conditional_variants = False
    variants = build_variants(bgr, s)
    assert VARIANT_WHITE_ON_DARK in variants
    assert variants[VARIANT_WHITE_ON_DARK].shape[:2] == variants["original"].shape[:2]
    # مسیر مشروط: برچسب با زمینهٔ روشن ⇒ این واریانت ساخته نمی‌شود
    s.conditional_variants = True
    skipped: list = []
    variants_c, _ = build_variants_traced(bgr, s, collect_trace=False,
                                          skipped_out=skipped)
    assert VARIANT_WHITE_ON_DARK not in variants_c
    assert any(sk["variant"] == VARIANT_WHITE_ON_DARK and sk["reason_fa"]
               for sk in skipped)


def test_no_false_bright_warning_on_light_scene():
    """پس‌زمینه روشن صحنه نباید هشدار «بیش‌نور» بدهد (باگ واقعی کاربر)."""
    img = Image.new("RGB", (600, 600), (208, 208, 206))
    d = ImageDraw.Draw(img)
    d.rectangle([140, 110, 460, 490], fill=(72, 122, 158))  # بسته آبی
    bgr = np.asarray(img)[:, :, ::-1].copy()
    s = _settings()
    _, issues = assess_quality(bgr, s)
    assert not any(i.code == "bright" for i in issues)


def test_mixed_script_garbage_and_persian_detection():
    """نگهبان ترکیب‌خطی (v1.8.0) و تشخیص سطر فارسی — API فعلی."""
    assert is_mostly_persian("استامینوفن 500")
    assert not is_mostly_persian("MEDICINE BOX")
    assert not is_mostly_persian("۱۲۳")  # فقط رقم؛ حرفی وجود ندارد

    cls = LabelReaderPipeline
    # حرف فارسی + حرف لاتین در «یک قطعه» = زبالهٔ خوانش
    assert cls._is_mixed_script_garbage("کپسولSy")
    # رقم فارسی + رقم لاتین = زباله
    assert cls._is_mixed_script_garbage("44۵")
    # رقم لاتین با حرف فارسی مجاز است (خروجی رایج موتورها)
    assert not cls._is_mixed_script_garbage("30 میلی‌گرم")
    assert not cls._is_mixed_script_garbage("MEDICINE")


def test_stage_emission_live_pipeline():
    """خط کامل با OCR ساختگی → ۴ مرحلهٔ اعلام‌شده + مسیر OpenCV در payload."""
    from tests.conftest import FakeOcrProvider

    s = _settings()
    pipe = LabelReaderPipeline(
        s, ocr_provider=FakeOcrProvider(
            [("MEDICINE", 0.9), ("BOX 20 mg", 0.85)]))
    payloads: dict = {}

    def cb(key, payload):
        payloads[key] = payload

    result = pipe.process_pil(_label_image(), stage_callback=cb)
    assert list(payloads.keys()) == ["opencv", "ocr", "fields", "response"]

    ov = payloads["opencv"]
    trace = ov["opencv_trace"]
    assert trace and isinstance(trace[0]["image_bgr"], np.ndarray)
    assert all(e.get("title_fa") and e.get("desc_fa") for e in trace)
    # گام اول همیشه «تصویر ورودی» است (مبنای مقایسهٔ قبل/بعد)
    assert trace[0]["step"] == "input"
    assert {"original", "gray_clahe"} <= set(ov["variants"])
    assert ov["quality_before"]["sharpness"] >= 0

    # v2.10.0: مقایسه با نسخهٔ واقعی بسته — رشتهٔ ثابت با هر bump نسخه می‌شکست
    from label_reader import __version__ as _pkg_version
    assert result.metadata.app_version == _pkg_version
    assert result.response_fa

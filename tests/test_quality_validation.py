# -*- coding: utf-8 -*-
"""آزمون اعتبارسنجی تصویر، کیفیت و پیش‌پردازش."""
import io

import numpy as np
import pytest
from PIL import Image

from label_reader.config import Settings
from label_reader.preprocess import build_variants, crop_fraction
from label_reader.quality import assess_quality
from label_reader.validation import (
    ImageValidationError, sniff_format, validate_and_load)


def _png_bytes(size=(900, 620), color=(255, 255, 255)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


def _settings() -> Settings:
    return Settings(_env_file=None)


def test_sniff_format():
    assert sniff_format(_png_bytes()) == "PNG"
    assert sniff_format(b"\x00\x00\x00fake") is None


def test_reject_unsupported_format():
    with pytest.raises(ImageValidationError) as exc:
        validate_and_load(b"GIF89a" + b"\x00" * 100,
                          max_file_mb=10, max_pixels=30_000_000)
    assert "مجاز" in exc.value.message_fa


def test_reject_oversize_file():
    with pytest.raises(ImageValidationError) as exc:
        validate_and_load(_png_bytes(), max_file_mb=0, max_pixels=30_000_000)
    assert "حجم" in exc.value.message_fa or "مجاز" in exc.value.message_fa


def test_reject_too_many_pixels():
    settings = _settings()
    settings.max_pixels = 1000
    with pytest.raises(ImageValidationError) as exc:
        validate_and_load(_png_bytes((500, 500)),
                          max_file_mb=settings.max_file_mb,
                          max_pixels=settings.max_pixels)
    assert "پیکسل" in exc.value.message_fa


def test_exif_orientation_applied():
    img = Image.new("RGB", (200, 100), "white")
    exif = img.getexif()
    exif[274] = 6  # orientation: rotate 90
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif)
    loaded = validate_and_load(buf.getvalue(), max_file_mb=10,
                               max_pixels=30_000_000)
    assert loaded.size == (100, 200)


def test_sharp_white_label_quality_ok():
    """برچسب سفید تمیز نباید انعکاس/روشنایی بیش‌ازحد بگیرد."""
    img = Image.new("RGB", (900, 620), "white")
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    d.text((60, 60), "Paracetamol 500 mg", fill="black")
    bgr = np.asarray(img)[:, :, ::-1].copy()
    metrics, issues = assess_quality(bgr, _settings())
    codes = {i.code for i in issues}
    assert "glare" not in codes
    assert "bright" not in codes


def test_blurry_detection():
    img = Image.new("RGB", (900, 620), (200, 200, 200))
    from PIL import ImageFilter, ImageDraw
    d = ImageDraw.Draw(img)
    d.text((60, 60), "Paracetamol 500 mg", fill="black")
    img = img.filter(ImageFilter.GaussianBlur(12))
    bgr = np.asarray(img)[:, :, ::-1].copy()
    _, issues = assess_quality(bgr, _settings())
    codes = {i.code for i in issues}
    assert "blurry" in codes
    blurry = [i for i in issues if i.code == "blurry"][0]
    assert "دوربین را ثابت" in blurry.message_fa


def test_dark_detection():
    img = Image.new("RGB", (900, 620), (20, 20, 20))
    bgr = np.asarray(img)[:, :, ::-1].copy()
    _, issues = assess_quality(bgr, _settings())
    assert any(i.code == "dark" for i in issues)


def test_glare_on_middtone():
    img = Image.new("RGB", (900, 620), (210, 210, 210))
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    d.rectangle([500, 50, 880, 400], fill=(255, 255, 255))
    bgr = np.asarray(img)[:, :, ::-1].copy()
    _, issues = assess_quality(bgr, _settings())
    assert any(i.code == "glare" for i in issues)


def test_variants_shapes_and_original_kept():
    img = Image.new("RGB", (640, 400), "white")
    bgr = np.asarray(img)[:, :, ::-1].copy()
    settings = _settings()
    settings.target_min_side = 300  # بدون بزرگ‌نمایی برای این آزمون
    variants = build_variants(bgr, settings)
    assert "original" in variants
    assert "gray_clahe" in variants
    assert variants["original"].shape[:2] == (400, 640)


def test_small_image_upscaled():
    img = Image.new("RGB", (640, 400), "white")
    bgr = np.asarray(img)[:, :, ::-1].copy()
    variants = build_variants(bgr, _settings())
    # کوچک‌ترین ضلع به target_min_side (پیش‌فرض 1000) می‌رسد
    assert min(variants["original"].shape[:2]) >= 1000


def test_crop_fraction():
    img = np.zeros((400, 600, 3), dtype=np.uint8)
    out = crop_fraction(img, (0.5, 0.5, 0.5, 0.5))
    assert out.shape[:2] == (200, 300)


def test_crop_full_returns_same():
    img = np.zeros((400, 600, 3), dtype=np.uint8)
    out = crop_fraction(img, (0, 0, 1.0, 1.0))
    assert out.shape[:2] == (400, 600)

# -*- coding: utf-8 -*-
"""آزمون‌های موتور سوم اختیاری Surya (v2.2.0).

آزمون استنتاج زندهٔ سنگین فقط با متغیر محیطی LBR_TEST_SURYA_LIVE=1 اجرا
می‌شود (بار اول وزن مدل‌ها را دانلود می‌کند و رم زیاد می‌خواهد).
"""
import os

import numpy as np
import pytest

from label_reader.config import Settings, load_settings
from label_reader.models_info import MODEL_REGISTRY, detect_versions
from label_reader.ocr import make_provider
from label_reader.ocr.base import OcrProvider, OcrUnavailableError
from label_reader.ocr.surya_provider import SuryaProvider


def _surya_installed() -> bool:
    try:
        import surya  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def test_surya_registered_in_factory():
    from label_reader.ocr import _PROVIDERS
    assert "surya" in _PROVIDERS
    assert _PROVIDERS["surya"] is SuryaProvider


def test_surya_provider_interface():
    settings = load_settings()
    provider = SuryaProvider(settings)
    assert isinstance(provider, OcrProvider)
    assert provider.name == "surya"
    ok, hint = provider.available()
    assert isinstance(ok, bool)
    assert isinstance(hint, str)


def test_surya_unknown_engine_rejected():
    settings = Settings(_env_file=None)
    with pytest.raises(OcrUnavailableError):
        make_provider("nonexistent-engine", settings)


def test_surya_config_fields():
    settings = Settings(_env_file=None)
    assert settings.ocr_provider == "tesseract"  # پیش‌فرض دست‌نخورده
    assert "surya" not in ("tesseract", "easyocr")
    assert settings.surya_variants == "original,gray_clahe"
    assert settings.surya_model_dir is None


def test_surya_in_model_registry():
    rows = [m["model"] for m in MODEL_REGISTRY if m["runtime"] == "surya"]
    assert rows, "Surya row missing from MODEL_REGISTRY"
    assert any("Surya" in r for r in rows)
    # ردیف اختیاری است
    row = next(m for m in MODEL_REGISTRY if m["runtime"] == "surya")
    assert row["optional"] is True


def test_surya_version_detection_never_crashes():
    ver = detect_versions()
    assert "surya" in ver
    assert isinstance(ver["surya"], str)


def test_auto_chain_excludes_surya():
    """auto نباید سوریا را انتخاب کند (پیش‌فرض سریع و پیش‌بینی‌پذیر)."""
    from label_reader.ocr import make_provider as mp
    settings = Settings(_env_file=None)
    try:
        provider = mp("auto", settings)
        assert provider.name in ("tesseract", "easyocr")
    except OcrUnavailableError:
        pytest.skip("هیچ موتور OCR پایه‌ای در این محیط نصب نیست")


@pytest.mark.skipif(os.environ.get("LBR_TEST_SURYA_LIVE") != "1",
                    reason="استنتاج زندهٔ سنگین — فقط با LBR_TEST_SURYA_LIVE=1")
def test_surya_live_inference():
    """دودآزمایی واقعی روی برچسب مصنوعی (رم ~۴GB؛ بار اول دانلود مدل)."""
    if not _surya_installed():
        pytest.skip("surya-ocr نصب نیست")
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (1000, 400), "#ffffff")
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(
        "/usr/share/fonts/truetype/freefont/FreeSerif.ttf", 48)
    d.text((960, 60), "لانسوپرازول", font=font, fill="#12283d", anchor="ra")
    d.text((960, 160), "Lansoprazole 30 mg", font=font, fill="#455a64",
           anchor="ra")
    bgr = np.array(img)[:, :, ::-1].copy()

    provider = make_provider("surya", load_settings())
    pieces = provider.run(bgr, "original")
    assert pieces, "surya returned no pieces"
    joined = " ".join(p.text for p in pieces)
    assert ("لانسو" in joined) or ("Lansoprazole" in joined)

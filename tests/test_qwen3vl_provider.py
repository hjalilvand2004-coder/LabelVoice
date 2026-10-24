# -*- coding: utf-8 -*-
"""آزمون‌های موتور چهارم قابل انتخاب Qwen3-VL (v2.3.0).

آزمون استنتاج زندهٔ سنگین فقط با متغیر محیطی LBR_TEST_VLM_LIVE=1 اجرا
می‌شود (بار اول مدل ~۴-۵ گیگابایتی دانلود می‌کند) — به‌صورت پیش‌فرض
فقط ساختار و آداپتور رابط با mock آزموده می‌شود.
"""
import os

import numpy as np
import pytest

from label_reader.config import Settings, load_settings
from label_reader.models_info import MODEL_REGISTRY, vlm_available
from label_reader.ocr import make_provider
from label_reader.ocr.base import OcrProvider, OcrUnavailableError
from label_reader.ocr.vlm_provider import QwenVlmProvider, VLM_MODEL_ID


def test_qwen3vl_registered_in_factory():
    from label_reader.ocr import _PROVIDERS
    assert "qwen3-vl" in _PROVIDERS
    assert _PROVIDERS["qwen3-vl"] is QwenVlmProvider


def test_qwen3vl_provider_interface():
    settings = load_settings()
    provider = QwenVlmProvider(settings)
    assert isinstance(provider, OcrProvider)
    assert provider.name == "qwen3-vl"
    assert provider.model_id == VLM_MODEL_ID
    ok, hint = provider.available()
    assert isinstance(ok, bool)
    assert isinstance(hint, str)


def test_qwen3vl_factory_accepts_engine_choice():
    """make_provider باید «qwen3-vl» را به‌عنوان انتخاب کاربر بپذیرد."""
    settings = Settings(_env_file=None)
    ok, _ = vlm_available()
    if not ok:
        pytest.skip("transformers نصب نیست — انتخاب qwen3-vl graceful رد می‌شود")
    provider = make_provider("qwen3-vl", settings)
    assert provider.name == "qwen3-vl"


def test_qwen3vl_run_adapter_mocked():
    """رابط run() خروجی read_lines را به OcrRaw تبدیل می‌کند (بدون دانلود مدل)."""
    settings = Settings(_env_file=None)
    provider = QwenVlmProvider(settings)
    fake_lines = [
        {"text": "لانسوپرازول", "confidence": 0.60},
        {"text": "۳۰ میلی‌گرم", "confidence": 0.60},
        {"text": "۲۸ کپسول", "confidence": 0.60},
    ]
    provider.read_lines = lambda image_bgr: fake_lines  # noqa: A001
    image = np.zeros((10, 10, 3), dtype=np.uint8)
    pieces = provider.run(image, "original")
    assert len(pieces) == 3
    assert all(p.engine == "qwen3-vl" for p in pieces)
    assert all(p.variant == "original" for p in pieces)
    assert [p.text for p in pieces] == ["لانسوپرازول", "۳۰ میلی‌گرم", "۲۸ کپسول"]
    assert all(p.confidence == pytest.approx(0.60) for p in pieces)
    assert all((p.x, p.y, p.w, p.h) == (0, 0, 0, 0) for p in pieces)


def test_qwen3vl_config_fields():
    settings = Settings(_env_file=None)
    assert settings.ocr_provider == "tesseract"  # پیش‌فرض دست‌نخورده
    assert settings.vlm_variants == "original"
    assert settings.vlm_assist is False


def test_qwen3vl_in_model_registry():
    rows = [m for m in MODEL_REGISTRY if m["runtime"] == "qwen3-vl"]
    assert rows, "qwen3-vl row missing from MODEL_REGISTRY"
    assert any(VLM_MODEL_ID in m["model"] for m in rows)
    assert rows[0]["optional"] is True


def test_qwen3vl_models_table_never_crashes():
    from label_reader.models_info import models_table_rows
    rows = models_table_rows()
    qrows = [r for r in rows if "qwen3-vl" in str(r.get("محل پیاده‌سازی", ""))
             or "Qwen3-VL" in str(r.get("مدل / موتور", ""))]
    assert qrows, "جدول مدل‌ها باید سطر Qwen3-VL داشته باشد"


def test_auto_chain_excludes_qwen3vl():
    """auto نباید qwen3-vl را انتخاب کند (پیش‌فرض سریع و پیش‌بینی‌پذیر)."""
    settings = Settings(_env_file=None)
    provider = make_provider("auto", settings)
    assert provider.name in ("tesseract", "easyocr")


@pytest.mark.skipif(os.environ.get("LBR_TEST_VLM_LIVE") != "1",
                    reason="استنتاج زنده سنگین است؛ فقط با LBR_TEST_VLM_LIVE=1")
def test_qwen3vl_live_read():
    settings = Settings(_env_file=None)
    provider = make_provider("qwen3-vl", settings)
    image = np.full((240, 320, 3), 255, dtype=np.uint8)
    pieces = provider.run(image, "original")
    assert isinstance(pieces, list)

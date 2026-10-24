# -*- coding: utf-8 -*-
"""کارخانه انتخاب ارائه‌دهنده OCR (قابل تعویض از پیکربندی)."""
from __future__ import annotations

from ..config import Settings
from .base import OcrProvider, OcrUnavailableError
from .easyocr_provider import EasyOcrProvider
from .surya_provider import SuryaProvider
from .tesseract_provider import TesseractProvider
from .vlm_provider import QwenVlmProvider

_PROVIDERS = {
    "tesseract": TesseractProvider,
    "easyocr": EasyOcrProvider,
    "surya": SuryaProvider,
    # v2.3.0: موتور چهارم قابل انتخاب — Qwen/Qwen3-VL-2B-Instruct
    "qwen3-vl": QwenVlmProvider,
}


def make_provider(name: str, settings: Settings) -> OcrProvider:
    """ساخت ارائه‌دهنده؛ در صورت نبود وابستگی خطای شفاف با راهنمای فارسی."""
    key = (name or "").strip().lower()
    if key == "auto":
        for candidate in ("tesseract", "easyocr"):
            provider = _PROVIDERS[candidate](settings)
            ok, _ = provider.available()
            if ok:
                return provider
        raise OcrUnavailableError(
            "هیچ موتور OCR در دسترس نیست. راهنمای نصب: docs/INSTALL.md")
    cls = _PROVIDERS.get(key)
    if cls is None:
        raise OcrUnavailableError(
            f"موتور OCR ناشناخته است: {name} "
            f"(گزینه‌ها: tesseract، easyocr، surya، qwen3-vl، auto)")
    provider = cls(settings)
    ok, hint = provider.available()
    if not ok:
        raise OcrUnavailableError(hint)
    return provider

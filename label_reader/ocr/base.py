# -*- coding: utf-8 -*-
"""رابط مشترک ارائه‌دهنده‌های OCR — مستقل و قابل تعویض."""
from __future__ import annotations

import abc

import numpy as np


class OcrRaw:
    """خروجی خام یک قطعه متن از موتور OCR."""

    __slots__ = ("text", "confidence", "x", "y", "w", "h", "variant", "engine")

    def __init__(self, text: str, confidence: float | None,
                 x: int, y: int, w: int, h: int,
                 variant: str, engine: str):
        self.text = text
        self.confidence = confidence
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.variant = variant
        self.engine = engine


class OcrProvider(abc.ABC):
    """هر موتور OCR این رابط را پیاده‌سازی می‌کند."""

    name: str = "base"

    @abc.abstractmethod
    def available(self) -> tuple[bool, str]:
        """(در دسترس است؟، راهنمای نصب فارسی در صورت نبود)"""

    @abc.abstractmethod
    def run(self, image_bgr: np.ndarray, variant: str) -> list[OcrRaw]:
        """اجرای OCR روی یک نسخه تصویر و بازگشت قطعات متن با مختصات."""


class OcrUnavailableError(RuntimeError):
    def __init__(self, message_fa: str):
        super().__init__(message_fa)
        self.message_fa = message_fa

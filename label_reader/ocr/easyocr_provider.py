# -*- coding: utf-8 -*-
"""ارائه‌دهنده OCR مبتنی بر EasyOCR (fa+en) — سنگین‌تر اما عمیق‌تر.

نکات صادقانه:
- بارگذاری اول نیازمند دانلود مدل‌ها (تشخیص + بازشناسی) است؛ چند صد مگابایت
  در سمت کاربر ذخیره می‌شود (پیش‌فرض ~/.EasyOCR یا مسیر تنظیم‌شده).
- اولین بارگذاری کند است؛ نمونه (Reader) به‌صورت Singleton نگه داشته می‌شود.
- این ماژول lazy import می‌کند؛ نبود easyocr مسیر اصلی را نمی‌شکند.
"""
from __future__ import annotations

import threading

import numpy as np

from ..config import Settings
from .base import OcrProvider, OcrRaw

INSTALL_HINT_FA = (
    "easyocr نصب نیست. نصب: «pip install torch torchvision --index-url "
    "https://download.pytorch.org/whl/cpu» و سپس «pip install easyocr». "
    "اولین اجرا مدل‌ها را دانلود می‌کند (نیازمند اینترنت)."
)

_READER = None
_READER_LOCK = threading.Lock()


def _get_reader(settings: Settings):
    global _READER
    with _READER_LOCK:
        if _READER is None:
            import easyocr  # lazy

            kwargs = {}
            if settings.easyocr_model_dir is not None:
                path = str(settings.easyocr_model_dir)
                kwargs.update(
                    model_storage_directory=path,
                    user_network_directory=path,
                    download_enabled=True,
                )
            _READER = easyocr.Reader(["fa", "en"], gpu=False, **kwargs)
        return _READER


class EasyOcrProvider(OcrProvider):
    name = "easyocr"

    def __init__(self, settings: Settings):
        self.settings = settings
        self._import_ok = True
        try:
            import easyocr  # noqa: F401
        except Exception:
            self._import_ok = False

    def available(self) -> tuple[bool, str]:
        return (True, "") if self._import_ok else (False, INSTALL_HINT_FA)

    def run(self, image_bgr: np.ndarray, variant: str) -> list[OcrRaw]:
        if not self._import_ok:
            raise RuntimeError(INSTALL_HINT_FA)
        reader = _get_reader(self.settings)
        results = reader.readtext(
            image_bgr, detail=1, paragraph=False, text_threshold=0.5)
        pieces: list[OcrRaw] = []
        for quad, text, conf in results:
            text = (text or "").strip()
            if not text:
                continue
            xs = [int(p[0]) for p in quad]
            ys = [int(p[1]) for p in quad]
            x0, y0 = max(0, min(xs)), max(0, min(ys))
            x1, y1 = max(xs), max(ys)
            pieces.append(OcrRaw(
                text=text,
                confidence=float(conf),
                x=x0, y=y0, w=max(1, x1 - x0), h=max(1, y1 - y0),
                variant=variant,
                engine=self.name,
            ))
        return pieces

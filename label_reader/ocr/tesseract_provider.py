# -*- coding: utf-8 -*-
"""ارائه‌دهنده OCR مبتنی بر Tesseract (pytesseract) با پشتیبانی fas+eng.

داده زبان فارسی (fas.traineddata) از پوشه models/tessdata پروژه خوانده می‌شود؛
در صورت نبود آن، فقط eng فعال می‌شود و صادقانه به کاربر اعلام می‌گردد
(پشتیبانی فارسی بدون داده واقعی ادعا نمی‌شود).
"""
from __future__ import annotations

import shutil
from pathlib import Path

import cv2
import numpy as np
import pytesseract

from ..config import Settings
from .base import OcrProvider, OcrRaw

INSTALL_HINT_FA = (
    "Tesseract نصب نیست. راهنما: در Ubuntu «sudo apt install tesseract-ocr»، "
    "در Windows نصب‌کننده UB-Mannheim، در macOS «brew install tesseract»."
)
FAS_HINT_FA = (
    "داده زبان فارسی fas.traineddata در models/tessdata یافت نشد؛ "
    "اسکریپت scripts/download_tessdata.py را اجرا کنید تا خواندن فارسی فعال شود."
)


class TesseractProvider(OcrProvider):
    name = "tesseract"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.tessdata_dir: Path = Path(settings.tessdata_dir)
        self._langs = settings.ocr_languages

    def available(self) -> tuple[bool, str]:
        if shutil.which("tesseract") is None:
            return False, INSTALL_HINT_FA
        if self.tessdata_dir.exists() and (self.tessdata_dir / "fas.traineddata").exists():
            self._langs = "fas+eng"
        elif self.tessdata_dir.exists() and (self.tessdata_dir / "eng.traineddata").exists():
            self._langs = "eng"
        # اگر مسیر محلی نبود، از نصب سیستمی استفاده می‌شود
        return True, FAS_HINT_FA if self._langs == "eng" else ""

    def _tess_config(self, psm: int) -> str:
        cfg = f"--psm {int(psm)}"
        if self.tessdata_dir.exists():
            cfg += f' --tessdata-dir "{self.tessdata_dir}"'
        return cfg

    def run(self, image_bgr: np.ndarray, variant: str) -> list[OcrRaw]:
        ok, hint = self.available()
        if not ok:
            raise RuntimeError(hint)
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        psms = [self.settings.tesseract_psm]
        extra = int(self.settings.tesseract_extra_psm or 0)
        if extra and extra != self.settings.tesseract_psm:
            psms.append(extra)
        sparse = int(self.settings.tesseract_sparse_psm or 0)
        if sparse and sparse not in psms:
            # PSM 11 (پراکنده) برای برچسب‌هایی با چند بلوک متن جدا از هم حیاتی است
            psms.append(sparse)
        pieces: list[OcrRaw] = []
        for psm in psms:
            data = pytesseract.image_to_data(
                rgb,
                lang=self._langs,
                config=self._tess_config(psm),
                output_type=pytesseract.Output.DICT,
            )
            n = len(data["text"])
            for i in range(n):
                text = (data["text"][i] or "").strip()
                if not text:
                    continue
                conf = data["conf"][i]
                conf_f: float | None
                try:
                    conf_val = float(conf)
                    conf_f = None if conf_val < 0 else conf_val / 100.0
                except (TypeError, ValueError):
                    conf_f = None
                pieces.append(OcrRaw(
                    text=text,
                    confidence=conf_f,
                    x=int(data["left"][i]),
                    y=int(data["top"][i]),
                    w=int(data["width"][i]),
                    h=int(data["height"][i]),
                    variant=variant,
                    engine=self.name,
                ))
        return pieces

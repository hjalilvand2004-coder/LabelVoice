# -*- coding: utf-8 -*-
"""ارائه‌دهنده OCR مبتنی بر Tesseract (pytesseract) — v1.8.0 گذرهای زبانی جدا.

یافتهٔ کلیدی v1.8.0 (ریشه‌یابی خروجی آشغال فارسی):
    اجرای «fas+eng» ترکیبی باعث می‌شود مدل لاتین، گلیف‌های فارسی را به حروف
    لاتین تفسیر کند و کلماتی مثل «Sy»، «us»، «44۵» داخل متن فارسی تزریق شود.
    راه‌حل: هر زبان در گذر (pass) جداگانه اجرا می‌شود و قطعه‌ها با برچسب زبان
    برمی‌گردند؛ ادغام در سطح خط لوله انجام می‌شود.

استراتژی تطبیقی:
    ۱. کاوش (probe): یک اجرای سریع «fas» با PSM پایه روی تصویر خام.
    ۲. اگر متن کاوش فارسی‌غالب بود → فقط fas (جلوگیری کامل از آلودگی لاتین).
    ۳. اگر لاتین‌غالب یا بی‌متن بود → فقط eng.
    ۴. اگر ترکیبی/مبهم بود → هر دو زبان در گذرهای جدا.

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
from ..textnorm import is_mostly_persian
from .base import OcrProvider, OcrRaw

INSTALL_HINT_FA = (
    "Tesseract نصب نیست. راهنما: در Ubuntu «sudo apt install tesseract-ocr»، "
    "در Windows نصب‌کننده UB-Mannheim، در macOS «brew install tesseract»."
)
FAS_HINT_FA = (
    "داده زبان فارسی fas.traineddata در models/tessdata یافت نشد؛ "
    "اسکریپت scripts/download_tessdata.py را اجرا کنید تا خواندن فارسی فعال شود."
)

PROBE_MIN_WORDS = 3


class TesseractProvider(OcrProvider):
    name = "tesseract"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.tessdata_dir: Path = Path(settings.tessdata_dir)
        self._langs = settings.ocr_languages
        # زبان‌های به‌کاررفته در آخرین اجرا (برای متادیتا و شفافیت)
        self.last_langs_used: list[str] = []
        # v2.10.0: فهرست PSM به‌کاررفته در آخرین اجرا (برای رکورد کامل خوانش خام)
        self.last_psms: list[int] = []
        # تصمیم زبان در اولین اجرا گرفته می‌شود و برای واریانت‌های بعدیِ
        # «همین تصویر» کش می‌شود (نمونهٔ provider به‌ازای هر تصویر تازه است)
        self._decided_langs: list[str] | None = None

    def available(self) -> tuple[bool, str]:
        if shutil.which("tesseract") is None:
            return False, INSTALL_HINT_FA
        if self.tessdata_dir.exists() and (self.tessdata_dir / "fas.traineddata").exists():
            self._langs = "fas+eng"
        elif self.tessdata_dir.exists() and (self.tessdata_dir / "eng.traineddata").exists():
            self._langs = "eng"
        # اگر مسیر محلی نبود، از نصب سیستمی استفاده می‌شود
        return True, FAS_HINT_FA if self._langs == "eng" else ""

    @property
    def fas_available(self) -> bool:
        return (self.tessdata_dir.exists()
                and (self.tessdata_dir / "fas.traineddata").exists())

    # ---------- استراتژی زبان تطبیقی (v1.8.0) ----------
    def _decide_langs(self, image_bgr: np.ndarray) -> list[str]:
        """انتخاب زبان(ها) بر اساس کاوش مقایسه‌ای سریع (v1.8.0-ط).

        هر دو زبانِ موجود یک اجرای سبک (PSM پایه) می‌گیرند و «امتیاز خوانش»
        (مجموع اطمینان × طول مؤثر) مقایسه می‌شود:
        - فارسی به‌مراتب جلوتر → فقط fas (جلوگیری از تزریق لاتین به فارسی)؛
        - لاتین به‌مراتب جلوتر → فقط eng (جلوگیری از زبالهٔ fas روی انگلیسی)؛
        - نزدیک هم → هر دو در گذر جدا (بستهٔ دوزبانه).
        اجرای fas+eng «ترکیبی» هرگز انجام نمی‌شود (ریشهٔ خروجی آشغال).
        """
        strategy = (getattr(self.settings, "ocr_language_strategy", "adaptive")
                    or "adaptive").strip().lower()
        if strategy in ("fas", "fa"):
            return ["fas"] if self.fas_available else ["eng"]
        if strategy == "eng":
            return ["eng"]
        if strategy in ("fas+eng", "combined"):
            return ["fas", "eng"] if self.fas_available else ["eng"]

        # --- adaptive: کاوش مقایسه‌ای ---
        langs_to_probe = (["fas", "eng"] if self.fas_available else ["eng"])
        scores: dict[str, float] = {}
        for lang in langs_to_probe:
            probe = self._run_single(image_bgr, lang, self.settings.tesseract_psm)
            score = 0.0
            for p in probe:
                if p.confidence is None:
                    continue
                alnum = sum(1 for ch in p.text if ch.isalnum())
                if alnum < 2:
                    continue
                score += float(p.confidence) * min(alnum, 12)
            scores[lang] = score
        fa_score = scores.get("fas", 0.0)
        en_score = scores.get("eng", 0.0)
        if not self.fas_available:
            return ["eng"]
        if fa_score >= en_score * 1.3:
            return ["fas"]
        if en_score >= fa_score * 1.3:
            return ["eng"]
        return ["fas", "eng"]

    # ---------- اجرا ----------
    def _tess_config(self, psm: int) -> str:
        cfg = f"--psm {int(psm)}"
        if self.tessdata_dir.exists():
            cfg += f' --tessdata-dir "{self.tessdata_dir}"'
        return cfg

    def _psm_list(self) -> list[int]:
        psms = [self.settings.tesseract_psm]
        extra = int(self.settings.tesseract_extra_psm or 0)
        if extra and extra != self.settings.tesseract_psm:
            psms.append(extra)
        sparse = int(self.settings.tesseract_sparse_psm or 0)
        if sparse and sparse not in psms:
            # PSM 11 (پراکنده) برای برچسب‌هایی با چند بلوک متن جدا از هم حیاتی است
            psms.append(sparse)
        return psms

    def _run_single(self, image_bgr: np.ndarray, lang: str, psm: int,
                    variant: str = "__probe__") -> list[OcrRaw]:
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        data = pytesseract.image_to_data(
            rgb,
            lang=lang,
            config=self._tess_config(psm),
            output_type=pytesseract.Output.DICT,
        )
        pieces: list[OcrRaw] = []
        for i in range(len(data["text"])):
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
                engine=f"{self.name}:{lang}",
            ))
        return pieces

    def run(self, image_bgr: np.ndarray, variant: str) -> list[OcrRaw]:
        ok, hint = self.available()
        if not ok:
            raise RuntimeError(hint)
        if self._decided_langs is None:
            self._decided_langs = self._decide_langs(image_bgr)
        langs = self._decided_langs
        self.last_langs_used = list(langs)
        self.last_psms = list(self._psm_list())
        pieces: list[OcrRaw] = []
        for lang in langs:
            for psm in self._psm_list():
                pieces.extend(
                    self._run_single(image_bgr, lang, psm, variant=variant))
        return pieces

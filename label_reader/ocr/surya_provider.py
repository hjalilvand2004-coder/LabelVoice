# -*- coding: utf-8 -*-
"""ارائه‌دهنده OCR مبتنی بر Surya (اختیاری — به انتخاب کاربر) — v2.2.0.

Surya چیست؟
    موتور OCR متن‌باز (مخزن VikParuchuri/surya — سازندهٔ Marker) با شبکه‌های
    تشخیص خط (Detection) و بازشناسی متن (Recognition) مبتنی بر ترنسفورمر؛
    پشتیبانی گسترده از بیش از ۹۰ زبان از جمله فارسی.

نکات صادقانه:
- بارگذاری اول نیازمند دانلود وزن مدل‌ها از Hugging Face است (چند صد مگابایت)
  و کند است؛ نمونه‌ها Singleton نگه داشته می‌شوند تا بارگذاری تکرار نشود.
- این ماژول lazy import می‌کند؛ نبود surya-ocr مسیر اصلی را نمی‌شکند.
- فقط دسکتاپ (موبایل/WASM پشتیبانی نمی‌کند) — عین EasyOCR.
- خروجی به همان قالب OcrRaw (متن، اطمینان، جعبه) تبدیل می‌شود تا از همان
  گیت کیفیت و رأی اجماعی خط لوله عبور کند؛ هیچ میان‌بری ندارد.
"""
from __future__ import annotations

import threading

import numpy as np

from ..config import Settings
from .base import OcrProvider, OcrRaw, OcrUnavailableError

INSTALL_HINT_FA = (
    "surya-ocr نصب نیست. نصب: «pip install surya-ocr» (به torch نیاز دارد؛ "
    "برای CPU: «pip install torch --index-url "
    "https://download.pytorch.org/whl/cpu»). اولین اجرا وزن مدل‌ها را از "
    "Hugging Face دانلود می‌کند (نیازمند اینترنت)."
)

_MODELS = None
_MODELS_LOCK = threading.Lock()


def _get_models(settings: Settings):
    """Singleton: (RecognitionPredictor, DetectionPredictor) با کش سراسری.

    ساختار رسمی surya-ocr 0.17.x: FoundationPredictor زیربنای مشترک
    RecognitionPredictor است (عین مثال رسمی surya/scripts/ocr_text.py).
    در بارگذاری پیش‌فرض (fp32 روی CPU) اگر حافظه کافی نباشد، یک‌بار با
    dtype=float16 تلاش می‌شود (نصف رم؛ روی CPU قابل اجراست).
    """
    global _MODELS
    with _MODELS_LOCK:
        if _MODELS is None:
            from surya.detection import DetectionPredictor  # lazy
            from surya.foundation import FoundationPredictor  # lazy
            from surya.recognition import RecognitionPredictor  # lazy

            model_dir = getattr(settings, "surya_model_dir", None)
            if model_dir is not None:
                # سوریا از متغیر محیطی SURYA_MODEL_CACHE_DIR استفاده می‌کند
                import os

                os.environ.setdefault("SURYA_MODEL_CACHE_DIR", str(model_dir))
            try:
                foundation = FoundationPredictor()
                _MODELS = (RecognitionPredictor(foundation),
                           DetectionPredictor())
            except (MemoryError, RuntimeError) as _oom_err:
                # بارگذاری fp32 ناموفق (معمولاً کمبود رم) → fp16
                import torch  # noqa: BLE001 — surya به torch وابسته است

                try:
                    foundation = FoundationPredictor(dtype=torch.float16)
                    _MODELS = (RecognitionPredictor(foundation),
                               DetectionPredictor())
                except Exception as err:  # noqa: BLE001
                    raise OcrUnavailableError(
                        "بارگذاری مدل‌های Surya ناموفق بود؛ رایانه به حافظهٔ "
                        "بیشتری نیاز دارد (حداقل ~۴ گیگابایت آزاد). خطا: "
                        f"{err} (خطای اولیه: {_oom_err})") from err
        return _MODELS


class SuryaProvider(OcrProvider):
    name = "surya"

    def __init__(self, settings: Settings):
        self.settings = settings
        self._import_ok = True
        try:
            import surya  # noqa: F401
        except Exception:  # noqa: BLE001
            self._import_ok = False

    def available(self) -> tuple[bool, str]:
        return (True, "") if self._import_ok else (False, INSTALL_HINT_FA)

    @staticmethod
    def _to_pil(image_bgr: np.ndarray):
        import cv2
        from PIL import Image

        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)

    def run(self, image_bgr: np.ndarray, variant: str) -> list[OcrRaw]:
        if not self._import_ok:
            raise RuntimeError(INSTALL_HINT_FA)
        rec_model, det_processor = _get_models(self.settings)
        pil_image = self._to_pil(image_bgr)
        preds = self._predict(rec_model, det_processor, pil_image)
        pieces: list[OcrRaw] = []
        for pred in preds:
            for line in getattr(pred, "text_lines", []) or []:
                text = (getattr(line, "text", "") or "").strip()
                if not text:
                    continue
                bbox = getattr(line, "bbox", None)
                if bbox is not None and len(bbox) == 4:
                    x0, y0, x1, y1 = [int(v) for v in bbox]
                else:
                    poly = getattr(line, "polygon", None) or []
                    xs = [int(p[0]) for p in poly] or [0]
                    ys = [int(p[1]) for p in poly] or [0]
                    x0, y0 = max(0, min(xs)), max(0, min(ys))
                    x1, y1 = max(xs), max(ys)
                conf = getattr(line, "confidence", None)
                pieces.append(OcrRaw(
                    text=text,
                    confidence=(float(conf) if conf is not None else None),
                    x=max(0, x0), y=max(0, y0),
                    w=max(1, x1 - x0), h=max(1, y1 - y0),
                    variant=variant,
                    engine=self.name,
                ))
        return pieces

    @staticmethod
    def _predict(rec_model, det_processor, pil_image):
        """فراخوانی سازگار با surya-ocr 0.17.x (API کلاسیک خط‌محور).

        تک‌مدل چندزبانه است (فارسی را بدون تعیین زبان می‌خواند)؛ به همین
        دلیل پارامتر زبان وجود ندارد و وظیفهٔ استاندارد «ocr_with_boxes»
        اجرا می‌شود تا هر خط با کادر و اطمینان برگردد.
        """
        from surya.common.surya.schema import TaskNames  # lazy

        return rec_model(
            [pil_image],
            [TaskNames.ocr_with_boxes],
            det_processor,
            recognition_batch_size=8,
            drop_repeated_text=True,
        )

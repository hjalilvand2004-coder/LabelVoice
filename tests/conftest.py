# -*- coding: utf-8 -*-
"""ابزارهای مشترک آزمون‌ها."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from label_reader.config import Settings  # noqa: E402
from label_reader.models import BoundingBox, OcrPiece, RawLine  # noqa: E402
from label_reader.textnorm import normalize_for_matching  # noqa: E402


@pytest.fixture()
def settings() -> Settings:
    s = Settings(_env_file=None)
    s.use_binarized_variant = False
    return s


def make_line(idx: int, text: str, y: int = 0, x: int = 0,
              conf: float | None = 0.92) -> RawLine:
    """ساخت سطر آزمون با شناسه شاهد پایدار."""
    return RawLine(
        id=f"line_{idx:03d}",
        text=text,
        normalized_text=normalize_for_matching(text),
        source_ids=[f"ocr_{idx:03d}"],
        bbox=BoundingBox(x=x, y=y, w=max(1, 10 * len(text)), h=24),
        confidence_mean=conf,
    )


def make_piece(idx: int, text: str, y: int, x: int = 20,
               conf: float | None = 0.92, variant: str = "original",
               engine: str = "fake") -> OcrPiece:
    return OcrPiece(
        id=f"ocr_{idx:03d}", text=text, normalized_text=normalize_for_matching(text),
        bbox=BoundingBox(x=x, y=y, w=max(1, 10 * len(text)), h=24),
        confidence=conf, variant=variant, engine=engine,
    )


class FakeOcrProvider:
    """ارائه‌دهنده OCR ساختگی برای آزمون خط کامل بدون موتور واقعی.

    چیدمان کلمات مثل موتور واقعی است: سطرهای فارسی به‌صورت بصری (اولین واژه
    منطقی در راست) و سطرهای لاتین چپ‌به‌راست.
    """

    name = "fake"

    def __init__(self, lines: list[tuple[str, float]]):
        self.lines = lines

    def available(self):
        return True, ""

    def run(self, image_bgr, variant: str):
        from label_reader.ocr.base import OcrRaw
        from label_reader.textnorm import is_mostly_persian

        out = []
        y = 30
        for text, conf in self.lines:
            words = text.split()
            rtl = is_mostly_persian(text)
            for j, word in enumerate(words):
                x = 20 + (len(words) - 1 - j) * 120 if rtl else 20 + j * 120
                out.append(OcrRaw(
                    text=word, confidence=conf, x=x, y=y,
                    w=10 * len(word), h=24, variant=variant, engine=self.name))
            y += 60
        return out


def has_tesseract_with_fas() -> bool:
    import shutil

    if shutil.which("tesseract") is None:
        return False
    return (ROOT / "models" / "tessdata" / "fas.traineddata").exists() or \
        Path("/usr/share/tesseract-ocr/5/tessdata/fas.traineddata").exists()

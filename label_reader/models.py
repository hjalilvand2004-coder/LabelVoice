# -*- coding: utf-8 -*-
"""مدل داده‌ای پروژه (Pydantic v2) — قابلیت ردیابی کامل هر فیلد تا شواهد OCR.

هر فیلد نمایش‌داده‌شده باید به یک یا چند شناسه قطعه OCR (source_ids) یا
اصلاح صریح کاربر (status=user_corrected) متصل باشد.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductType(str, Enum):
    MEDICINE = "medicine"
    GENERAL_PRODUCT = "general_product"
    UNKNOWN = "unknown"


class FieldStatus(str, Enum):
    EXTRACTED = "extracted"
    UNCERTAIN = "uncertain"
    MISSING = "missing"
    CONFLICTING = "conflicting"
    USER_CORRECTED = "user_corrected"


class BoundingBox(BaseModel):
    model_config = ConfigDict(frozen=True)

    x: int
    y: int
    w: int
    h: int

    @property
    def x2(self) -> int:
        return self.x + self.w

    @property
    def y2(self) -> int:
        return self.y + self.h

    def iou(self, other: "BoundingBox") -> float:
        ix = max(0, min(self.x2, other.x2) - max(self.x, other.x))
        iy = max(0, min(self.y2, other.y2) - max(self.y, other.y))
        inter = ix * iy
        union = self.w * self.h + other.w * other.h - inter
        return inter / union if union > 0 else 0.0


class OcrPiece(BaseModel):
    """یک قطعه متن (کلمه یا ناحیه) خروجی موتور OCR."""

    id: str
    text: str                      # متن خام، همان‌طور که موتور برگرداند
    normalized_text: str           # فقط اصلاح نویسه (ي→ی، ك→ک، ارقام داخلی)
    bbox: BoundingBox
    confidence: Optional[float] = None   # 0..1؛ None یعنی موتور امتیاز نداد
    variant: str                   # نسخه پردازشی تصویر (original / gray_clahe / ...)
    engine: str                    # tesseract:fas / tesseract:eng / easyocr
    support: int = 1               # v1.8.0: چند پیکربندی مستقل همین ناحیه را خواندند


class RawLine(BaseModel):
    """یک سطر منطقی ساخته‌شده از قطعات OCR (برای نمایش و استخراج)."""

    id: str
    text: str
    normalized_text: str
    source_ids: list[str] = Field(default_factory=list)
    bbox: BoundingBox
    confidence_mean: Optional[float] = None


class QualityIssue(BaseModel):
    code: str          # blurry / dark / bright / glare / low_resolution / ok
    severity: Literal["info", "warning", "severe"]
    message_fa: str


class FieldRecord(BaseModel):
    """ساختار هر فیلد استخراج‌شده با اتصال به شواهد."""

    key: str
    label_fa: str
    value: Optional[str] = None          # مقدار نهایی برای نمایش (ارقام فارسی)
    unit: Optional[str] = None           # واحد بدون تغییر معنایی (mg, mcg, mL, ...)
    raw_text: Optional[str] = None       # متن خامِ شاهد
    source_ids: list[str] = Field(default_factory=list)
    confidence: Optional[float] = None
    status: FieldStatus = FieldStatus.MISSING
    previous_values: list[str] = Field(default_factory=list)  # منشأ پیش از اصلاح کاربر
    note_fa: Optional[str] = None        # توضیح ابهام/تناقض/ناخوانایی


class ProcessingMetadata(BaseModel):
    engine: str
    languages: str
    variants_used: list[str]
    image_width: int
    image_height: int
    deskew_applied: bool = False
    deskew_angle_deg: Optional[float] = None
    durations_ms: dict[str, int] = Field(default_factory=dict)
    warnings_fa: list[str] = Field(default_factory=list)
    notes_fa: list[str] = Field(default_factory=list)
    timestamp_utc: str = ""
    app_version: str = "1.0.0"


class AnalysisResult(BaseModel):
    """خروجی کامل پردازش یک تصویر."""

    product_type: ProductType = ProductType.UNKNOWN
    product_type_note_fa: str = ""
    ocr_pieces: list[OcrPiece] = Field(default_factory=list)
    raw_lines: list[RawLine] = Field(default_factory=list)
    fields: dict[str, FieldRecord] = Field(default_factory=dict)
    quality_issues: list[QualityIssue] = Field(default_factory=list)
    response_fa: str = ""
    metadata: ProcessingMetadata

    def to_json_str(self) -> str:
        return self.model_dump_json(indent=2)

    def to_json_bytes(self) -> bytes:
        return self.to_json_str().encode("utf-8")


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

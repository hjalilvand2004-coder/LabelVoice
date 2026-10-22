# -*- coding: utf-8 -*-
"""اعتبارسنجی فایل تصویر: نوع واقعی، اندازه، تعداد پیکسل، اصلاح جهت EXIF."""
from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = 300_000_000  # سقف ایمنی خود PIL؛ بررسی دقیق‌تر پایین‌تر انجام می‌شود

ALLOWED_FORMATS = {"JPEG", "PNG"}
JPEG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


class ImageValidationError(Exception):
    """خطای اعتبارسنجی با پیام فارسی و کد ماشین‌خوان."""

    def __init__(self, code: str, message_fa: str):
        super().__init__(message_fa)
        self.code = code
        self.message_fa = message_fa


def sniff_format(data: bytes) -> str | None:
    """تشخیص نوع واقعی فایل از روی بایت‌های آغازین (نه پسوند)."""
    if data[:3] == JPEG_MAGIC:
        return "JPEG"
    if data[:8] == PNG_MAGIC:
        return "PNG"
    return None


def validate_and_load(data: bytes, *, max_file_mb: int, max_pixels: int) -> Image.Image:
    """اعتبارسنجی کامل و بازگشت تصویر RGB با اعمال جهت EXIF.

    مراحل: اندازه فایل ← نوع واقعی ← باز شدن ← تعداد پیکسل ← EXIF transpose ← RGB
    """
    if not data:
        raise ImageValidationError("empty_file", "فایل تصویر خالی است. لطفاً تصویر دیگری انتخاب کنید.")
    limit_bytes = max_file_mb * 1024 * 1024
    if len(data) > limit_bytes:
        raise ImageValidationError(
            "file_too_large",
            f"حجم فایل بیش از حد مجاز است (حداکثر {max_file_mb} مگابایت).",
        )
    fmt = sniff_format(data)
    if fmt is None:
        raise ImageValidationError(
            "unsupported_format",
            "قالب فایل مجاز نیست. فقط JPG، JPEG و PNG پذیرفته می‌شود.",
        )
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:  # فایل خراب
        raise ImageValidationError(
            "corrupt_image", "فایل تصویر باز نشد؛ فایل خراب یا ناقص است."
        ) from exc
    if (img.format or fmt) not in ALLOWED_FORMATS:
        raise ImageValidationError(
            "unsupported_format",
            "قالب واقعی تصویر مجاز نیست. فقط JPG و PNG پذیرفته می‌شود.",
        )
    width, height = img.size
    if width * height > max_pixels:
        raise ImageValidationError(
            "too_many_pixels",
            f"تعداد پیکسل تصویر بیش از حد مجاز است (حداکثر {max_pixels:,} پیکسل).",
        )
    # اصلاح جهت بر اساس EXIF
    img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def pil_to_bgr(img: Image.Image) -> np.ndarray:
    """تبدیل PIL RGB به آرایه BGR سازگار با OpenCV."""
    rgb = np.asarray(img, dtype=np.uint8)
    return rgb[:, :, ::-1].copy()


def bgr_to_pil(bgr: np.ndarray) -> Image.Image:
    return Image.fromarray(bgr[:, :, ::-1].copy())

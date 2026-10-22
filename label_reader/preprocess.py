# -*- coding: utf-8 -*-
"""پیش‌پردازش OpenCV — قابل تنظیم و محافظه‌کارانه.

ملاحظه مهم: از پردازش‌هایی که شکل اعداد یا حروف را تغییر دهند پرهیز می‌شود
(بدون threshold سراسری تهاجمی، بدون تغییر شکل نویسه). تصویر اصلی همیشه
حفظ می‌شود و OCR روی چند نسخه اجرا و نتایج مقایسه می‌گردد.
"""
from __future__ import annotations

import cv2
import numpy as np

from .config import Settings

VARIANT_ORIGINAL = "original"
VARIANT_GRAY_CLAHE = "gray_clahe"
VARIANT_BINARIZED = "binarized"


def upscale_if_needed(bgr: np.ndarray, target_min_side: int) -> np.ndarray:
    """بزرگ‌نمایی کنترل‌شده برای OCR (فقط وقتی تصویر کوچک است)."""
    h, w = bgr.shape[:2]
    min_side = min(h, w)
    if min_side >= target_min_side:
        return bgr
    scale = min(3.0, target_min_side / max(1, min_side))
    new_w, new_h = int(round(w * scale)), int(round(h * scale))
    return cv2.resize(bgr, (new_w, new_h), interpolation=cv2.INTER_CUBIC)


def to_gray_clahe(bgr: np.ndarray, settings: Settings) -> np.ndarray:
    """تبدیل به خاکستری + کاهش نویز ملایم + بهبود کنتراست با CLAHE."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, d=5, sigmaColor=40, sigmaSpace=5)
    clahe = cv2.createCLAHE(
        clipLimit=settings.clahe_clip_limit,
        tileGridSize=(settings.clahe_tile_size, settings.clahe_tile_size),
    )
    gray = clahe.apply(gray)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def binarize(bgr: np.ndarray) -> np.ndarray:
    """آستانه‌گذاری تطبیقی فقط به‌عنوان نسخه جایگزین برای مقایسه نتایج OCR.

    نتیجه به BGR سه‌کاناله برگردانده می‌شود تا همه موتورها یک ورودی داشته باشند.
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    bw = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)
    return cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)


def estimate_skew_angle(bgr: np.ndarray) -> float:
    """برآورد زاویه چرخش سطرهای متن (درجه). مثبت = نیاز به چرخش پادساعتگرد."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    bw = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 35, 20)
    # اتصال حروف هر سطر برای پیدا کردن مستطیل سطرها
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 3))
    merged = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, kernel)
    coords = cv2.findNonZero(merged)
    if coords is None or len(coords) < 50:
        return 0.0
    rect = cv2.minAreaRect(coords)
    angle = rect[2]
    if angle > 45:
        angle -= 90
    return float(angle)


def rotate_bgr(bgr: np.ndarray, angle_deg: float) -> np.ndarray:
    h, w = bgr.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
    return cv2.warpAffine(
        bgr, matrix, (w, h), flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE)


def auto_deskew(bgr: np.ndarray, settings: Settings) -> tuple[np.ndarray, float]:
    """اصلاح چرخش کم‌زاویه؛ زاویه‌های بزرگ قابل اعتماد نیستند و دست نمی‌خورند."""
    angle = estimate_skew_angle(bgr)
    if 0.5 <= abs(angle) <= settings.deskew_max_angle_deg:
        return rotate_bgr(bgr, angle), angle
    return bgr, 0.0


def crop_fraction(bgr: np.ndarray, box: tuple[float, float, float, float]) -> np.ndarray:
    """برش با کسری از ابعاد تصویر: (x, y, w, h) هرکدام 0..1."""
    h, w = bgr.shape[:2]
    fx, fy, fw, fh = box
    x0 = int(round(max(0.0, fx) * w))
    y0 = int(round(max(0.0, fy) * h))
    x1 = int(round(min(1.0, fx + fw) * w))
    y1 = int(round(min(1.0, fy + fh) * h))
    if x1 - x0 < 10 or y1 - y0 < 10:
        return bgr
    return bgr[y0:y1, x0:x1].copy()


def build_variants(bgr: np.ndarray, settings: Settings) -> dict[str, np.ndarray]:
    """ساخت نسخه‌های پردازشی؛ تصویر اصلی حفظ و بازگردانده می‌شود."""
    base = upscale_if_needed(bgr, settings.target_min_side)
    variants: dict[str, np.ndarray] = {VARIANT_ORIGINAL: base}
    variants[VARIANT_GRAY_CLAHE] = to_gray_clahe(base, settings)
    if settings.use_binarized_variant:
        variants[VARIANT_BINARIZED] = binarize(base)
    return variants

# -*- coding: utf-8 -*-
"""ارزیابی کیفیت تصویر: تاری، نور نامناسب، انعکاس و رزولوشن پایین.

این ارزیابی‌ها هیوریستیک هستند و به‌عنوان راهنما ارائه می‌شوند؛ امتیاز
کیفیت معادل «قطعیت محتوا» نیست. اگر کیفیت ناکافی باشد راهنمای عملی
نمایش داده می‌شود و پردازش متوقف نمی‌شود (مگر تصویر کاملاً نامناسب).
"""
from __future__ import annotations

import cv2
import numpy as np

from .models import QualityIssue
from .config import Settings

BLUR_GUIDANCE_FA = (
    "متن بسته واضح نیست. لطفاً دوربین را ثابت نگه دارید، نور را بهتر کنید "
    "و از انعکاس نور روی بسته جلوگیری کنید."
)


class QualityMetrics:
    def __init__(self, width: int, height: int, laplacian_var: float,
                 mean_brightness: float, highlight_ratio: float):
        self.width = width
        self.height = height
        self.laplacian_var = laplacian_var
        self.mean_brightness = mean_brightness
        self.highlight_ratio = highlight_ratio

    def as_dict(self) -> dict:
        return {
            "width": self.width,
            "height": self.height,
            "laplacian_var": round(self.laplacian_var, 2),
            "mean_brightness": round(self.mean_brightness, 2),
            "highlight_ratio": round(self.highlight_ratio, 4),
        }


def _standard_gray(bgr: np.ndarray, target_width: int = 800) -> np.ndarray:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    if w > target_width:
        scale = target_width / w
        gray = cv2.resize(gray, (target_width, max(1, int(h * scale))),
                          interpolation=cv2.INTER_AREA)
    return gray


def _washed_ratio(gray: np.ndarray) -> float:
    """نسبت پیکسل‌های میان‌روشن (190..246) — نشانه عکس شسته‌شده/بیش‌نور.

    برچسب با پس‌زمینه سفید خالص این آستانه را فعال نمی‌کند چون پس‌زمینه آن
    نزدیک 255 است، نه در بازه میان‌روشن.
    """
    mask = (gray >= 190) & (gray <= 246)
    return float(mask.sum()) / float(gray.size)


def assess_quality(bgr: np.ndarray, settings: Settings) -> tuple[QualityMetrics, list[QualityIssue]]:
    """سنجش کیفیت و تولید هشدارهای فارسی (همیشه همراه متن؛ نه فقط رنگ)."""
    gray = _standard_gray(bgr)
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    mean_brightness = float(gray.mean())
    highlight_ratio = float((gray > 248).sum()) / float(gray.size)
    washed = _washed_ratio(gray)

    h, w = bgr.shape[:2]
    metrics = QualityMetrics(w, h, lap_var, mean_brightness, highlight_ratio)
    issues: list[QualityIssue] = []

    if lap_var < settings.severe_blur_threshold:
        issues.append(QualityIssue(
            code="blurry", severity="severe", message_fa=BLUR_GUIDANCE_FA))
    elif lap_var < settings.blur_laplacian_threshold:
        issues.append(QualityIssue(
            code="blurry", severity="warning",
            message_fa="تصویر کمی تار است؛ " + BLUR_GUIDANCE_FA))

    if mean_brightness < settings.dark_mean_brightness:
        issues.append(QualityIssue(
            code="dark", severity="warning",
            message_fa="نور تصویر کم است. لطفاً در محیط روشن‌تر از بسته عکس بگیرید."))

    if washed > 0.55:
        issues.append(QualityIssue(
            code="bright", severity="warning",
            message_fa="تصویر بیش از حد روشن/شسته‌شده است؛ نور مستقیم روی بسته نیفتد."))

    # انعکاس: ناحیه بزرگ سوخته روشن در عکسی با میان‌تون (نه پس‌زمینه سفید برچسب)
    if highlight_ratio > settings.glare_highlight_ratio and \
            80 < mean_brightness < 235:
        issues.append(QualityIssue(
            code="glare", severity="warning",
            message_fa="احتمال انعکاس نور روی بسته وجود دارد. زاویه دوربین یا منبع نور را تغییر دهید."))

    if min(w, h) < settings.min_dimension_px:
        issues.append(QualityIssue(
            code="low_resolution", severity="warning",
            message_fa="رزولوشن تصویر پایین است. لطفاً از نزدیک‌تر و بدون زوم دیجیتال عکس بگیرید."))

    if not issues:
        issues.append(QualityIssue(
            code="ok", severity="info",
            message_fa="کیفیت تصویر برای خواندن برچسب مناسب به نظر می‌رسد."))
    return metrics, issues


def has_severe_issue(issues: list[QualityIssue]) -> bool:
    return any(i.severity == "severe" for i in issues)

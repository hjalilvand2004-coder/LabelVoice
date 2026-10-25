# -*- coding: utf-8 -*-
"""آزمون‌های v2.9.0 — توسعهٔ کیفیت پایپ‌لاین OpenCV.

پوشش:
۱) flatten_illumination: حذف سایه/گرادیان روشنایی (تقسیم بر پس‌زمینه)
۲) unsharp_gray: افزایش تیزی لبه‌ها
۳) واریانت‌های جدید shadow_free و sharpened در build_variants_traced
۴) binarize: خروجی دودویی پاک با بلوک مقیاس‌پذیر
۵) estimate_skew_angle: پالایش پروفایلی روی متن چرخیده
۶) گیت اطمینان: واریانت‌های مکمل فقط وقتی خوانش اصلی ضعیف است اجرا می‌شوند
"""
import cv2
import numpy as np
import pytest
from PIL import Image, ImageDraw

from label_reader.config import Settings
from label_reader.pipeline import LabelReaderPipeline
from label_reader.preprocess import (
    VARIANT_SHADOW_FREE, VARIANT_SHARPENED,
    build_variants_traced, flatten_illumination, unsharp_gray,
    estimate_skew_angle, binarize,
)
from tests.conftest import FakeOcrProvider


def _bgr(img: Image.Image) -> np.ndarray:
    return np.array(img)[:, :, ::-1].copy()


def _shadowed_box(w: int = 800, h: int = 560) -> Image.Image:
    """جعبهٔ سفید با متن تیره + گرادیان روشنایی سنگین (سایهٔ سمت چپ)."""
    img = Image.new("RGB", (w, h), (245, 245, 242))
    d = ImageDraw.Draw(img)
    ys = 40
    for _ in range(7):
        d.rectangle([80, ys, w - 80, ys + 34], fill=(20, 20, 20))
        ys += 70
    arr = np.array(img).astype(np.float32)
    grad = np.linspace(0.45, 1.0, w, dtype=np.float32)[None, :, None]
    arr *= grad  # تاریک‌شدن سمت چپ تصویر تا ۴۵٪
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


# ---------------------------------------------------------------------------
# ۱) یکنواخت‌سازی نور
# ---------------------------------------------------------------------------
def test_flatten_illumination_removes_gradient():
    src = _bgr(_shadowed_box())
    gray = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
    flat = flatten_illumination(gray)
    # پس‌زمینه پس از flatten باید تقریباً هموار باشد (انحراف معیار کم)
    # نمونه‌گیری از نواحی بدون متن (ستون‌های حاشیه)
    left_bg_before = gray[10:30, 5:60].std()
    left_bg_after = flat[10:30, 5:60].std()
    assert left_bg_after < max(6.0, left_bg_before * 0.5), (
        f"گرادیان حذف نشد: std قبل={left_bg_before:.1f} بعد={left_bg_after:.1f}")
    # متن تیره باید تیره بماند (کنتراست متن حفظ شود)
    assert flat[60:80, 300:500].mean() < flat[10:30, 300:500].mean()


def test_flatten_output_range():
    gray = (np.ones((120, 160), dtype=np.uint8) * 200)
    flat = flatten_illumination(gray)
    assert flat.shape == gray.shape
    assert flat.min() >= 0 and flat.max() <= 255


# ---------------------------------------------------------------------------
# ۲) تیزکردن لبه‌ها
# ---------------------------------------------------------------------------
def test_unsharp_gray_increases_sharpness():
    src = _bgr(_shadowed_box())
    gray = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
    soft = cv2.GaussianBlur(gray, (5, 5), 1.2)  # شبیه‌سازی عکس نرم موبایل
    sharp = unsharp_gray(soft, 0.9)
    var_before = cv2.Laplacian(soft, cv2.CV_64F).var()
    var_after = cv2.Laplacian(sharp, cv2.CV_64F).var()
    assert var_after > var_before * 1.3, (
        f"تیزی افزایش نیافت: {var_before:.1f} → {var_after:.1f}")


# ---------------------------------------------------------------------------
# ۳) واریانت‌های جدید در مسیر گام‌به‌گام
# ---------------------------------------------------------------------------
def test_new_variants_in_traced_build(settings):
    bgr = _bgr(_shadowed_box())
    variants, trace = build_variants_traced(bgr, settings, collect_trace=True)
    assert VARIANT_SHADOW_FREE in variants
    assert VARIANT_SHARPENED in variants
    steps = [t["step"] for t in trace]
    assert VARIANT_SHADOW_FREE in steps and VARIANT_SHARPENED in steps
    assert len(steps) == len(variants)
    for entry in trace:
        assert entry["title_fa"] and entry["desc_fa"]
        assert entry["image_bgr"].shape[:2] == \
            variants[entry["step"]].shape[:2]
    # ترتیب: original اول، مکمل‌ها قبل از پلاریتی‌ها
    assert steps[0] == "original"
    assert steps.index(VARIANT_SHARPENED) < steps.index("white_on_dark")


def test_shadow_free_flattens_background(settings):
    bgr = _bgr(_shadowed_box())
    variants, _ = build_variants_traced(bgr, settings, collect_trace=False)
    sf = cv2.cvtColor(variants[VARIANT_SHADOW_FREE], cv2.COLOR_BGR2GRAY)
    src = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    # نوار بدون متن (بالا) — میانگین هر ستون فقط روی پس‌زمینه
    col_src = src[8:28, ::4].mean(axis=0)
    col_sf = sf[8:28, ::4].mean(axis=0)
    assert col_sf.std() < col_src.std() * 0.35, (
        f"گرادیان ستونی حذف نشد: {col_src.std():.1f} → {col_sf.std():.1f}")
    # میانگین پس‌زمینه پس از flatten نزدیک سفید است
    assert col_sf.mean() > 230


# ---------------------------------------------------------------------------
# ۴) دودویی مقیاس‌پذیر
# ---------------------------------------------------------------------------
def test_binarize_output_clean(settings):
    bgr = _bgr(_shadowed_box())
    out = binarize(bgr)
    gray = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
    uniq = set(np.unique(gray).tolist())
    assert uniq <= {0, 255}, f"خروجی دودویی نیست: {len(uniq)} سطح"
    # نسبت سیاه معقول (متن + نویز کم)
    black_ratio = float((gray == 0).mean())
    assert 0.01 < black_ratio < 0.6


# ---------------------------------------------------------------------------
# ۵) صاف‌کردن چرخش با پالایش پروفایلی
# ---------------------------------------------------------------------------
def test_estimate_skew_straight_is_zero():
    img = Image.new("RGB", (600, 400), (248, 248, 248))
    d = ImageDraw.Draw(img)
    for y in range(50, 380, 60):
        d.rectangle([60, y, 540, y + 26], fill=(30, 30, 30))
    angle = estimate_skew_angle(_bgr(img))
    assert abs(angle) <= 1.0, f"متن صاف، زاویهٔ {angle} برآورد شد"


def test_estimate_skew_rotated_close():
    img = Image.new("RGB", (600, 400), (248, 248, 248))
    d = ImageDraw.Draw(img)
    for y in range(50, 380, 60):
        d.rectangle([60, y, 540, y + 26], fill=(30, 30, 30))
    bgr = _bgr(img)
    m = cv2.getRotationMatrix2D((300, 200), 3.0, 1.0)
    rotated = cv2.warpAffine(bgr, m, (600, 400),
                             borderMode=cv2.BORDER_CONSTANT, borderValue=(248, 248, 248))
    angle = estimate_skew_angle(rotated)
    assert 1.5 <= abs(angle) <= 4.5, f"زاویهٔ ۳ درجه، {angle} برآورد شد"


# ---------------------------------------------------------------------------
# ۶) گیت اطمینان واریانت‌های مکمل
# ---------------------------------------------------------------------------
def _run_with_conf(conf: float) -> set:
    pipe = LabelReaderPipeline(
        Settings(_env_file=None), ocr_provider=FakeOcrProvider(
            [("Paracetamol", conf), ("500 mg", conf), ("20 Tablets", conf)]))
    payloads: dict = {}
    pipe.process_pil(Image.new("RGB", (640, 420), (240, 244, 248)),
                     stage_callback=lambda k, p: payloads.__setitem__(k, p))
    readings = payloads["ocr"]["variant_readings"]
    return {r["variant"] for r in readings}


def test_gate_closes_supplementary_when_confident():
    names = _run_with_conf(0.96)
    assert VARIANT_SHADOW_FREE not in names
    assert VARIANT_SHARPENED not in names


def test_gate_opens_supplementary_when_weak():
    names = _run_with_conf(0.40)
    assert VARIANT_SHADOW_FREE in names
    assert VARIANT_SHARPENED in names

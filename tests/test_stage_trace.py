# -*- coding: utf-8 -*-
"""آزمون‌های v2.6.0 — مسیر گام‌به‌گام OpenCV و خوانش خام هر نسخهٔ OCR.

کاربر خواسته «خروجی مرحله OpenCV را ببینم… و بعد ببینم OCR چی خوند»؛ این
آزمون‌ها تضمین می‌کنند:
۱) build_variants_traced برای هر عملیات OpenCV یک گام با تصویر/عنوان/توضیح می‌دهد؛
۲) خط لوله مسیر کامل (ورودی/برش/deskew/واریانت‌ها) و خوانش خام هر نسخه را
   در اعلام مراحل منتشر می‌کند؛
۳) ابزار کادرکشی خوانش خام بدون خطا کار می‌کند.
"""
import io

import numpy as np
import pytest
from PIL import Image

from label_reader.config import Settings
from label_reader.pipeline import LabelReaderPipeline
from label_reader.preprocess import build_variants, build_variants_traced
from label_reader.stages import build_stage_item
from label_reader.ui_helpers import draw_boxes_from_dicts
from tests.conftest import FakeOcrProvider


def _small_image(w: int = 640, h: int = 420) -> Image.Image:
    img = Image.new("RGB", (w, h), (240, 244, 248))
    return img


# ---------------------------------------------------------------------------
# ۱) traced واریانت‌ها
# ---------------------------------------------------------------------------
def test_build_variants_traced_steps(settings):
    bgr = np.array(_small_image())[:, :, ::-1].copy()  # RGB→BGR
    variants, trace = build_variants_traced(bgr, settings, collect_trace=True)

    steps = [t["step"] for t in trace]
    # پیش‌فرض‌ها: بدون واریانت دودویی (فیکسچر خاموشش کرده) اما با بقیه
    assert steps[0] == "original"
    assert "gray_clahe" in steps
    assert "white_on_dark" in steps
    assert "ink_isolated" in steps
    assert "binarized" not in steps
    assert len(steps) == len(variants)

    for entry in trace:
        assert entry["title_fa"], "هر گام باید عنوان فارسی داشته باشد"
        assert entry["desc_fa"], "هر گام باید توضیح عملیات داشته باشد"
        img = entry["image_bgr"]
        assert isinstance(img, np.ndarray) and img.ndim == 3
        # تصویر گام همان واریانت ساخته‌شده است
        assert img.shape[:2] == variants[entry["step"]].shape[:2]
        assert "metrics" not in entry  # معیارها در خط لوله اضافه می‌شود


def test_build_variants_traced_matches_build_variants(settings):
    bgr = np.array(_small_image())[:, :, ::-1].copy()
    variants_plain = build_variants(bgr, settings)
    variants_traced, _ = build_variants_traced(bgr, settings,
                                               collect_trace=False)
    assert set(variants_plain.keys()) == set(variants_traced.keys())


def test_build_variants_traced_upscale_step(settings):
    # تصویر کوچک → گام بزرگ‌نمایی باید توضیح resize داشته باشد
    bgr = np.array(_small_image(160, 110))[:, :, ::-1].copy()
    variants, trace = build_variants_traced(bgr, settings)
    first = trace[0]
    assert first["step"] == "original"
    assert "بزرگ‌نمایی" in first["title_fa"]
    assert variants["original"].shape[0] > bgr.shape[0]


# ---------------------------------------------------------------------------
# ۲) انتشار مسیر و خوانش خام در خط لوله
# ---------------------------------------------------------------------------
def _run_pipeline_capture(payloads: dict):
    pipe = LabelReaderPipeline(
        Settings(_env_file=None),
        ocr_provider=FakeOcrProvider([
            ("Paracetamol", 0.96), ("500 mg", 0.96), ("20 Tablets", 0.96)]))

    def cb(key, payload):
        payloads[key] = payload

    result = pipe.process_pil(_small_image(), stage_callback=cb)
    return result


def test_pipeline_emits_opencv_trace():
    payloads: dict = {}
    result = _run_pipeline_capture(payloads)
    assert result is not None
    opencv = payloads["opencv"]
    trace = opencv["opencv_trace"]
    assert isinstance(trace, list) and len(trace) >= 4
    steps = [e["step"] for e in trace]
    assert steps[0] == "input"
    assert "original" in steps and "gray_clahe" in steps
    for entry in trace:
        assert isinstance(entry["image_bgr"], np.ndarray)
        assert entry["title_fa"] and entry["desc_fa"]
        m = entry["metrics"]
        assert {"sharpness", "contrast", "brightness"} <= set(m.keys())
    assert len(opencv["opencv_steps"]) == len(trace)
    assert opencv["opencv_steps"][0] == trace[0]["title_fa"]


def test_pipeline_emits_variant_readings():
    payloads: dict = {}
    _run_pipeline_capture(payloads)
    readings = payloads["ocr"]["variant_readings"]
    assert isinstance(readings, list) and readings
    names = {r["variant"] for r in readings}
    assert "original" in names and "gray_clahe" in names
    all_text = []
    for r in readings:
        assert r["engines"] == ["fake"]
        assert isinstance(r["dropped"], int) and r["dropped"] >= 0
        for p in r["pieces"]:
            assert {"text", "confidence", "x", "y", "w", "h", "engine"} <= \
                set(p.keys())
            assert p["engine"] == "fake"
            all_text.append(p["text"])
    assert any("Paracetamol" in t for t in all_text)
    # ترتیب قطعه‌ها: بالا به پایین (y صعودی)
    for r in readings:
        ys = [p["y"] for p in r["pieces"]]
        assert ys == sorted(ys)


def test_stage_item_mentions_trace_and_readings():
    payloads: dict = {}
    _run_pipeline_capture(payloads)
    op_item = build_stage_item("opencv", payloads["opencv"])
    assert any("مسیر گام‌به‌گام OpenCV" in o for o in op_item["outputs_fa"])
    ocr_item = build_stage_item("ocr", payloads["ocr"])
    assert any("خوانش خام هر نسخه" in o for o in ocr_item["outputs_fa"])
    # گزارش JSON-سازگار می‌ماند (بدون تصویر/آرایه numpy)
    from label_reader.stages import report_json
    txt = report_json([op_item, ocr_item], {"engine": "fake"})
    assert "مسیر گام‌به‌گام OpenCV" in txt


# ---------------------------------------------------------------------------
# ۳) کادرکشی خوانش خام
# ---------------------------------------------------------------------------
def test_draw_boxes_from_dicts():
    img = _small_image()
    pieces = [
        {"text": "Paracetamol", "confidence": 0.96, "x": 20, "y": 40,
         "w": 220, "h": 30, "engine": "fake"},
        {"text": "500", "confidence": None, "x": 300, "y": 100,
         "w": 60, "h": 28, "engine": "fake"},
    ]
    out = draw_boxes_from_dicts(img, pieces)
    assert out.size == img.size
    assert out is not img  # کپی است؛ تصویر اصلی تغییر نمی‌کند
    # قطعه خراب نباید استثنا بدهد
    out2 = draw_boxes_from_dicts(img, [{"text": "x", "x": None, "w": "bad"}])
    assert out2.size == img.size

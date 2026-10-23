# -*- coding: utf-8 -*-
"""آزمون اعلام مرحله‌به‌مرحله پردازش و ارزیابی مرحله‌ای (v1.6.0).

تضمین می‌کند که:
- هر ۵ مرحله ملزومات استاد تعریف و اعلام‌پذیر است؛
- callback مرحله‌ای خط لوله دقیقاً ۴ مرحله را با payload درست فراخوانی می‌کند؛
- آیتم هر مرحله، پیام «این بخش از نیازمندی استاد برآورده شد» را دارد؛
- گزارش JSON-سازگار و بدون تصویر است.
"""
from __future__ import annotations

import json

import pytest
from PIL import Image

from label_reader.config import Settings
from label_reader.pipeline import LabelReaderPipeline
from label_reader.stages import (
    STAGE_BY_KEY, STAGE_DEFS, STAGE_TTS_KEY, STATUS_FA, build_stage_item,
    done_message, image_quality_metrics, report_json, start_message,
    summary_rows, tts_payload,
)
from tests.conftest import FakeOcrProvider

import io

import numpy as np


def _png() -> bytes:
    img = Image.new("RGB", (900, 700), "white")
    from PIL import ImageDraw, ImageFont
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSans.ttf", 36)
    d.text((60, 60), "Paracetamol 500 mg", font=f, fill="black")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _pipe(lines) -> LabelReaderPipeline:
    return LabelReaderPipeline(Settings(_env_file=None),
                               ocr_provider=FakeOcrProvider(lines))


# ---------- تعریف مراحل (انطباق با ملزومات استاد) ----------

def test_five_stages_match_professor_requirements():
    keys = [s["key"] for s in STAGE_DEFS]
    assert keys == ["opencv", "ocr", "fields", "response", STAGE_TTS_KEY]
    reqs = " ".join(s["requirement_fa"] for s in STAGE_DEFS)
    # عین عبارت‌های کلیدی ملزومات استاد
    for token in ["OpenCV", "تشخیص ناحیه برچسب", "اصلاح زاویه", "بهبود وضوح",
                  "OCR", "پردازش متن و کنترل فیلدها", "قدرت و تعداد درج‌شده",
                  "تولید پاسخ فارسی", "LLM", "وفادار", "TTS + Streamlit",
                  "خواندن اطلاعات و نمایش متن"]:
        assert token in reqs, token


def test_done_message_declares_requirement_fulfilled():
    msg = done_message("۲", "موتور OCR")
    assert "مرحله ۲ از ۵" in msg
    assert "این بخش از نیازمندی استاد برآورده شد" in msg
    assert "در حال اجرا" in start_message("۲", "موتور OCR")


def test_stage_defs_have_files_and_numbers():
    for s in STAGE_DEFS:
        assert s["files_desktop_fa"] and s["files_mobile_fa"]
        assert s["num_fa"] and s["title_fa"]


# ---------- callback مرحله‌ای خط لوله ----------

def test_pipeline_emits_four_stage_payloads_in_order():
    events: list[tuple[str, dict]] = []
    pipe = _pipe([("Paracetamol", 0.96), ("500 mg", 0.96), ("20 Tablets", 0.96)])
    result = pipe.process_pil(Image.open(io.BytesIO(_png())),
                              stage_callback=lambda k, p: events.append((k, p)))
    keys = [k for k, _ in events]
    assert keys == ["opencv", "ocr", "fields", "response"]
    assert result.fields["name"].value == "Paracetamol"

    op = events[0][1]
    assert op["quality_after"]["sharpness"] > 0
    assert op["deskew_applied"] in (True, False)
    assert "original" in op["variants"]
    assert op["image_bgr"] is not None  # فقط در callback؛ در گزارش حذف می‌شود

    oc = events[1][1]
    assert oc["pieces_count"] > 0
    assert oc["chars_total"] > 0
    assert 0.0 <= (oc["mean_confidence"] or 0) <= 1.0
    assert oc["lines_preview"]

    fd = events[2][1]
    assert fd["evidence_coverage"] == 100
    assert fd["status_counts"].get("extracted", 0) >= 3

    rs = events[3][1]
    assert rs["guard_ok"] is True
    assert rs["llm_used"] is False
    assert rs["length"] > 0
    assert rs["preview"]


def test_pipeline_works_without_callback():
    pipe = _pipe([("Paracetamol", 0.96)])
    result = pipe.process_pil(Image.open(io.BytesIO(_png())))
    assert result.response_fa  # بدون callback هم پردازش سالم است


def test_callback_exception_never_breaks_pipeline():
    def bad_cb(key, payload):
        raise RuntimeError("UI error")
    pipe = _pipe([("Paracetamol", 0.96)])
    result = pipe.process_pil(Image.open(io.BytesIO(_png())), stage_callback=bad_cb)
    assert result.response_fa


# ---------- ساخت آیتم هر مرحله ----------

def _events_from_pipe():
    events: list[tuple[str, dict]] = []
    pipe = _pipe([("Paracetamol", 0.96), ("500 mg", 0.96), ("20 Tablets", 0.96)])
    pipe.process_pil(Image.open(io.BytesIO(_png())),
                     stage_callback=lambda k, p: events.append((k, dict(p))))
    return events


def test_build_stage_items_for_all_pipeline_stages():
    for key, payload in _events_from_pipe():
        item = build_stage_item(key, payload)
        assert item["key"] == key
        assert item["status"] in ("done", "warn", "fail")
        assert "نیازمندی استاد برآورده شد" in item["done_message_fa"]
        assert item["requirement_fa"]
        assert item["metrics"] and item["outputs_fa"]
        assert json.dumps(item, ensure_ascii=False, default=str)  # JSON-سازگار


def test_no_text_case_marks_ocr_failed_but_pipeline_survives():
    events: list[tuple[str, dict]] = []
    pipe = _pipe([])
    result = pipe.process_pil(
        Image.open(io.BytesIO(_png())),
        stage_callback=lambda k, p: events.append((k, dict(p))))
    ocr_item = build_stage_item("ocr", dict(events[1][1]))
    assert ocr_item["status"] == "fail"
    assert result.response_fa  # پاسخ امن حداقلی همچنان تولید می‌شود


def test_tts_stage_pending_then_done():
    p1 = tts_payload("edge-tts", "در دسترس است", "سلام ۵۰۰", synthesized=False)
    item1 = build_stage_item(STAGE_TTS_KEY, p1)
    assert item1["status"] == "pending"
    assert STATUS_FA["pending"] in item1["done_label"]
    p2 = tts_payload("edge-tts", "تولید شد", "سلام ۵۰۰", synthesized=True)
    item2 = build_stage_item(STAGE_TTS_KEY, p2)
    assert item2["status"] == "done"
    m2 = {m["name_fa"]: m["value"] for m in item2["metrics"]}
    assert any("تولید شد" in str(v) for v in m2.values())


# ---------- گزارش ----------

def test_summary_rows_and_report_json():
    records = [build_stage_item(k, dict(p)) for k, p in _events_from_pipe()]
    records.append(build_stage_item(
        STAGE_TTS_KEY, tts_payload("edge-tts", "در دسترس", "x", False)))
    rows = summary_rows(records)
    assert len(rows) == 5
    assert all("الزام استاد" in r for r in rows)
    rep = json.loads(report_json(records, {"engine": "fake"}))
    assert rep["report"] == "stage_evaluation_report"
    assert len(rep["stages"]) == 5
    assert "استاد قربانی" in rep["requirement_basis"]
    assert "توصیه" in rep["problem_statement"]
    # گزارش نباید تصویر داشته باشد
    assert "image_bgr" not in json.dumps(rep)


def test_image_quality_metrics_ranges():
    rng = np.random.default_rng(42)
    img = (rng.random((60, 80, 3)) * 255).astype("uint8")
    m = image_quality_metrics(img)
    assert m["sharpness"] >= 0 and m["contrast"] >= 0
    assert 0 <= m["brightness"] <= 255


def test_stage_defs_keys_complete():
    assert set(STAGE_BY_KEY.keys()) == {
        "opencv", "ocr", "fields", "response", STAGE_TTS_KEY}


@pytest.mark.parametrize("key", ["opencv", "ocr", "fields", "response"])
def test_every_stage_item_carries_professor_requirement(key):
    for k, p in _events_from_pipe():
        if k == key:
            item = build_stage_item(k, dict(p))
            assert item["requirement_fa"] == STAGE_BY_KEY[key]["requirement_fa"]
            return
    pytest.fail(f"مرحله {key} از خط لوله اعلام نشد")

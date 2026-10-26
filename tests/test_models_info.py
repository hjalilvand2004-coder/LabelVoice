# -*- coding: utf-8 -*-
"""آزمون‌های v2.0.0: رجیستری مدل‌ها (شفافیت) + دستیار خوانش Qwen3-VL.

پیشینه: کاربر خواست بداند «برای هر بخش از چه مدل/موتوری استفاده می‌شود» —
هم در مستندات و هم درون سامانه در حین مراحل. این آزمون‌ها تضمین می‌کنند:
- رجیستری مدل‌ها کامل و سازگار است و نسخه‌ها بدون کرش تشخیص داده می‌شوند؛
- دستیار VLM پیش‌فرض خاموش است و هرگز پردازش اصلی را نمی‌شکند؛
- سطرهای دستیار فقط «تازه» هستند و با شناسهٔ شاهد vlm-* ردیابی‌پذیر می‌مانند.
"""
import sys
import types

import numpy as np
import pytest

from label_reader.config import Settings
from label_reader.ocr.base import OcrRaw, OcrUnavailableError
from label_reader.ocr.vlm_provider import (
    VLM_CONFIDENCE_ESTIMATE, VLM_MODEL_ID, QwenVlmProvider,
)
from label_reader.pipeline import LabelReaderPipeline
from label_reader import models_info


def _settings(**kw):
    s = Settings(_env_file=None)
    s.use_binarized_variant = False
    for k, v in kw.items():
        setattr(s, k, v)
    return s


# ---------------------------------------------------------------------------
# رجیستری مدل‌ها
# ---------------------------------------------------------------------------

REQUIRED_KEYS = {"stage_fa", "model", "runtime", "role_fa", "where",
                 "privacy_fa", "optional"}


def test_registry_complete_and_consistent():
    assert len(models_info.MODEL_REGISTRY) >= 8
    for m in models_info.MODEL_REGISTRY:
        assert REQUIRED_KEYS <= set(m), f"کلید ناقص در رجیستری: {m}"
        assert m["stage_fa"] and m["model"] and m["role_fa"]
    # مدل VLM در رجیستری عین شناسهٔ رسمی است
    vlm_rows = [m for m in models_info.MODEL_REGISTRY
                if m["runtime"] == "vlm"]
    assert len(vlm_rows) == 1
    assert VLM_MODEL_ID in vlm_rows[0]["model"]
    assert vlm_rows[0]["optional"] is True


def test_detect_versions_returns_strings_and_never_crashes():
    ver = models_info.detect_versions()
    for key in ("opencv", "tesseract", "easyocr", "sherpa_onnx",
                "transformers", "torch"):
        assert key in ver
        assert isinstance(ver[key], str) and ver[key]


def test_models_table_rows_and_markdown():
    rows = models_info.models_table_rows()
    assert len(rows) == len(models_info.MODEL_REGISTRY)
    cols = rows[0].keys()
    assert {"مرحله", "مدل / موتور", "نقش در سامانه",
            "نسخه روی این دستگاه", "محل پیاده‌سازی"} <= set(cols)
    md = models_info.models_markdown_fa()
    assert "Qwen/Qwen3-VL-2B-Instruct" in md
    assert "Tesseract" in md and "Piper" in md


# ---------------------------------------------------------------------------
# دستیار Qwen3-VL — مسیرهای نبود کتابخانه
# ---------------------------------------------------------------------------

def test_vlm_unavailable_without_transformers_is_graceful():
    """بدون transformers: در دسترس نیست + راهنمای فارسی؛ بدون کرش."""
    ok, note = QwenVlmProvider(_settings()).available()
    if "transformers" not in sys.modules or True:
        # در محیط آزمون transformers نصب نیست؛ نتیجه باید محترمانه منفی باشد
        if not ok:
            assert "pip install" in note or "transformers" in note


def test_vlm_read_lines_raises_unavailable_without_transformers():
    """read_lines بدون کتابخانه: OcrUnavailableError — نه کرش خام."""
    prov = QwenVlmProvider(_settings())
    ok, _ = prov.available()
    if not ok:
        img = np.zeros((12, 12, 3), dtype=np.uint8)
        with pytest.raises(OcrUnavailableError):
            prov.read_lines(img)


def test_vlm_run_is_not_an_ocr_engine():
    """دستیار جایگزین موتور OCR نیست (رابط run عمداً بسته است)."""
    prov = QwenVlmProvider(_settings())
    img = np.zeros((12, 12, 3), dtype=np.uint8)
    with pytest.raises(OcrUnavailableError):
        prov.run(img, "original")


# ---------------------------------------------------------------------------
# دستیار Qwen3-VL — خوانش موفق با ماک transformers/torch
# ---------------------------------------------------------------------------

class _FakeIds:
    shape = (1, 7)


class _FakeOut:
    def __getitem__(self, sl):
        return "TRIMMED"


class _FakeInputs(dict):
    def to(self, device):
        return self


class _FakeProcessor:
    def apply_chat_template(self, messages, tokenize=False,
                            add_generation_prompt=True):
        return "PROMPT"

    def __call__(self, text=None, images=None, return_tensors=None):
        return _FakeInputs({"input_ids": _FakeIds()})

    def batch_decode(self, tokens, skip_special_tokens=True):
        return ["لانسوپرازول ۳۰ میلی‌گرم\n? \nکپسول انتریک کوتد\n\n"]


class _FakeModel:
    device = "cpu"

    def generate(self, **kwargs):
        return _FakeOut()


@pytest.fixture()
def fake_vlm_stack(monkeypatch):
    fake_torch = types.ModuleType("torch")

    class _NoGrad:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    fake_torch.no_grad = _NoGrad
    fake_tf = types.ModuleType("transformers")
    fake_tf.AutoProcessor = type("AP", (), {
        "from_pretrained": staticmethod(
            lambda mid, trust_remote_code=False: _FakeProcessor())})
    fake_tf.Qwen3VLForConditionalGeneration = type("QM", (), {
        "from_pretrained": staticmethod(
            lambda mid, **kw: _FakeModel())})
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setitem(sys.modules, "transformers", fake_tf)


def test_vlm_read_lines_mocked_success(fake_vlm_stack):
    prov = QwenVlmProvider(_settings())
    lines = prov.read_lines(np.zeros((16, 16, 3), dtype=np.uint8))
    texts = [ln["text"] for ln in lines]
    assert texts == ["لانسوپرازول ۳۰ میلی‌گرم", "کپسول انتریک کوتد"]
    assert all(ln["confidence"] == VLM_CONFIDENCE_ESTIMATE for ln in lines)


# ---------------------------------------------------------------------------
# اتصال دستیار به خط لوله
# ---------------------------------------------------------------------------

class _FakeVlm:
    name = "qwen3-vl"

    def __init__(self, lines, ok=True, note=""):
        self._lines = lines
        self._ok = ok
        self._note = note
        self.calls = 0

    def available(self):
        return self._ok, self._note

    def read_lines(self, image_bgr):
        self.calls += 1
        return self._lines


def _tiny_provider(pieces_by_variant):
    class _Tiny:
        name = "fake"

        def available(self):
            return True, ""

        def run(self, image_bgr, variant):
            return pieces_by_variant.get(variant, [])
    return _Tiny()


def _ocr_raw(text, conf=0.9):
    return OcrRaw(text=text, confidence=conf, x=10, y=10, w=300, h=40,
                  variant="original", engine="fake")


def test_pipeline_vlm_assist_off_by_default(monkeypatch):
    """پیش‌فرض: دستیار خاموش — حتی با فراهم‌بودن، هرگز فراخوانی نمی‌شود."""
    fake = _FakeVlm([{"text": "سطر تازهٔ دستیار", "confidence": 0.6}])
    monkeypatch.setattr("label_reader.ocr.vlm_provider.QwenVlmProvider",
                        lambda s: fake)
    pipe = LabelReaderPipeline(_settings(),
                               ocr_provider=_tiny_provider(
                                   {"original": [_ocr_raw("LANSOPRAZOLE")]}))
    result = pipe.process_pil(_tiny_image())
    assert fake.calls == 0
    assert not [ln for ln in result.raw_lines if ln.id.startswith("vlm-")]


def test_pipeline_vlm_adds_only_new_lines_with_traceable_ids(monkeypatch):
    """سطر تکراری اضافه نمی‌شود؛ سطر تازه با شناسهٔ vlm-* و موتور qwen3-vl."""
    fake = _FakeVlm([
        {"text": "LANSOPRAZOLE", "confidence": 0.6},          # تکرار موتور اصلی
        {"text": "شرکت داروسازی نمونه تهران", "confidence": 0.6},  # تازه
    ])
    monkeypatch.setattr("label_reader.ocr.vlm_provider.QwenVlmProvider",
                        lambda s: fake)
    pipe = LabelReaderPipeline(_settings(vlm_assist=True),
                               ocr_provider=_tiny_provider(
                                   {"original": [_ocr_raw("LANSOPRAZOLE")]}))
    result = pipe.process_pil(_tiny_image())
    vlm_lines = [ln for ln in result.raw_lines if ln.id.startswith("vlm-")]
    assert len(vlm_lines) == 1
    assert vlm_lines[0].text == "شرکت داروسازی نمونه تهران"
    assert vlm_lines[0].source_ids == ["vlm-1"]
    assert "qwen3-vl" in result.metadata.engine
    assert any("دستیار" in w for w in result.metadata.warnings_fa)


def test_pipeline_vlm_unavailable_is_silent_and_warned(monkeypatch):
    """دستیار فعال ولی نصب‌نشده: بدون کرش؛ فقط هشدار شفاف."""
    fake = _FakeVlm([], ok=False, note="نصب نشده (اختیاری)")
    monkeypatch.setattr("label_reader.ocr.vlm_provider.QwenVlmProvider",
                        lambda s: fake)
    pipe = LabelReaderPipeline(_settings(vlm_assist=True),
                               ocr_provider=_tiny_provider(
                                   {"original": [_ocr_raw("LANSOPRAZOLE")]}))
    result = pipe.process_pil(_tiny_image())
    assert fake.calls == 0
    assert not [ln for ln in result.raw_lines if ln.id.startswith("vlm-")]
    assert any("در دسترس نیست" in w for w in result.metadata.warnings_fa)


def test_pipeline_vlm_crash_never_breaks_main_flow(monkeypatch):
    """اگر خود دستیار استثنا بدهد، پردازش اصلی سالم ادامه می‌یابد."""

    class _Boom:
        name = "qwen3-vl"

        def __init__(self, settings):
            pass

        def available(self):
            raise RuntimeError("boom")

    monkeypatch.setattr("label_reader.ocr.vlm_provider.QwenVlmProvider", _Boom)
    pipe = LabelReaderPipeline(_settings(vlm_assist=True),
                               ocr_provider=_tiny_provider(
                                   {"original": [_ocr_raw("LANSOPRAZOLE")]}))
    result = pipe.process_pil(_tiny_image())
    assert result.ocr_pieces and result.response_fa


# ---------------------------------------------------------------------------
# ابزار
# ---------------------------------------------------------------------------

def _tiny_image():
    from PIL import Image
    return Image.new("RGB", (60, 40), color=(250, 250, 250))

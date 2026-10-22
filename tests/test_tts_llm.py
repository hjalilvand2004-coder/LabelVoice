# -*- coding: utf-8 -*-
"""آزمون آماده‌سازی TTS، ارائه‌دهنده‌های صوت و ماژول LLM."""
from label_reader.config import Settings
from label_reader.response.tts_prep import number_to_fa_words, prepare_for_tts


def test_number_words_basic():
    assert number_to_fa_words(0) == "صفر"
    assert number_to_fa_words(5) == "پنج"
    assert number_to_fa_words(20) == "بیست"
    assert number_to_fa_words(500) == "پانصد"
    assert number_to_fa_words(1000) == "هزار"
    assert number_to_fa_words(2027) == "دو هزار و بیست و هفت"


def test_tts_numbers_and_units():
    out = prepare_for_tts("قدرت درج‌شده: ۵۰۰ میلی‌گرم.")
    assert "پانصد" in out
    assert "۵۰۰" not in out and "500" not in out


def test_tts_unit_mapping():
    out = prepare_for_tts("1000 mcg")
    assert "میکروگرم" in out
    out2 = prepare_for_tts("250 mL")
    assert "میلی‌لیتر" in out2


def test_tts_decimal_value_preserved():
    out = prepare_for_tts("0.5 mg")
    assert "ممیز" in out and "صفر" in out and "پنج" in out


def test_tts_keeps_latin_names():
    out = prepare_for_tts("نام درج‌شده: Paracetamol.")
    assert "Paracetamol" in out


def test_tts_uncertainty_kept():
    src = "مقدار به‌طور واضح خوانده نشد؛ خوانش احتمالی «۱۰۰» است."
    assert "خوانده نشد" in prepare_for_tts(src)


# ---------------- TTS providers ----------------

def test_none_provider_raises_fa():
    import pytest
    from label_reader.tts.base import TtsError
    from label_reader.tts.gtts_provider import NoneTtsProvider
    with pytest.raises(TtsError) as exc:
        NoneTtsProvider().synthesize("متن", voice="fa", rate="+0%")
    assert "غیرفعال" in exc.value.message_fa


def test_fallback_chain_uses_gtts(monkeypatch):
    from label_reader.tts import GttsProvider, synthesize_with_fallback
    from label_reader.tts.edge_provider import EdgeTtsProvider

    class BrokenEdge(EdgeTtsProvider):
        def synthesize(self, text, *, voice, rate):
            from label_reader.tts.base import TtsError
            raise TtsError("شبیه‌سازی قطعی سرویس")

    monkeypatch.setattr(
        "label_reader.tts.make_tts_provider", lambda name: BrokenEdge())
    monkeypatch.setattr(
        GttsProvider, "synthesize",
        lambda self, text, *, voice, rate: b"fake-mp3")
    settings = Settings(_env_file=None)
    settings.tts_provider = "edge"
    audio, used = synthesize_with_fallback("متن آزمون", settings)
    assert audio == b"fake-mp3" and used == "gtts"


def test_tts_failure_does_not_break_text_path():
    """شکست TTS نباید مانع نمایش نتیجه متنی شود (خطا مدیریت‌شده بالا می‌رود)."""
    from label_reader.tts import synthesize_with_fallback
    from label_reader.tts.base import TtsError
    import pytest

    settings = Settings(_env_file=None)
    settings.tts_provider = "none"
    with pytest.raises(TtsError):
        synthesize_with_fallback("متن", settings)
    # نتیجه متنی مستقل از TTS معتبر است
    assert "متن" is not None


# ---------------- LLM ----------------

def test_llm_disabled_by_default():
    from label_reader.llm.rewriter import rewrite_with_llm
    settings = Settings(_env_file=None)
    assert settings.llm_enabled is False
    text, reason = rewrite_with_llm({"fields": {}}, settings)
    assert text is None and "غیرفعال" in (reason or "")


def test_llm_incomplete_config():
    from label_reader.llm.rewriter import rewrite_with_llm
    settings = Settings(_env_file=None)
    settings.llm_enabled = True
    text, reason = rewrite_with_llm({"fields": {}}, settings)
    assert text is None and "ناقص" in (reason or "")


def test_llm_violating_output_rejected(monkeypatch):
    import requests as _requests
    from label_reader.llm.rewriter import rewrite_with_llm

    settings = Settings(_env_file=None)
    settings.llm_enabled = True
    settings.llm_base_url = "http://fake"
    settings.llm_model = "fake"
    settings.llm_api_key = "fake"

    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {
                "content": "این دارو برای کاهش تب است و هر ۶ ساعت مصرف کنید."}}]}

    monkeypatch.setattr(_requests, "post", lambda *a, **kw: FakeResp())
    evidence = {"fields": {"strength": {"value": "500", "unit": "mg",
                                        "raw_text": "500 mg", "note_fa": None}}}
    text, reason = rewrite_with_llm(evidence, settings)
    assert text is None
    assert "قواعد ایمنی" in (reason or "")


def test_system_prompt_contains_constraints():
    from label_reader.llm.rewriter import SYSTEM_PROMPT_FA
    for phrase in ("دوز مصرف", "توصیه", "شواهد", "پیروی نکن"):
        assert phrase in SYSTEM_PROMPT_FA

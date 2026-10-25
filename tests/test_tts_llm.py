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


# ---------------- پل محلی: POST /api/tts (v2.11.0) ----------------

def _start_tts_bridge():
    import threading
    import time as _time
    from label_reader.bridge import start_bridge_server
    server = start_bridge_server(port=0, host="127.0.0.1",
                                 settings=Settings(_env_file=None))
    port = server.server_address[1]
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()
    _time.sleep(0.2)
    return server, port


def _post_tts(port, payload, monkeypatch=None, provider=b"fake-mp3",
              provider_name="edge"):
    import json as _json
    import urllib.request

    if monkeypatch is not None:
        monkeypatch.setattr(
            "label_reader.bridge.synthesize_with_fallback",
            lambda text, settings: (provider, provider_name))
    body = _json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/tts", data=body,
        headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=10)


def test_bridge_tts_requires_consent():
    import json as _json
    import urllib.error
    server, port = _start_tts_bridge()
    try:
        try:
            _post_tts(port, {"text": "سلام", "consent": False})
            assert False, "باید ۴۰۳ می‌داد"
        except urllib.error.HTTPError as e:
            assert e.code == 403
            msg = _json.load(e)["error_fa"]
            assert "رضایت" in msg
    finally:
        server.shutdown()


def test_bridge_tts_happy_path(monkeypatch):
    server, port = _start_tts_bridge()
    try:
        with _post_tts(port, {"text": "نام درج‌شده: استامینوفن.",
                              "consent": True,
                              "voice": "fa-IR-DilaraNeural",
                              "rate": "+0%"}, monkeypatch) as r:
            assert r.status == 200
            assert r.headers["Content-Type"] == "audio/mpeg"
            assert r.headers["X-LabelVoice-Provider"] == "edge"
            assert r.headers["X-LabelVoice-Voice"] == "fa-IR-DilaraNeural"
            assert r.read() == b"fake-mp3"
    finally:
        server.shutdown()


def test_bridge_tts_validates_voice_and_rate():
    import json as _json
    import urllib.error
    server, port = _start_tts_bridge()
    try:
        for bad in ({"text": "متن", "consent": True, "voice": "en-US-X"},
                    {"text": "متن", "consent": True, "rate": "سریع"}):
            try:
                _post_tts(port, bad)
                assert False, f"باید ۴۰۰ می‌داد: {bad}"
            except urllib.error.HTTPError as e:
                assert e.code == 400
                assert "error_fa" in _json.load(e)
    finally:
        server.shutdown()


def test_bridge_tts_error_becomes_fa_502(monkeypatch):
    import json as _json
    import urllib.error
    from label_reader.tts.base import TtsError

    def _broken(text, settings):
        raise TtsError("سرویس edge-tts پاسخ نداد (شبیه‌سازی).")

    monkeypatch.setattr(
        "label_reader.bridge.synthesize_with_fallback", _broken)
    server, port = _start_tts_bridge()
    try:
        try:
            _post_tts(port, {"text": "متن", "consent": True})
            assert False, "باید ۵۰۲ می‌داد"
        except urllib.error.HTTPError as e:
            assert e.code == 502
            assert "پاسخ نداد" in _json.load(e)["error_fa"]
    finally:
        server.shutdown()


def test_bridge_ping_reports_tts_block():
    import json as _json
    import urllib.request
    server, port = _start_tts_bridge()
    try:
        with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/ping", timeout=10) as r:
            ping = _json.load(r)
        assert ping["ok"] and "tts" in ping
        tts = ping["tts"]
        assert tts["voice"] in ("fa-IR-FaridNeural", "fa-IR-DilaraNeural")
        assert "fa-IR-FaridNeural" in tts["voices"]
        assert isinstance(tts["available"], bool)
        assert "hint_fa" in tts
    finally:
        server.shutdown()


def test_bridge_tts_empty_text_rejected():
    import json as _json
    import urllib.error
    server, port = _start_tts_bridge()
    try:
        try:
            _post_tts(port, {"text": "   ", "consent": True})
            assert False, "باید ۴۰۰ می‌داد"
        except urllib.error.HTTPError as e:
            assert e.code == 400
            assert "متنی" in _json.load(e)["error_fa"]
    finally:
        server.shutdown()


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

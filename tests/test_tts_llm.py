# -*- coding: utf-8 -*-
"""آزمون آماده‌سازی TTS، ارائه‌دهندهٔ صوتی لوکال و ماژول LLM (v2.12.0).

v2.12.0: سرویس‌های آنلاین (edge-tts/gTTS) حذف شدند؛ تبدیل گفتار فقط
«لوکال» است — مدل Piper fa_IR-amir-medium داخل فایل‌های پروژه.
"""
from label_reader.bridge import BRIDGE_VERSION
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


# ---------------- TTS لوکال (v2.12.0) ----------------

def test_none_provider_raises_fa():
    import pytest
    from label_reader.tts import NoneTtsProvider
    from label_reader.tts.base import TtsError
    with pytest.raises(TtsError) as exc:
        NoneTtsProvider().synthesize("متن", voice="", rate="+0%")
    assert "غیرفعال" in exc.value.message_fa


def test_rate_to_speed_parity_with_js():
    """پاریتی کامل با js/tts.js → rateToSpeed."""
    from label_reader.tts.local_provider import rate_to_speed
    assert rate_to_speed("+0%") == 1.0
    assert rate_to_speed("+10%") == 1.1
    assert rate_to_speed("-15%") == 0.85
    assert rate_to_speed("") == 1.0
    assert rate_to_speed("نامعتبر") == 1.0
    assert rate_to_speed("+500%") == 2.0   # سقف
    assert rate_to_speed("-200%") == 0.5   # کف


def test_local_provider_unavailable_without_model(monkeypatch):
    from label_reader.tts import local_provider

    monkeypatch.setattr(local_provider, "find_model_dir", lambda: None)
    prov = local_provider.LocalPiperProvider()
    ok, hint = prov.available()
    assert ok is False
    assert ("sherpa-onnx" in hint) or ("مدل صوتی" in hint)


def test_local_provider_unavailable_when_sherpa_missing(monkeypatch):
    """اگر بسته نصب نباشد، پیام فارسی راهنما برگردد."""
    import builtins
    from label_reader.tts import local_provider

    monkeypatch.setattr(local_provider, "find_model_dir", lambda: None)
    real_import = builtins.__import__

    def fake_import(name, *a, **kw):
        if name == "sherpa_onnx":
            raise ImportError("no sherpa")
        return real_import(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    prov = local_provider.LocalPiperProvider()
    ok, hint = prov.available()
    assert ok is False and "sherpa" in hint


def test_local_provider_synthesizes_wav(monkeypatch):
    import struct
    from label_reader.tts import local_provider

    class FakeAudio:
        samples = [0.1, -0.1, 0.2, -0.2] * 64
        sample_rate = 22050

    class FakeTts:
        def generate(self, text, sid=0, speed=1.0):
            assert 0.5 <= speed <= 2.0
            return FakeAudio()

    prov = local_provider.LocalPiperProvider()
    monkeypatch.setattr(prov, "_get_engine", lambda: FakeTts())
    data = prov.synthesize("نام درج‌شده: استامینوفن.", voice="", rate="+10%")
    assert data[:4] == b"RIFF" and data[8:12] == b"WAVE"
    rate = struct.unpack("<I", data[24:28])[0]
    assert rate == 22050
    assert len(data) > 44


def test_samples_to_wav_bytes_header():
    import struct
    from label_reader.tts.local_provider import samples_to_wav_bytes
    data = samples_to_wav_bytes([0.0, 0.5, -0.5], 22050)
    assert struct.unpack("<I", data[40:44])[0] == 6  # ۳ نمونه × ۲ بایت
    assert struct.unpack("<H", data[22:24])[0] == 1  # مونو


def test_fallback_is_local_only(monkeypatch):
    from label_reader.tts import LocalPiperProvider, synthesize_with_fallback

    settings = Settings(_env_file=None)
    settings.tts_provider = "local"
    monkeypatch.setattr(
        LocalPiperProvider, "synthesize",
        lambda self, text, *, voice, rate: b"fake-wav")
    audio, used = synthesize_with_fallback("متن آزمون", settings)
    assert audio == b"fake-wav" and used == "local"


def test_no_online_providers_remain():
    """خط قرمز v2.12.0: هیچ سرویس آنلاینی در کد TTS فراخوانی نشود."""
    import pathlib
    tts_dir = pathlib.Path("label_reader/tts")
    forbidden = ("import edge_tts", "from gtts", "import gtts",
                 "gTTS(", "Communicate(")
    for f in tts_dir.glob("*.py"):
        src = f.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in src, (f, token)
    assert not (tts_dir / "edge_provider.py").exists()
    assert not (tts_dir / "gtts_provider.py").exists()


# ---------------- پل محلی: فقط OCR (v2.12.0 — TTS حذف شد) ----------------

def _start_bridge():
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


def test_bridge_tts_endpoint_removed():
    """POST /api/tts دیگر وجود ندارد (v2.12.0 — صدا کاملاً در مرورگر لوکال)."""
    import json as _json
    import urllib.error
    import urllib.request
    server, port = _start_bridge()
    try:
        body = _json.dumps({"text": "سلام", "consent": True}).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/tts", data=body,
            headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=10)
            assert False, "باید ۴۰۴ می‌داد"
        except urllib.error.HTTPError as e:
            assert e.code == 404
            assert "مسیر ناشناخته" in _json.load(e)["error_fa"]
    finally:
        server.shutdown()


def test_bridge_ping_without_tts_block():
    import json as _json
    import urllib.request
    server, port = _start_bridge()
    try:
        with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/ping", timeout=10) as r:
            ping = _json.load(r)
        assert ping["ok"] and ping["version"] == BRIDGE_VERSION  # با ثابت پل مقایسه شود — نه نسخهٔ ثابت شکننده
        assert "tts" not in ping          # v2.12.0: بلوک TTS حذف شد
        assert isinstance(ping["engines"], list)
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

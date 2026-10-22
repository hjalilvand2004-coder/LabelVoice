# -*- coding: utf-8 -*-
"""کارخانه TTS با جایگزینی خودکار (edge → gtts) و مدیریت شفاف شکست."""
from __future__ import annotations

from ..config import Settings
from .base import TtsError, TtsProvider
from .edge_provider import EdgeTtsProvider
from .gtts_provider import GttsProvider, NoneTtsProvider

_PROVIDERS = {
    "edge": EdgeTtsProvider,
    "gtts": GttsProvider,
    "none": NoneTtsProvider,
}


def make_tts_provider(name: str) -> TtsProvider:
    key = (name or "").strip().lower()
    cls = _PROVIDERS.get(key)
    if cls is None:
        raise TtsError(f"ارائه‌دهنده TTS ناشناخته است: {name} (گزینه‌ها: edge، gtts، none)")
    return cls()


def synthesize_with_fallback(
    text: str, settings: Settings
) -> tuple[bytes, str]:
    """تولید صوت با جایگزینی خودکار؛ هرگز خطا را قورت نمی‌دهد.

    بازگشت: (mp3 bytes، نام ارائه‌دهنده استفاده‌شده)
    خطا در صورت شکست هر دو ارائه‌دهنده بالا می‌رود (UI نتیجه متنی را نمایش می‌دهد).
    """
    primary = make_tts_provider(settings.tts_provider)
    if primary.name == "none":
        raise TtsError(NoneTtsProvider().available()[1])
    try:
        return primary.synthesize(text, voice=settings.tts_voice,
                                  rate=settings.tts_rate), primary.name
    except TtsError:
        if primary.name == "edge":
            fallback = GttsProvider()
            ok, _ = fallback.available()
            if ok:
                return fallback.synthesize(text, voice="fa", rate="+0%"), "gtts"
        raise

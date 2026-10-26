# -*- coding: utf-8 -*-
"""کارخانه TTS — فقط لوکال (v2.12.0)

مدل Piper fa_IR-amir-medium داخل فایل‌های پروژه است و با sherpa-onnx اجرا
می‌شود. سرویس‌های آنلاین (edge-tts / gTTS) در v2.12.0 به‌کلی حذف شدند —
هیچ متنی از دستگاه خارج نمی‌شود.
"""
from __future__ import annotations

from ..config import Settings
from .base import TtsError, TtsProvider
from .local_provider import LocalPiperProvider


class NoneTtsProvider(TtsProvider):
    """وقتی TTS روی none تنظیم شده یا موتور در دسترس نیست."""

    name = "none"

    def available(self) -> tuple[bool, str]:
        return False, "تبدیل گفتار غیرفعال است (تنظیمات: tts_provider=none)."

    def synthesize(self, text: str, *, voice: str, rate: str) -> bytes:
        raise TtsError("تبدیل گفتار غیرفعال است؛ نتیجهٔ متنی بدون تغییر نمایش داده می‌شود.")


_PROVIDERS = {
    "local": LocalPiperProvider,
    "none": NoneTtsProvider,
}


def make_tts_provider(name: str) -> TtsProvider:
    key = (name or "").strip().lower()
    cls = _PROVIDERS.get(key)
    if cls is None:
        raise TtsError(
            f"ارائه‌دهندهٔ TTS ناشناخته است: {name} (گزینه‌ها: local، none)")
    return cls()


def synthesize_with_fallback(text: str, settings: Settings) -> tuple[bytes, str]:
    """تولید صوت با موتور لوکال؛ بدون جایگزین آنلاین (خط قرمز پروژه).

    بازگشت: (wav bytes، نام ارائه‌دهندهٔ استفاده‌شده)
    """
    primary = make_tts_provider(settings.tts_provider)
    if primary.name == "none":
        raise TtsError(NoneTtsProvider().available()[1])
    return primary.synthesize(text, voice=settings.tts_voice,
                              rate=settings.tts_rate), primary.name

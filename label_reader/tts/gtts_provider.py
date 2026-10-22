# -*- coding: utf-8 -*-
"""ارائه‌دهنده جایگزین gTTS — ساده‌تر، صدای مکانیکی‌تر، بدون کنترل سرعت.

نیازمند اینترنت است و متن را به سرویس ابری گوگل می‌فرستد.
"""
from __future__ import annotations

import io

from .base import TtsError, TtsProvider


class GttsProvider(TtsProvider):
    name = "gtts"

    def available(self) -> tuple[bool, str]:
        try:
            from gtts import gTTS  # noqa: F401
        except Exception:
            return False, ("gTTS نصب نیست: «pip install gtts». "
                           "این سرویس نیازمند اینترنت است.")
        return True, ("صدای فارسی gTTS نیازمند ارسال متن به سرویس ابری گوگل است؛ "
                      "فقط با رضایت شما فراخوانی می‌شود. کنترل سرعت ندارد.")

    def synthesize(self, text: str, *, voice: str, rate: str) -> bytes:
        try:
            from gtts import gTTS
        except Exception as exc:
            raise TtsError("gTTS نصب نیست؛ صوت تولید نشد.") from exc
        try:
            tts = gTTS(text=text, lang="fa")
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            return buf.getvalue()
        except Exception as exc:
            raise TtsError(
                "سرویس gTTS پاسخ نداد (احتمالاً اینترنت قطع است). "
                "نتیجه متنی بدون تغییر نمایش داده می‌شود.") from exc


class NoneTtsProvider(TtsProvider):
    """وقتی TTS روی none تنظیم شده یا سرویس‌ها در دسترس نیستند."""

    name = "none"

    def available(self) -> tuple[bool, str]:
        return False, "تبدیل گفتار غیرفعال است (تنظیمات: tts_provider=none)."

    def synthesize(self, text: str, *, voice: str, rate: str) -> bytes:
        raise TtsError("تبدیل گفتار غیرفعال است؛ نتیجه متنی بدون تغییر نمایش داده می‌شود.")

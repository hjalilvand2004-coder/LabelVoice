# -*- coding: utf-8 -*-
"""رابط مشترک ارائه‌دهنده‌های TTS فارسی.

توجه حریم خصوصی: ارائه‌دهنده‌های edge-tts و gTTS متن را به سرویس ابری
می‌فرستند؛ فراخوانی آن‌ها فقط با رضایت صریح کاربر (چک‌باکس رابط) انجام شود.
"""
from __future__ import annotations

import abc


class TtsError(RuntimeError):
    def __init__(self, message_fa: str):
        super().__init__(message_fa)
        self.message_fa = message_fa


class TtsProvider(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    def available(self) -> tuple[bool, str]:
        """(در دسترس؟، توضیح فارسی)"""

    @abc.abstractmethod
    def synthesize(self, text: str, *, voice: str, rate: str) -> bytes:
        """تولید صوت mp3؛ در صورت شکست TtsError با پیام فارسی."""


EDGE_VOICES = [
    "fa-IR-FaridNeural",   # مرد
    "fa-IR-DilaraNeural",  # زن
]

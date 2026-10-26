# -*- coding: utf-8 -*-
"""رابط مشترک ارائه‌دهنده‌های TTS فارسی.

v2.12.0 — حریم خصوصی: تبدیل گفتار «کاملاً محلی» است (Piper fa_IR-amir-medium
با sherpa-onnx)؛ هیچ متنی به هیچ سرویس ابری ارسال نمی‌شود و رضایتِ
«ارسال به سرویس ابری» دیگر موضوعیت ندارد.
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
        """تولید صوت (WAV)؛ در صورت شکست TtsError با پیام فارسی."""

# -*- coding: utf-8 -*-
"""ارائه‌دهنده TTS مایکروسافت (edge-tts) — صدای فارسی طبیعی.

نیازمند اینترنت است. سرعت خوانش با پارامتر rate (مثل +10% یا -15%) تنظیم
می‌شود. شکست این سرویس نباید مانع نمایش نتیجه متنی شود (در pipeline و UI
مدیریت می‌شود).
"""
from __future__ import annotations

import asyncio

from .base import TtsError, TtsProvider


class EdgeTtsProvider(TtsProvider):
    name = "edge"

    def available(self) -> tuple[bool, str]:
        try:
            import edge_tts  # noqa: F401
        except Exception:
            return False, ("edge-tts نصب نیست: «pip install edge-tts». "
                           "این سرویس نیازمند اینترنت است.")
        return True, ("صدای فارسی edge-tts نیازمند ارسال متن به سرویس ابری "
                      "مایکروسافت است؛ فقط با رضایت شما فراخوانی می‌شود.")

    def synthesize(self, text: str, *, voice: str, rate: str) -> bytes:
        try:
            import edge_tts
        except Exception as exc:
            raise TtsError("edge-tts نصب نیست؛ صوت تولید نشد.") from exc

        async def _run() -> bytes:
            communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
            buf = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buf.extend(chunk["data"])
            return bytes(buf)

        try:
            audio = asyncio.run(_run())
        except Exception as exc:
            raise TtsError(
                "سرویس edge-tts پاسخ نداد (احتمالاً اینترنت قطع است). "
                "نتیجه متنی بدون تغییر نمایش داده می‌شود.") from exc
        if not audio:
            raise TtsError("سرویس edge-tts صدای خالی برگرداند.")
        return audio

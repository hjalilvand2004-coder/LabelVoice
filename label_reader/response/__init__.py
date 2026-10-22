# -*- coding: utf-8 -*-
"""زیرسیستم پاسخ: سازنده قالبی، نگهبان ایمنی و آماده‌سازی TTS."""
from .builder import build_response, format_strength, format_count, DISCLAIMER_FA
from .guard import validate_text, validate_llm_output, GuardReport
from .tts_prep import prepare_for_tts, number_to_fa_words

__all__ = [
    "build_response", "format_strength", "format_count", "DISCLAIMER_FA",
    "validate_text", "validate_llm_output", "GuardReport",
    "prepare_for_tts", "number_to_fa_words",
]

# -*- coding: utf-8 -*-
"""ارائه‌دهندهٔ TTS کاملاً لوکال — مدل Piper fa_IR-amir-medium (v2.12.0)

مدل دانلودشده و داخل فایل‌های پروژه قرار دارد:
    models/tts/piper-fa_IR-amir/
        model.onnx          ← وزن‌های fp32 (کیفیت کامل — منبع: rhasspy/piper-voices v1.0.0)
        model.int8.onnx     ← نسخهٔ کوانتیزهٔ int8 (سبک — همان صدای رابط وب/موبایل)
        tokens.txt          ← نگاشت فونم به شناسه
        espeak-ng-data/     ← دادهٔ فونِم‌ساز espeak-ng (fa + en)
        fa_IR-amir-medium.onnx.json ← پیکربندی Piper (نرخ نمونه/مقیاس‌ها)

اجرای استنتاج با sherpa-onnx (نسخهٔ 1.12.x — دارای فونِم‌ساز espeak-ng داخلی).
هیچ درخواست شبکه‌ای انجام نمی‌شود؛ سرعت خوانش با rate (مثل +10%) تنظیم
می‌شود که دقیقاً همان قاعدهٔ سمت مرورگر (js/tts.js) است.
"""
from __future__ import annotations

import io
import os
import re
import struct
import wave
from pathlib import Path

from .base import TtsError, TtsProvider

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR_ENV = "LBR_TTS_MODEL_DIR"

RATE_RE = re.compile(r"^[+-]\d{1,3}%$")


def rate_to_speed(rate: str) -> float:
    """«+10%» → 1.1 و «-15%» → 0.85 — پاریتی کامل با js/tts.js (rateToSpeed)."""
    r = str(rate or "")
    pct = int(r[:-1]) if RATE_RE.match(r) else 0
    return max(0.5, min(2.0, 1.0 + pct / 100.0))


def find_model_dir() -> Path | None:
    """پوشهٔ مدل: اولویت متغیر محیط، سپس models/tts/piper-fa_IR-amir پروژه."""
    env = os.environ.get(MODEL_DIR_ENV, "").strip()
    if env:
        p = Path(env)
        if p.is_dir():
            return p
    default = _PROJECT_ROOT / "models" / "tts" / "piper-fa_IR-amir"
    return default if default.is_dir() else None


def _find_weights(d: Path) -> Path | None:
    fp32 = d / "model.onnx"
    int8 = d / "model.int8.onnx"
    if fp32.exists():
        return fp32
    if int8.exists():
        return int8
    return None


def samples_to_wav_bytes(samples, sample_rate: int) -> bytes:
    """Float32 نمونه‌ها ([-1,1]) → بایت‌های WAV 16بیتی مونو."""
    import numpy as np

    arr = np.clip(np.asarray(samples, dtype=np.float32), -1.0, 1.0)
    pcm = (arr * 32767.0).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(int(sample_rate))
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


class LocalPiperProvider(TtsProvider):
    """مدل صوتی لوکال Piper — بدون اینترنت، بدون سرویس ابری، بدون TTS دستگاه."""

    name = "local"

    def __init__(self) -> None:
        self._tts = None            # کش موتور sherpa
        self._engine_model: Path | None = None

    # ---------- وضعیت ----------
    def available(self) -> tuple[bool, str]:
        try:
            import sherpa_onnx  # noqa: F401
        except Exception:
            return False, (
                "بستهٔ sherpa-onnx نصب نیست: «pip install sherpa-onnx==1.12.40». "
                "تبدیل گفتار کاملاً محلی است و به اینترنت نیازی ندارد.")
        d = find_model_dir()
        if d is None or _find_weights(d) is None or not (d / "tokens.txt").exists():
            return False, (
                "مدل صوتی لوکال یافت نشد؛ پوشهٔ «models/tts/piper-fa_IR-amir/» "
                "(شامل model.onnx یا model.int8.onnx + tokens.txt + espeak-ng-data) "
                "باید در فایل‌های پروژه موجود باشد.")
        return True, (
            "مدل صوتی «Piper — fa_IR-amir-medium» به‌صورت کاملاً محلی روی همین "
            "دستگاه اجرا می‌شود؛ بدون اینترنت و بدون ارسال متن به هر سرویسی.")

    # ---------- موتور ----------
    def _get_engine(self):
        import sherpa_onnx

        d = find_model_dir()
        weights = _find_weights(d) if d else None
        if weights is None:
            raise TtsError("مدل صوتی لوکال یافت نشد؛ پوشهٔ models/tts را بررسی کنید.")
        if self._tts is not None and self._engine_model == weights:
            return self._tts
        cfg = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                    model=str(weights),
                    tokens=str(d / "tokens.txt"),
                    data_dir=str(d / "espeak-ng-data"),
                ),
            ),
            max_num_sentences=1,
        )
        self._tts = sherpa_onnx.OfflineTts(cfg)
        self._engine_model = weights
        return self._tts

    # ---------- سنتز ----------
    def synthesize(self, text: str, *, voice: str = "", rate: str = "+0%") -> bytes:
        clean = (text or "").strip()
        if not clean:
            raise TtsError("متنی برای خواندن وجود ندارد.")
        try:
            tts = self._get_engine()
        except TtsError:
            raise
        except Exception as exc:  # noqa: BLE001 — خطای موتور با پیام فارسی
            raise TtsError(
                "موتور صوتی لوکال راه‌اندازی نشد. بستهٔ sherpa-onnx 1.12.x لازم است "
                "(نسخهٔ 2.x فونِم‌ساز داخلی ندارد).") from exc
        try:
            audio = tts.generate(clean, sid=0, speed=rate_to_speed(rate))
        except Exception as exc:  # noqa: BLE001
            raise TtsError("تولید صدا با مدل لوکال ناموفق بود؛ "
                           "نتیجهٔ متنی بدون تغییر نمایش داده می‌شود.") from exc
        if audio is None or len(audio.samples) == 0:
            raise TtsError("مدل صوتی، صدای خالی تولید کرد (کاراکترهای پشتیبانی‌نشده؟).")
        return samples_to_wav_bytes(audio.samples, audio.sample_rate)


# سازگاری نام قدیمی‌ترِ داخل پروژه
SherpaLocalProvider = LocalPiperProvider

# ثابت‌های نمایشی (جایگزین EDGE_VOICES حذف‌شده)
LOCAL_VOICES = ["fa_IR-amir-medium (Piper — کاملاً لوکال)"]

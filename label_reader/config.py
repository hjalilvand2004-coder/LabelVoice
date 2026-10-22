# -*- coding: utf-8 -*-
"""پیکربندی مرکزی برنامه — همه محدودیت‌ها و آستانه‌ها قابل تنظیم‌اند.

کلیدهای محیطی با پیشوند LBR_ خوانده می‌شوند (مثلاً LBR_MAX_FILE_MB=5).
فایل .env.example نمونه تنظیمات بدون اطلاعات محرمانه است.
کلیدهای API فقط از متغیر محیط یا secrets خوانده می‌شوند.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# ریشه پروژه: پوشهٔ بالاتر از بسته label_reader
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LBR_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ---------- محدودیت‌های تصویر (جلوگیری از مصرف بیش از حد حافظه) ----------
    max_file_mb: int = 10
    max_pixels: int = 30_000_000
    max_side_px: int = 4000

    # ---------- آستانه‌های کیفیت (هیوریستیک؛ قابل تنظیم) ----------
    blur_laplacian_threshold: float = 45.0
    severe_blur_threshold: float = 18.0
    glare_highlight_ratio: float = 0.10
    dark_mean_brightness: float = 55.0
    bright_mean_brightness: float = 225.0
    min_dimension_px: int = 300

    # ---------- پیش‌پردازش ----------
    target_min_side: int = 1000
    clahe_clip_limit: float = 2.0
    clahe_tile_size: int = 8
    deskew_max_angle_deg: float = 15.0
    use_binarized_variant: bool = True

    # ---------- OCR ----------
    # tesseract | easyocr | auto (اولین موتور در دسترس)
    ocr_provider: str = "tesseract"
    tessdata_dir: Path = PROJECT_ROOT / "models" / "tessdata"
    ocr_languages: str = "fas+eng"
    tesseract_psm: int = 3
    # اجرای دوم با psm دیگر برای پوشش بهتر سطرها (0 = غیرفعال)
    tesseract_extra_psm: int = 6
    easyocr_model_dir: Path | None = None

    # ---------- استخراج فیلدها ----------
    low_confidence_threshold: float = 0.55

    # ---------- TTS فارسی ----------
    # edge | gtts | none
    tts_provider: str = "edge"
    tts_voice: str = "fa-IR-FaridNeural"
    tts_rate: str = "+0%"

    # ---------- LLM اختیاری (پیش‌فرض: خاموش؛ مسیر اصلی بدون LLM کار می‌کند) ----------
    llm_enabled: bool = False
    llm_base_url: str = ""
    llm_model: str = ""
    llm_api_key: str = ""  # فقط از متغیر محیط/secret؛ هرگز در کد هاردکد نشود
    llm_timeout_s: int = 30


def load_settings() -> Settings:
    return Settings()

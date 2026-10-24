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
    # 1000: مقیاس بهینه آزمایش‌شده (۱۴۰۰ حروف درشت را برای تسراکت بیش‌ازحد بزرگ می‌کند)
    target_min_side: int = 1000
    clahe_clip_limit: float = 2.0
    clahe_tile_size: int = 8
    deskew_max_angle_deg: float = 15.0
    use_binarized_variant: bool = True
    use_white_on_dark_variant: bool = True
    # v1.8.0: جداسازی جوهر رنگی (255 - بیشینهٔ کانال) برای متن رنگی روی زمینه روشن
    use_ink_isolated_variant: bool = True

    # ---------- OCR ----------
    # tesseract | easyocr | surya | auto (اولین موتور در دسترس)
    ocr_provider: str = "tesseract"
    tessdata_dir: Path = PROJECT_ROOT / "models" / "tessdata"
    ocr_languages: str = "fas+eng"
    # v1.8.0: استراتژی زبان تطبیقی — «fas» و «eng» جدا اجرا می‌شوند نه ترکیبی؛
    # ترکیب fas+eng باعث تزریق حروف لاتین به کلمات فارسی می‌شود (ریشهٔ خروجی آشغال).
    # adaptive: کاوش اول با fas؛ اگر متن فارسی‌غالب بود eng کلاً اجرا نمی‌شود.
    ocr_language_strategy: str = "adaptive"
    tesseract_psm: int = 3
    # اجرای دوم با psm دیگر برای پوشش بهتر سطرها (0 = غیرفعال)
    tesseract_extra_psm: int = 6
    # اجرای سوم با PSM پراکنده (Sparse) برای برچسب‌هایی با متن پراکنده (0 = غیرفعال)
    tesseract_sparse_psm: int = 11
    easyocr_model_dir: Path | None = None
    # v1.8.0: موتور دوم (EasyOCR) به‌عنوان مکمل Tesseract برای نواحی ناخوانا؛
    # در نبود easyocr بی‌صدا رد می‌شود. فقط دسکتاپ (موبایل WASM پشتیبانی نمی‌کند).
    dual_engine: bool = True
    easyocr_variants: str = "original,gray_clahe"

    # v2.2.0: موتور سوم اختیاری (Surya) — به انتخاب صریح کاربر فعال می‌شود؛
    # در زنجیرهٔ «auto» قرار ندارد تا اجرای پیش‌فرض سریع و پیش‌بینی‌پذیر بماند.
    # surya-ocr>=0.17 تک‌مدل چندزبانه است (فارسی را بدون تعیین زبان می‌خواند).
    surya_model_dir: Path | None = None
    # نسخه‌هایی که سوریا روی‌شان اجرا می‌شود (سنگین است؛ کمینهِ کافی):
    surya_variants: str = "original,gray_clahe"

    # ---------- گیت کیفیت قطعه‌های OCR (v1.7.0) ----------
    # کف مطلق اطمینان: قطعه زیر این مقدار همیشه حذف می‌شود
    piece_conf_floor: float = 0.30
    # قطعه‌های کوتاه (≤ این طول) باید اطمینان بیشتری داشته باشند
    # (۰٫۳۰ = برابر کف مطلق تا واحدهای معنی‌دار کم‌اطمینان مثل «mg» حذف نشوند)
    short_piece_max_len: int = 2
    short_piece_conf_min: float = 0.30
    # کمینه اطمینان برای اینکه سطر «کاندید نام» معتبر شود
    name_min_confidence: float = 0.45

    # ---------- رأی‌گیری اجماعی (v1.8.0) ----------
    # قطعه‌ای که فقط در «یک» پیکربندی (واریانت×PSM×زبان) دیده شود و اطمینانش
    # زیر این کف باشد حذف می‌شود (نویز تک‌پیکربندی). متن پرتکرار سالم می‌ماند.
    lonely_piece_conf: float = 0.55
    # فیلتر اجماع فقط وقتی قطعه‌های کافی وجود دارد اعمال می‌شود تا تصاویر
    # کم‌متن خالی نمانند.
    min_pieces_for_consensus: int = 6

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

    # ---------- دستیار خوانش دوم VLM (v2.0.0 — پیش‌فرض: خاموش) ----------
    # مدل: Qwen/Qwen3-VL-2B-Instruct — اجرای کاملاً محلی با transformers؛
    # فقط سطرهای تازه (غیرتکراری) با شناسهٔ شاهد vlm-* اضافه می‌شود.
    vlm_assist: bool = False
    vlm_model_id: str = "Qwen/Qwen3-VL-2B-Instruct"
    vlm_max_lines: int = 60


def load_settings() -> Settings:
    return Settings()

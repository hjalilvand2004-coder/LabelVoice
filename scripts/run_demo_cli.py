# -*- coding: utf-8 -*-
"""اجرای خط پردازش روی یک تصویر از خط فرمان (بدون رابط کاربری).

نمونه:
  python scripts/run_demo_cli.py sample_images/en_paracetamol_500mg.png
  python scripts/run_demo_cli.py sample.png --engine easyocr --json out.json
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from label_reader.config import load_settings  # noqa: E402
from label_reader.models import FieldStatus  # noqa: E402
from label_reader.pipeline import LabelReaderPipeline  # noqa: E402
from label_reader.validation import validate_and_load  # noqa: E402

STATUS_FA = {
    FieldStatus.EXTRACTED: "استخراج‌شده", FieldStatus.UNCERTAIN: "نامطمئن",
    FieldStatus.MISSING: "غایب", FieldStatus.CONFLICTING: "متناقض",
    FieldStatus.USER_CORRECTED: "اصلاح کاربر",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="برچسب‌خوان هوشمند — اجرای خط فرمان")
    parser.add_argument("image", type=Path, help="مسیر تصویر برچسب (JPG/PNG)")
    parser.add_argument("--engine", default=None,
                        choices=["tesseract", "easyocr", "auto"],
                        help="موتور OCR (پیش‌فرض: تنظیمات)")
    parser.add_argument("--json", type=Path, default=None,
                        help="ذخیره خروجی JSON کامل در مسیر داده‌شده")
    args = parser.parse_args()

    if not args.image.exists():
        print(f"تصویر یافت نشد: {args.image}")
        return 1
    data = args.image.read_bytes()
    settings = load_settings()
    if args.engine:
        settings.ocr_provider = args.engine
    pipeline = LabelReaderPipeline(settings)

    result = pipeline.process_bytes(data)
    print("=" * 60)
    print("پاسخ فارسی:")
    print(result.response_fa)
    print("=" * 60)
    print("فیلدها:")
    for field in result.fields.values():
        conf = f"{round(field.confidence * 100)}%" \
            if field.confidence is not None else "—"
        print(f"  {field.label_fa:32} | {str(field.value):28} | "
              f"{STATUS_FA.get(field.status, field.status):10} | اطمینان: {conf} | "
              f"شواهد: {','.join(field.source_ids) or '—'}")
    print("=" * 60)
    print(f"موتور: {result.metadata.engine} | نسخه‌ها: "
          f"{','.join(result.metadata.variants_used)} | "
          f"زمان کل: {result.metadata.durations_ms.get('total_ms', '—')} ms")
    print(f"قطعات OCR: {len(result.ocr_pieces)} | سطرها: {len(result.raw_lines)}")
    if args.json:
        args.json.write_bytes(result.to_json_bytes())
        print(f"خروجی JSON ذخیره شد: {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

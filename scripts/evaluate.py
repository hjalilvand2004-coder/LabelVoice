# -*- coding: utf-8 -*-
"""سنجش واقعی دقت استخراج روی مجموعه نمونه برچسب‌خورده (sample_images/manifest.json).

هیچ عددی جعل نمی‌شود: فقط نتایج اجرای واقعی در همین محیط چاپ می‌شود.
اجرا: python scripts/evaluate.py [--engine tesseract]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from label_reader.config import load_settings  # noqa: E402
from label_reader.models import FieldStatus  # noqa: E402
from label_reader.pipeline import LabelReaderPipeline  # noqa: E402


def norm_strength(value: str | None, unit: str | None) -> str:
    if not value:
        return ""
    return value if not unit else f"{value} {unit}"


def check(field, expected_raw: str) -> bool:
    if field is None or field.status in (FieldStatus.MISSING, FieldStatus.CONFLICTING):
        return False
    got = field.value or ""
    exp = expected_raw.strip()
    if field.unit and field.key in ("strength", "count", "net_weight"):
        got_full = f"{got} {field.unit}"
        return exp.lower() in got_full.lower() or got_full.lower() == exp.lower()
    return got.lower() == exp.lower() or exp.lower() in got.lower()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", default=None)
    args = parser.parse_args()

    manifest_path = ROOT / "sample_images" / "manifest.json"
    if not manifest_path.exists():
        print("manifest یافت نشد؛ ابتدا scripts/make_sample_images.py را اجرا کنید.")
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    settings = load_settings()
    if args.engine:
        settings.ocr_provider = args.engine
    pipeline = LabelReaderPipeline(settings)

    rows = []
    total_fields = matched = 0
    total_time = 0.0
    for name, meta in sorted(manifest.items()):
        img_path = ROOT / "sample_images" / name
        if not img_path.exists():
            continue
        t0 = time.perf_counter()
        try:
            result = pipeline.process_bytes(img_path.read_bytes())
        except Exception as exc:  # noqa: BLE001
            rows.append((name, meta["case"], f"ERROR {exc.__class__.__name__}", "-", "-"))
            continue
        elapsed = time.perf_counter() - t0
        total_time += elapsed
        hits, tries = 0, 0
        for key, expected in meta.get("expected", {}).items():
            tries += 1
            field = result.fields.get(key)
            ok = check(field, expected)
            matched += 1 if ok else 0
            total_fields += 1
            hits += 1 if ok else 0
        rows.append((name, meta["case"], f"{hits}/{tries}", f"{elapsed * 1000:.0f}ms",
                     result.metadata.engine))

    print(f"{'تصویر':38} | {'حالت':18} | فیلد | زمان | موتور")
    print("-" * 95)
    for r in rows:
        print(f"{r[0]:38} | {r[1]:18} | {r[2]:4} | {r[3]:7} | {r[4]}")
    if total_fields:
        print("-" * 95)
        print(f"دقت فیلد: {matched}/{total_fields} = {100 * matched / total_fields:.1f}%")
    print(f"میانگین زمان پردازش: {total_time / max(1, len(rows)) * 1000:.0f} ms "
          f"(اجرای واقعی در همین محیط)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

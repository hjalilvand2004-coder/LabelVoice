# -*- coding: utf-8 -*-
"""اثبات بهبود کیفیت OpenCV (v2.9.0) — اجرای واقعی Tesseract روی نمونهٔ سایه‌دار.

ساخت نمونهٔ «عکس موبایل با سایهٔ سنگین» (گرادیان روشنایی ۴۵٪ تا ۱۰۰٪) و
مقایسهٔ خوانش واقعی تسراکت روی واریانت‌ها: original (فقط بزرگ‌نمایی لانسزوس)
در برابر shadow_free / gray_clahe / sharpened.

خروجی: جدول مقایسه + تصاویر شاهد در scripts/evidence_v290/
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from label_reader.config import Settings, load_settings  # noqa: E402
from label_reader.preprocess import build_variants  # noqa: E402
from label_reader.ocr.tesseract_provider import TesseractProvider  # noqa: E402
from label_reader.stages import image_quality_metrics  # noqa: E402

EVID = ROOT / "scripts" / "evidence_v290"
EVID.mkdir(exist_ok=True)

FONT_FA = "/usr/share/fonts/truetype/freefont/FreeSerif.ttf"


def make_shadowed_box() -> Image.Image:
    w, h = 900, 640
    img = Image.new("RGB", (w, h), (247, 246, 242))
    d = ImageDraw.Draw(img)
    f_big = ImageFont.truetype(FONT_FA, 44)
    f_mid = ImageFont.truetype(FONT_FA, 34)
    f_lat = ImageFont.truetype(FONT_FA, 30)
    rows = [
        ("استامینوفن", f_big, 46),
        ("Paracetamol 500 mg", f_lat, 118),
        ("کپسول‌های نرم گوارشی", f_mid, 190),
        ("۵۰ کپسول", f_mid, 250),
        ("En.Ceutoed Capsules", f_lat, 330),
        ("تاریخ انقضا: ۱۴۰۶/۰۵", f_mid, 400),
        ("شماره سری: ۹۸۴۲۱", f_mid, 470),
    ]
    for text, font, y in rows:
        d.text((110, y), text, fill=(24, 24, 26), font=font)
    arr = np.array(img).astype(np.float32)
    grad = np.linspace(0.42, 1.0, w, dtype=np.float32)[None, :, None]
    arr *= grad
    # نویز ISO ملایم
    rng = np.random.default_rng(42)
    arr += rng.normal(0, 4.5, arr.shape)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def main() -> None:
    pil = make_shadowed_box()
    pil.save(EVID / "input_shadowed.png")

    settings = load_settings()
    bgr = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    variants = build_variants(bgr, settings)

    provider = TesseractProvider(settings)
    ok, note = provider.available()
    if not ok:
        print("Tesseract در دسترس نیست:", note)
        return

    print("ابعاد ورودی:", bgr.shape, "→ واریانت‌ها:",
          {k: v.shape for k, v in variants.items()})
    rows = []
    for name in ("original", "shadow_free", "gray_clahe", "sharpened"):
        img = variants[name]
        Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).save(
            EVID / f"variant_{name}.png")
        t0 = time.perf_counter()
        pieces = provider.run(img, name)
        dt = time.perf_counter() - t0
        confs = [p.confidence for p in pieces if p.confidence is not None]
        text_join = " ".join(p.text for p in pieces)
        hits = sum(1 for probe in ("استامینوفن", "Paracetamol", "500", "کپسول")
                   if probe in text_join)
        rows.append({
            "variant": name,
            "pieces": len(pieces),
            "chars": sum(len(p.text) for p in pieces),
            "mean_conf": round(float(np.mean(confs)), 3) if confs else 0.0,
            "hits": hits,
            "sec": round(dt, 2),
            "metrics": image_quality_metrics(img),
            "text": text_join[:150],
        })

    hdr = f"{'واریانت':<13}{'قطعه':>6}{'نویسه':>7}{'اطمینان':>9}{'برخورد':>8}{'زمان':>7}  معیارها"
    print(hdr)
    for r in rows:
        print(f"{r['variant']:<13}{r['pieces']:>6}{r['chars']:>7}"
              f"{r['mean_conf']:>9}{r['hits']:>8}{r['sec']:>7}  {r['metrics']}")
    print()
    for r in rows:
        print(f"--- {r['variant']} ---")
        print(r["text"])
    print("\nشواهد تصویری:", EVID)


if __name__ == "__main__":
    main()

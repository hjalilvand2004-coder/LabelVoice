# -*- coding: utf-8 -*-
"""تریم بستهٔ فونِم‌ساز Piper برای LabelVoice v2.12.0

piper_phonemize.data حاوی واژه‌نامهٔ همهٔ زبان‌های espeak-ng است (۱۸MB؛ فقط
ru_dict ۸.۵MB). برنامهٔ ما فقط فارسی و انگلیسی می‌خواند؛ این اسکریپت:
  ۱) فقط فایل‌های لازم (fa_dict، en_dict و همهٔ فایل‌های غیرواژه‌نامه‌ای مثل
     phontab/phonindex/phondata/intonations/lang/voices) را نگه می‌دارد؛
  ۲) piper_phonemize.data جدید با آفست‌های بازمحاسبه‌شده می‌سازد؛
  ۳) متادیتای تعبیه‌شده در قطعهٔ گلو (piper-DeOu3H9E.js) را با همان قالب
     (کلیدهای unquoted) بازنویسی می‌کند؛
  ۴) شواهد: طول جدید، تعداد فایل‌ها، بایست تحویل به mobile-app/vendor/tts/.
اجرا: python scripts/trim_piper_wasm_data.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DL = Path("/home/z/my-project/tts-research/dl")
CHUNK = Path("/home/z/my-project/tts-research/package/dist/piper-DeOu3H9E.js")
OUT_DIR = ROOT / "mobile-app" / "vendor" / "tts"

ENTRY_RE = re.compile(
    r"\{\s*filename:\s*\"([^\"]+)\",\s*start:\s*(\d+),\s*end:\s*(\d+)\s*\}")
LIT_START = "files: ["
RPS_RE = re.compile(r"remote_package_size:\s*(\d+)")


def keep(name: str) -> bool:
    if name.endswith("_dict"):
        return name.endswith(("fa_dict", "en_dict"))
    return True  # phontab/phonindex/phondata/intonations/lang/voices/mbrola


def main() -> None:
    src = CHUNK.read_text(encoding="utf-8")
    i0 = src.find(LIT_START)
    assert i0 > 0, "files: [ یافت نشد"
    m_rps = RPS_RE.search(src, i0)
    assert m_rps, "remote_package_size یافت نشد"
    span = src[i0:m_rps.end()]

    entries = [(m.group(1), int(m.group(2)), int(m.group(3)))
               for m in ENTRY_RE.finditer(span)]
    assert entries, "هیچ فایلی در متادیتا نبود"
    old_size = int(m_rps.group(1))
    data = (DL / "piper_phonemize.data").read_bytes()
    assert len(data) == old_size, f"حجم .data با متادیتا نمی‌خواند: {len(data)} != {old_size}"

    kept = [(n, s, e) for (n, s, e) in entries if keep(n)]
    new_size = sum(e - s for (_, s, e) in kept)

    out = bytearray()
    new_entries = []
    off = 0
    for (n, s, e) in kept:
        blob = data[s:e]
        out += blob
        new_entries.append((n, off, off + len(blob)))
        off += len(blob)
    assert off == new_size

    lines = []
    for (n, s, e) in new_entries:
        lines.append(f'            {{ filename: "{n}", start: {s}, end: {e} }},')
    body = ("files: [\n" + "\n".join(lines) +
            f"\n          ],\n          remote_package_size: {new_size}")
    patched = src[:i0] + body + src[m_rps.end():]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "piper_phonemize.data").write_bytes(bytes(out))
    (OUT_DIR / "piper-phonemize.js").write_text(patched, encoding="utf-8")

    print(f"فایل‌ها: {len(entries)} → {len(kept)}")
    print(f"حجم: {old_size/1e6:.2f}MB → {new_size/1e6:.2f}MB")
    print("خروجی:", OUT_DIR / "piper_phonemize.data")
    print("گلو:", OUT_DIR / "piper-phonemize.js")


if __name__ == "__main__":
    main()

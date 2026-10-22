# -*- coding: utf-8 -*-
"""دانلود داده زبان فارسی Tesseract (fas.traineddata) در models/tessdata.

بدون این فایل، خواندن فارسی فعال نمی‌شود و محصول صادقانه فقط eng را اعلام می‌کند.
اجرا: python scripts/download_tessdata.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESSDATA = ROOT / "models" / "tessdata"

FAS_URLS = [
    "https://github.com/tesseract-ocr/tessdata_best/raw/main/fas.traineddata",
    "https://github.com/tesseract-ocr/tessdata_fast/raw/main/fas.traineddata",
]
ENG_URLS = [
    "https://github.com/tesseract-ocr/tessdata_fast/raw/main/eng.traineddata",
]


def _system_tessdata() -> Path | None:
    try:
        out = subprocess.run(["tesseract", "--version"], capture_output=True,
                             text=True, timeout=10)
        if out.returncode != 0:
            return None
    except (OSError, subprocess.TimeoutExpired):
        return None
    candidates = [
        Path("/usr/share/tesseract-ocr/5/tessdata"),
        Path("/usr/share/tesseract-ocr/4/tessdata"),
        Path("/usr/local/share/tessdata"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _download(urls: list[str], dest: Path) -> bool:
    for url in urls:
        try:
            print(f"دانلود {url} …")
            with urllib.request.urlopen(url, timeout=120) as resp, \
                    open(dest, "wb") as fh:
                shutil.copyfileobj(resp, fh)
            if dest.stat().st_size > 100_000:
                return True
        except Exception as exc:  # noqa: BLE001
            print(f"  ناموفق: {exc}")
    return False


def main() -> int:
    TESSDATA.mkdir(parents=True, exist_ok=True)
    fas = TESSDATA / "fas.traineddata"
    eng = TESSDATA / "eng.traineddata"

    if eng.exists() and fas.exists():
        print("همه داده‌ها از قبل موجود است.")
        return 0
    sys_dir = _system_tessdata()
    if sys_dir and not eng.exists() and (sys_dir / "eng.traineddata").exists():
        shutil.copyfile(sys_dir / "eng.traineddata", eng)
        print(f"eng.traineddata از نصب سیستمی کپی شد ({sys_dir}).")
    if not eng.exists():
        if not _download(ENG_URLS, eng):
            print("دانلود eng.traineddata ناموفق بود.")
    if not fas.exists():
        if not _download(FAS_URLS, fas):
            print("دانلود fas.traineddata ناموفق بود؛ خواندن فارسی غیرفعال می‌ماند.")
            return 1
    print("انجام شد. زبان‌های موجود:")
    subprocess.run(["tesseract", "--list-langs"], check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())

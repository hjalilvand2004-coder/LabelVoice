# -*- coding: utf-8 -*-
"""ساخت Release v1.7.0 — ZIP موبایل قابل حمل + ZIP پروژه کامل.

الگوی همان اسکریپت‌های ریلیز قبلی (v1.5.0)؛ توکن از remote URL خوانده می‌شود.
"""
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path("/home/z/my-project/work/release-v170")
OUT.mkdir(parents=True, exist_ok=True)

TAG = "v1.7.0"
NAME_FA = ("v1.7.0 — اصلاح اساسی کیفیت OCR: واریانت متن-روشن-روی-تیره، "
           "ادغام بهترین-اول نسخه‌ها، گیت کیفیت قطعه‌ها، حذف هشدارهای کاذب")

BODY = """## ✨ اصلاح اساسی کیفیت OCR (رفع خروجی بی‌معنی و هشدارهای کاذب)

با بازخورد واقعی روی تصویر جعبه با متن سفید و زمینه سبز-آبی (که خروجی «RIE [SE ۱ ES {= ray WE» می‌داد)، چهار اصلاح ریشه‌ای در **هر دو نسخه دسکتاپ و موبایل** اعمال شد:

1. **واریانت جدید `white_on_dark`** — آستانه‌گذاری تطبیقی برای «متن روشن روی جعبه رنگی»؛ بدون آن نام سفید روی جعبه اصلاً خوانده نمی‌شد.
2. **ادغام «بهترین-اول» نسخه‌های پردازشی** — هر نسخه (اصلی/CLAHE/دودویی/روشن-روی-تیره) امتیاز می‌گیرد؛ بهترین مبناست و بقیه فقط جای خالی پر می‌کنند. جانشینی فقط با «خوانش کامل‌ترِ معتبر»؛ خوانش جزئی آشغال با اطمینان بالا دیگر متن سالم را خراب نمی‌کند.
3. **گیت کیفیت قطعه‌ها** — نمادهای محض (@ ، » ، °)، اطمینان زیر ۰٫۳ و قطعه کوتاه با کادر غول‌پیکر قبل از ادغام حذف می‌شوند.
4. **دروازه نام معتبر + حذف هشدارهای کاذب** — سطر آشغال دیگر «نام» نمی‌شود؛ هشدار «تصویر شسته‌شده» فقط با شستگی واقعی؛ هشدار «چند ناحیه» فقط با نام دوم معتبر؛ پاسخ فارسی ابتدا اطلاعات، بعد هشدار.

**شفافیت مرحله‌ای (ادامه v1.6.0):** خروجی مرحله ۲ (OCR) اکنون مقایسه نسخه‌های پردازشی (تعداد قطعه، اطمینان، امتیاز) را نشان می‌دهد.

## ✅ راستی‌آزمایی
- تصویر واقعی جعبه کمک‌دستی: «نام درج‌شده روی بسته: MEDICINE» (پیش از این: متن آشغال) + BOX خوانده شد + بدون هشدار کاذب
- ۱۰۶ آزمون pytest (۱۱ جدید) · ۶۴ آزمون Node (۹ جدید) · AppTest استریم‌لیت بدون استثنا · نسخه زنده Pages به‌روزرسانی شد (SW v7)

## 📥 نصب
- **موبایل/قابل حمل:** `LabelVoice-Mobile-Portable-1.7.0.zip` را باز کنید و `index.html` را باز کنید (یا روی میزبان HTTPS برای PWA).
- **اندروید:** `LabelVoice-Android-1.7.0.apk` (versionCode 10). اگر نسخه قبلی را دارید، ابتدا Uninstall کنید (کلید امضا ممکن است متفاوت باشد).
- **پروژه کامل دسکتاپ (Streamlit):** `LabelVoice-Full-Project-1.7.0.zip` — طبق README نصب شود.
- سند فنی: `documentation.html` روی Pages (نسخه ۱.۷.۰)؛ PDF سند در ریلیزهای بعدی به‌روز می‌شود.
"""


def remote_token():
    url = subprocess.check_output(
        ["git", "remote", "get-url", "origin"], cwd=ROOT, text=True)
    m = re.search(r"https://([^@]+)@", url)
    return m.group(1) if m else None


def zip_dir(src: Path, dest: Path, exclude: set = frozenset()):
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(src.rglob("*")):
            if p.is_dir():
                continue
            rel = p.relative_to(src)
            if any(part in exclude for part in rel.parts):
                continue
            z.write(p, str(rel))
    return dest


def main():
    token = remote_token()
    if not token:
        sys.exit("توکن از remote یافت نشد")
    mobile = ROOT / "mobile-app"
    z_mobile = OUT / "LabelVoice-Mobile-Portable-1.7.0.zip"
    z_full = OUT / "LabelVoice-Full-Project-1.7.0.zip"
    if not z_mobile.exists():
        zip_dir(mobile, z_mobile)
    if not z_full.exists():
        zip_dir(ROOT, z_full, exclude={".git", "__pycache__", ".venv",
                                       "node_modules", ".pytest_cache"})
    print("zips:", z_mobile.stat().st_size // 1024, "KB /",
          z_full.stat().st_size // 1024, "KB")

    api = "https://api.github.com/repos/hjalilvand2004-coder/LabelVoice"
    hdr = {"Authorization": f"token {token}",
           "Accept": "application/vnd.github+json"}

    import urllib.request
    # تگ
    req = urllib.request.Request(
        f"{api}/git/refs/tags/{TAG}", headers=hdr)
    try:
        with urllib.request.urlopen(req) as r:
            print("tag exists")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            data = json.dumps({
                "ref": f"refs/tags/{TAG}",
                "sha": subprocess.check_output(
                    ["git", "rev-parse", "main"], cwd=ROOT, text=True).strip(),
            }).encode()
            req = urllib.request.Request(
                f"{api}/git/refs", data=data, headers=hdr, method="POST")
            with urllib.request.urlopen(req) as r:
                print("tag created")

    # ریلیز (idempotent)
    req = urllib.request.Request(f"{api}/releases/tags/{TAG}", headers=hdr)
    try:
        with urllib.request.urlopen(req) as r:
            release = json.load(r)
        print("release exists:", release["id"])
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        data = json.dumps({
            "tag_name": TAG, "name": NAME_FA, "body": BODY,
            "draft": False, "prerelease": False,
        }).encode()
        req = urllib.request.Request(f"{api}/releases", data=data,
                                     headers=hdr, method="POST")
        with urllib.request.urlopen(req) as r:
            release = json.load(r)
        print("release created:", release["id"])

    # آپلود دارایی‌ها
    for asset_path in (z_mobile, z_full):
        name = asset_path.name
        existing = {a["name"] for a in release.get("assets", [])}
        if name in existing:
            print("asset exists:", name)
            continue
        url = release["upload_url"].split("{")[0] + f"?name={name}"
        data = asset_path.read_bytes()
        req = urllib.request.Request(
            url, data=data, method="POST",
            headers={**hdr, "Content-Type": "application/zip"})
        with urllib.request.urlopen(req) as r:
            res = json.load(r)
        print("uploaded:", res["name"], res["size"] // 1024, "KB")


if __name__ == "__main__":
    main()

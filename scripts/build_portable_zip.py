#!/usr/bin/env python3
"""ساخت بستهٔ قابل حمل LabelVoice (Portable Web ZIP) — v1.9.0

رفع باگ ۴۰۴ نسخهٔ v1.8.2:
  - چیدمان استاندارد: START-HERE.html + label-reader-singlefile.html + webapp/ + لانچرها + README
  - «همهٔ» نام‌فایل‌های داخل ZIP کاملاً ASCII هستند تا در هر استخراج‌کننده‌ای
    (Windows Explorer، WinRAR، 7-Zip، Bandizip، ...) بدون مخدوش‌شدگی انکودینگ خارج شوند.
  - server-windows.ps1 اصلاح‌شده: مسیر «/» به‌طور خودکار webapp/index.html را پیدا می‌کند.

کاربرد: python3 scripts/build_portable_zip.py [--apk path/to/apk]
خروجی: /home/z/my-project/download/LabelVoice-v1.9.0-Portable-Web.zip
"""
import argparse
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MOBILE = REPO / 'mobile-app'
PORTABLE = REPO / 'portable'
OUT = Path('/home/z/my-project/download')

VERSION = "2.10.0"
ROOT_NAME = 'LabelVoice-Portable-Web'

# فایل‌هایی که از mobile-app به ریشهٔ بسته می‌روند (نه داخل webapp/)
ROOT_MOVERS = {
    'VERSION.txt',
    'label-reader-singlefile.html',
    'README-MOBILE-fa.md',
    'START-WINDOWS.bat',
    'server-windows.ps1',
    'شروع-در-ویندوز.bat',
    'شروع-در-لینوکس-مک.sh',
}


def is_ascii_name(name: str) -> bool:
    return all(ord(c) < 128 for c in name)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--apk', default=None, help='مسیر APK اختیاری برای پوشهٔ _APK')
    args = ap.parse_args()

    assert (MOBILE / 'index.html').exists(), 'mobile-app/index.html یافت نشد'
    assert (PORTABLE / 'START-HERE.html').exists(), 'portable/START-HERE.html یافت نشد'

    out_path = OUT / f'LabelVoice-v{VERSION}-Portable-Web.zip'
    OUT.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    n_files = 0
    with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        # --- webapp/ (PWA کامل) ---
        for p in sorted(MOBILE.rglob('*')):
            if p.is_dir():
                continue
            rel = p.relative_to(MOBILE)
            if rel.name in ROOT_MOVERS:
                continue
            if not is_ascii_name(p.name):
                raise SystemExit(f'نام غیر-ASCII در mobile-app: {rel}')
            z.write(p, f'{ROOT_NAME}/webapp/{rel.as_posix()}')
            n_files += 1

        # --- ریشه: تک‌فایل + صفحه شروع + لانچرها + README ---
        z.write(MOBILE / 'label-reader-singlefile.html', f'{ROOT_NAME}/label-reader-singlefile.html')
        n_files += 1
        for name in ['START-HERE.html', 'START-WINDOWS.bat', 'server-windows.ps1',
                     'start-linux-mac.sh', 'START-BRIDGE.bat', 'START-BRIDGE.sh']:
            z.write(PORTABLE / name, f'{ROOT_NAME}/{name}')
            n_files += 1
        z.write(MOBILE / 'README-MOBILE-fa.md', f'{ROOT_NAME}/README-MOBILE-fa.md')
        n_files += 1
        if (MOBILE / 'VERSION.txt').exists():
            z.write(MOBILE / 'VERSION.txt', f'{ROOT_NAME}/VERSION.txt')
            n_files += 1

        # --- _APK (اختیاری) ---
        apk = Path(args.apk) if args.apk else None
        if apk and apk.exists():
            z.write(apk, f'{ROOT_NAME}/_APK/{apk.name}')
            n_files += 1

    # راستی‌آزمایی نهایی: هیچ نام غیر-ASCII داخل ZIP نباشد
    with zipfile.ZipFile(out_path) as z:
        names = z.namelist()
        bad = [n for n in names if not n.isascii()]
        assert not bad, f'نام غیر-ASCII داخل ZIP: {bad}'
        print(f'✓ {out_path}  ({out_path.stat().st_size/1024/1024:.1f} MB, {n_files} فایل + پوشه‌ها)')
        print('✓ همهٔ نام‌فایل‌های داخل ZIP کاملاً ASCII هستند')
        # خلاصهٔ چیدمان
        roots = sorted({n.split('/')[1] for n in names if n.count('/') >= 1 and len(n.split('/')) > 1 and n.split('/')[1]})
        print('✓ محتوای ریشه:', ', '.join(roots[:12]))


if __name__ == '__main__':
    main()

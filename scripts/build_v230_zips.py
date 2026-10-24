#!/usr/bin/env python3
"""ساخت بسته‌های انتشار v2.2.0 — شامل بستهٔ مستقل اپ موبایل (PWA)."""
import zipfile
from pathlib import Path

REPO = Path('/home/z/my-project/labelvoice-clone')
MOBILE = REPO / 'mobile-app'
OUT = Path('/home/z/my-project/download')
OUT.mkdir(parents=True, exist_ok=True)

VERSION = "2.5.0"


def is_ascii_name(name: str) -> bool:
    return all(ord(c) < 128 for c in name)


def add_file(zf: zipfile.ZipFile, src: Path, arcname: str) -> None:
    assert is_ascii_name(arcname), f'non-ascii: {arcname}'
    zf.write(src, arcname)


# ---------- ۱) بستهٔ مستقل اپ موبایل (PWA) ----------
mobile_zip = OUT / f'LabelVoice-v{VERSION}-Mobile-App-PWA.zip'
with zipfile.ZipFile(mobile_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    # کل PWA به‌جز تک‌فایل داخلی و فایل‌های ریشهٔ دسکتاپ
    skip = {
        'label-reader-singlefile.html', 'START-WINDOWS.bat',
        'server-windows.ps1', 'شروع-در-ویندوز.bat', 'شروع-در-لینوکس-مک.sh',
    }
    n = 0
    for p in MOBILE.rglob('*'):
        if p.is_dir():
            continue
        rel = p.relative_to(MOBILE)
        if rel.as_posix() in skip:
            continue
        if any(part in {'.git', '__pycache__', 'node_modules'} for part in rel.parts):
            continue
        add_file(zf, p, f'LabelVoice-Mobile-PWA/{rel.as_posix()}')
        n += 1
    # لانچرهای ASCII با نام استاندارد
    add_file(zf, MOBILE / 'START-WINDOWS.bat', 'LabelVoice-Mobile-PWA/START-WINDOWS.bat')
    add_file(zf, MOBILE / 'server-windows.ps1', 'LabelVoice-Mobile-PWA/server-windows.ps1')
    add_file(zf, MOBILE / 'START-BRIDGE.bat', 'LabelVoice-Mobile-PWA/START-BRIDGE.bat')
    add_file(zf, MOBILE / 'START-BRIDGE.sh', 'LabelVoice-Mobile-PWA/START-BRIDGE.sh')
    add_file(zf, MOBILE / 'شروع-در-لینوکس-مک.sh', 'LabelVoice-Mobile-PWA/start-linux-mac.sh')
print(f'OK {mobile_zip} ({mobile_zip.stat().st_size/1e6:.1f} MB)')

# ---------- ۲) پروژهٔ کامل ----------
full_zip = OUT / f'LabelVoice-v{VERSION}-Full-Project.zip'
exclude_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules',
                '.venv', 'venv', 'build', 'keystore', 'deploy-tmp'}
with zipfile.ZipFile(full_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    n = 0
    for p in REPO.rglob('*'):
        if p.is_dir():
            continue
        rel = p.relative_to(REPO)
        if any(part in exclude_dirs for part in rel.parts):
            continue
        if rel.suffix == '.pyc':
            continue
        if is_ascii_name(rel.as_posix()):
            arc = f'LabelVoice-v{VERSION}/{rel.as_posix()}'
        else:
            # نام‌فایل غیر ASCII → ترجمهٔ امن برای ویندوز
            safe = rel.name.encode('ascii', 'ignore').decode() or 'file'
            arc = f'LabelVoice-v{VERSION}/{rel.parent.as_posix()}/x-{safe}'
        zf.write(p, arc)
        n += 1
print(f'OK {full_zip} ({full_zip.stat().st_size/1e6:.1f} MB)')

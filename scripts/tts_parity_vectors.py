# -*- coding: utf-8 -*-
"""تولید وکتورهای پاریتی توکن Sec-MS-GEC v2 (مرجع: edge-tts 7.3.1).

خروجی JSON برای آزمون JS (tests-js/tts_v2110.js) — همان ورودی باید همان
توکن را در پایتون و JS بدهد؛ وگرنه کلاینت مستقیم مرورگر کار نخواهد کرد.
"""
import json
import sys

sys.path.insert(0, "/home/z/.venv/lib/python3.12/site-packages")

from edge_tts.drm import (  # noqa: E402
    TRUSTED_CLIENT_TOKEN,
    _cs64_digest,
    _sha256_digest,
    generate_sec_ms_gec_v2,
)

VECTORS_TS = [
    1768000000.5,   # اعشاری — بخش کسری باید دور شود
    1700000000.0,
    1735689600.0,   # 2025-01-01T00:00:00Z
    1799999999.9,
    1600000290.0,   # نزدیک مرز ۵ دقیقه
    1600000300.0,   # دقیقاً مرز
]

out = {"trusted_token": TRUSTED_CLIENT_TOKEN, "cases": []}
for ts in VECTORS_TS:
    ticks = float(ts)
    ticks += 11644473600
    ticks -= ticks % 300
    ticks *= 1e9 / 100
    data = f"{ticks:.0f}{TRUSTED_CLIENT_TOKEN}".encode("ascii")
    digest = _sha256_digest(data)
    a, b = _cs64_digest(data, digest)
    import struct
    cs64_hex = struct.pack("<II", a, b).hex().upper()
    out["cases"].append({
        "ts": ts,
        "ticks_str": f"{ticks:.0f}",
        "digest_hex": digest.hex().upper(),
        "cs64_hex": cs64_hex,
        "token": generate_sec_ms_gec_v2(ts),
    })

with open("/home/z/my-project/labelvoice-clone/tests-js/tts_parity_vectors.json",
          "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1)
print("OK", len(out["cases"]), "vectors; sample:", out["cases"][0]["token"][:40], "…")

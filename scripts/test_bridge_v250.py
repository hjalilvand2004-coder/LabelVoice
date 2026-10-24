# -*- coding: utf-8 -*-
"""آزمون پل OCR محلی — ping و یک خوانش واقعی با Tesseract."""
import io
import json
import threading
import time
import urllib.request

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from label_reader.bridge import start_bridge_server
from label_reader.config import Settings


def _make_png() -> bytes:
    img = Image.new("RGB", (640, 200), "white")
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 44)
    except Exception:
        f = ImageFont.load_default()
    d.text((30, 70), "Paracetamol 500 mg", fill="black", font=f)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def main() -> None:
    server = start_bridge_server(port=8779, host="127.0.0.1", settings=Settings())
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()
    time.sleep(0.3)
    base = "http://127.0.0.1:8779"

    with urllib.request.urlopen(base + "/ping", timeout=10) as r:
        ping = json.load(r)
    assert ping["ok"] and ping["server"] == "labelvoice-bridge", ping
    tess = [e for e in ping["engines"] if e["id"] == "tesseract"][0]
    print("ping OK — engines:", [(e["id"], e["available"]) for e in ping["engines"]])

    req = urllib.request.Request(
        base + "/ocr?engine=tesseract", data=_make_png(),
        headers={"Content-Type": "image/png"})
    with urllib.request.urlopen(req, timeout=60) as r:
        ocr = json.load(r)
    assert ocr["ok"], ocr
    text = " ".join(p["text"] for p in ocr["pieces"])
    assert "Paracetamol" in text and "500" in text, text
    assert ocr["count"] > 0 and ocr["width"] == 640
    print(f"ocr OK — engine={ocr['engine']} count={ocr['count']} "
          f"{ocr['duration_ms']}ms :: {text[:60]!r}")

    # خطای موتور ناشناخته → پیام شفاف ۴۰۰
    req2 = urllib.request.Request(
        base + "/ocr?engine=unknown-x", data=_make_png())
    try:
        with urllib.request.urlopen(req2, timeout=15) as r:
            bad = json.load(r)
        assert False, f"باید خطا می‌داد: {bad}"
    except urllib.error.HTTPError as e:
        assert e.code == 400
        print("unknown-engine OK → 400:", json.load(e)["error_fa"][:60])

    server.shutdown()
    print("ALL BRIDGE TESTS PASSED")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""پل OCR محلی — اجرای موتورهای سنگین دسکتاپ برای نسخهٔ وب/موبایل (v2.12.0)

خواستهٔ کاربر (v2.5.0): «جایی باشد که انتخاب مدل OCR واقعاً صورت بگیرد — هم در موبایل
اپلیکیشن و هم در وب‌سایت». موتورهای مرورگری (Tesseract.js) داخل خود مرورگر اجرا
می‌شوند؛ اما EasyOCR و Surya و Qwen3-VL-2B-Instruct مدل‌های پایتونی‌اند و داخل
مرورگر قابل اجرا نیستند. راه‌حل صادقانه: «پل محلی».

v2.12.0: اندپوینت /api/tts (v2.11.0 — مسیر آنلاین edge-tts) حذف شد؛ صدا حالا
در خود مرورگر/WebView با مدل لوکال Piper (vendor/tts + js/tts.js) ساخته می‌شود
و هیچ متنی به هیچ سرویسی — ابری یا پل — ارسال نمی‌شود.

سرورِ کوچکِ همین ماژول روی رایانهٔ دسکتاپ بالا می‌آید (از دکمهٔ سایدبار
Streamlit یا START-BRIDGE.bat) و نسخهٔ وب/موبایل تصویر پیش‌پردازش‌شده را برای
خوانش با موتور انتخابی کاربر به آن می‌فرستد. خروجی = قطعات متن با مختصات و
اطمینان؛ بقیهٔ خط لوله (استخراج فیلد، نگهبان، پاسخ) همان مسیر محلی مرورگر
می‌ماند — یعنی موتور انتخابی فقط «خواننده» است و از هیچ گواری میان‌بر نمی‌زند.

حریم خصوصی: تصویر و متن فقط بین دستگاه کاربر و رایانهٔ خودش روی شبکهٔ محلی رد و بدل
می‌شود؛ هیچ ذخیره‌سازی یا لاگ محتوایی انجام نمی‌شود (فایل‌ها بلافاصله از حافظه
پاک می‌شوند؛ لاگ فقط تعداد و مدت است).

اجرا:
    python -m label_reader.bridge --port 8770
یا در Streamlit: سایدبار → «🛰️ پل OCR برای موبایل/وب» → شروع.
"""
from __future__ import annotations

import argparse
import json
import socket
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .config import Settings
from .ocr import OcrUnavailableError, make_provider

__all__ = ["BridgeServer", "start_bridge_server", "list_engines", "main"]

BRIDGE_VERSION = "2.12.2"
DEFAULT_PORT = 8770
MAX_BODY = 20 * 1024 * 1024  # سقف امن حجم تصویر (۲۰MB)

ENGINE_CATALOG_FA = [
    {"id": "tesseract", "fa": "Tesseract 5 — LSTM (سبک و سریع)"},
    {"id": "easyocr", "fa": "EasyOCR — CRNN (عمیق)"},
    {"id": "surya", "fa": "Surya OCR — ترنسفورمری چندزبانه"},
    {"id": "qwen3-vl", "fa": "Qwen/Qwen3-VL-2B-Instruct — مدل زبانی-بینایی"},
]


def list_engines(settings: Settings | None = None) -> list[dict]:
    """فهرست موتورهای این دستگاه + وضعیت در دسترس بودن هرکدام (برای /ping)."""
    settings = settings or Settings()
    out = []
    for meta in ENGINE_CATALOG_FA:
        try:
            provider = make_provider(meta["id"], settings)
            out.append({**meta, "available": True, "hint": ""})
            del provider
        except OcrUnavailableError as exc:  # وابستگی نصب نیست — پیام شفاف
            out.append({**meta, "available": False, "hint": str(exc)})
    return out


class BridgeServer(BaseHTTPRequestHandler):
    """مسیرها: GET /ping، POST /ocr — بدون ذخیره‌سازی، بدون لاگ محتوا."""

    server_version = "LabelVoiceBridge/" + BRIDGE_VERSION
    settings: Settings  # توسط start_bridge_server تزریق می‌شود

    # ---------- ابزار پاسخ ----------
    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        """بدون لاگ محتوایی — فقط متد/مسیر/کد (حریم خصوصی)."""
        print(f"[bridge] {self.command} {self.path.split('?')[0]} :: "
              f"{fmt % args if args else ''}".split(" :: ")[0])

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.end_headers()

    # ---------- GET /ping ----------
    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?")[0]
        if path != "/ping":
            self._json({"ok": False,
                        "error_fa": "مسیر ناشناخته؛ فقط GET /ping و POST /ocr."},
                       status=404)
            return
        try:
            engines = list_engines(self.settings)
        except Exception as exc:  # noqa: BLE001
            self._json({"ok": False, "error_fa": f"خطای فهرست موتورها: {exc}"},
                       status=500)
            return
        self._json({
            "ok": True,
            "server": "labelvoice-bridge",
            "version": BRIDGE_VERSION,
            "engines": engines,
        })

    # ---------- POST /ocr?engine=<id> ----------
    def do_POST(self) -> None:  # noqa: N802
        path, _, query = self.path.partition("?")
        if path != "/ocr":
            self._json({"ok": False,
                        "error_fa": "مسیر ناشناخته؛ فقط POST /ocr?engine=…"},
                       status=404)
            return
        engine = "tesseract"
        for part in query.split("&"):
            if part.startswith("engine="):
                engine = part[7:].strip().lower() or engine

        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            self._json({"ok": False, "error_fa": "بدنهٔ تصویر خالی است."},
                       status=400)
            return
        if length > MAX_BODY:
            self._json({"ok": False,
                        "error_fa": "تصویر بیش از حد بزرگ است (سقف ۲۰ مگابایت)."},
                       status=413)
            return
        image_bytes = self.rfile.read(length)

        try:
            import cv2
            import numpy as np
        except ImportError:
            self._json({"ok": False, "error_fa":
                        "opencv-python نصب نیست — در رایانهٔ دسکتاپ "
                        "«pip install opencv-python-headless» را اجرا کنید."},
                       status=500)
            return

        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        image_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        del arr, image_bytes  # بلافاصله پاک — بدون ماندگاری
        if image_bgr is None:
            self._json({"ok": False, "error_fa":
                        "تصویر قابل رمزگشایی نبود (PNG/JPEG/WebP؟)."},
                       status=400)
            return

        t0 = time.perf_counter()
        try:
            settings = self.settings.model_copy(update={"ocr_provider": engine})
            provider = make_provider(engine, settings)
            raws = provider.run(image_bgr, "original")
        except OcrUnavailableError as exc:
            self._json({"ok": False, "engine": engine,
                        "error_fa": str(exc)}, status=400)
            return
        except Exception as exc:  # noqa: BLE001 — خطای موتور → پیام شفاف
            self._json({"ok": False, "engine": engine,
                        "error_fa": f"خطای موتور «{engine}»: {exc}"},
                       status=500)
            return
        duration_ms = int((time.perf_counter() - t0) * 1000)

        pieces = [{
            "text": r.text,
            "confidence": None if r.confidence is None else round(float(r.confidence), 4),
            "x": int(r.x), "y": int(r.y), "w": int(r.w), "h": int(r.h),
        } for r in raws]
        self._json({
            "ok": True,
            "engine": engine,
            "engine_fa": next((e["fa"] for e in ENGINE_CATALOG_FA
                               if e["id"] == engine), engine),
            "duration_ms": duration_ms,
            "count": len(pieces),
            "width": int(image_bgr.shape[1]),
            "height": int(image_bgr.shape[0]),
            "pieces": pieces,
        })


def start_bridge_server(port: int = DEFAULT_PORT,
                        host: str = "0.0.0.0",
                        settings: Settings | None = None) -> ThreadingHTTPServer:
    """ساخت سرور آمادهٔ serve_forever() — نخ daemon توسط فراخوان مدیریت می‌شود."""
    handler = type("BoundBridge", (BridgeServer,), {
        "settings": settings or Settings(),
    })
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server


def lan_ip() -> str:
    """IP محلی بدون ارسال بسته (اتصال UDP به مسیر پاک‌سازی‌شده)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:  # noqa: BLE001
        return "127.0.0.1"


def main() -> None:
    ap = argparse.ArgumentParser(
        description="پل OCR محلی LabelVoice — موتورهای دسکتاپ برای وب/موبایل")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--host", default="0.0.0.0",
                    help="پیش‌فرض 0.0.0.0 تا گوشی روی شبکهٔ محلی هم برسد")
    args = ap.parse_args()

    server = start_bridge_server(port=args.port, host=args.host)
    print("🛰️  پل برچسب‌خوان (OCR) راه‌اندازی شد (Ctrl+C برای توقف):")
    print(f"   • روی همین رایانه:  http://127.0.0.1:{args.port}/ping")
    print(f"   • از گوشی (همان Wi-Fi): http://{lan_ip()}:{args.port}/ping")
    print("   موتورهای آمادهٔ این دستگاه:")
    for e in list_engines():
        mark = "✅" if e["available"] else "⛔"
        print(f"     {mark} {e['id']:<10} {e['fa']}"
              + ("" if e["available"] else f" — {e['hint'][:70]}"))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nپل OCR متوقف شد.")


if __name__ == "__main__":
    main()

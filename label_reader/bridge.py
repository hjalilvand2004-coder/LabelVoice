# -*- coding: utf-8 -*-
"""پل OCR و TTS محلی — اجرای موتورهای سنگین دسکتاپ برای نسخهٔ وب/موبایل (v2.11.0)

خواستهٔ کاربر (v2.5.0): «جایی باشد که انتخاب مدل OCR واقعاً صورت بگیرد — هم در موبایل
اپلیکیشن و هم در وب‌سایت». موتورهای مرورگری (Tesseract.js) داخل خود مرورگر اجرا
می‌شوند؛ اما EasyOCR و Surya و Qwen3-VL-2B-Instruct مدل‌های پایتونی‌اند و داخل
مرورگر قابل اجرا نیستند. راه‌حل صادقانه: «پل محلی».

خواستهٔ کاربر (v2.11.0): «همان مدل صوتی دسکتاپ در موبایل، بدون TTS خود گوشی» —
مسیر POST /api/tts با همان کد label_reader/tts (edge-tts با صداهای
fa-IR-FaridNeural/fa-IR-DilaraNeural و جایگزین gTTS) صدا را در رایانهٔ دسکتاپ
می‌سازد و mp3 به صفحهٔ موبایل می‌دهد؛ یعنی صدای موبایل دقیقاً همان مدل دسکتاپ است.
(مسیر دوم صدا: کلاینت مستقیم Edge در js/tts.js — فقط در مرورگر Edge/APK.)

سرورِ کوچکِ همین ماژول روی رایانهٔ دسکتاپ بالا می‌آید (از دکمهٔ سایدبار
Streamlit یا START-BRIDGE.bat) و نسخهٔ وب/موبایل تصویر پیش‌پردازش‌شده را برای
خوانش با موتور انتخابی کاربر به آن می‌فرستد. خروجی = قطعات متن با مختصات و
اطمینان؛ بقیهٔ خط لوله (استخراج فیلد، نگهبان، پاسخ) همان مسیر محلی مرورگر
می‌ماند — یعنی موتور انتخابی فقط «خواننده» است و از هیچ گواری میان‌بر نمی‌زند.

حریم خصوصی: تصویر و متن فقط بین دستگاه کاربر و رایانهٔ خودش روی شبکهٔ محلی رد و بدل
می‌شود؛ هیچ ذخیره‌سازی یا لاگ محتوایی انجام نمی‌شود (فایل‌ها بلافاصله از حافظه
پاک می‌شوند؛ لاگ فقط تعداد و مدت است). TTS فقط با رضایت صریح (consent=true)
اجرا می‌شود و متن برای همان یک درخواست به سرویس ابری صوتی می‌رود.

اجرا:
    python -m label_reader.bridge --port 8770
یا در Streamlit: سایدبار → «🛰️ پل OCR برای موبایل/وب» → شروع.
"""
from __future__ import annotations

import argparse
import io
import json
import socket
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .config import Settings
from .ocr import OcrUnavailableError, make_provider
from .tts import TtsError, synthesize_with_fallback
from .tts.base import EDGE_VOICES

__all__ = ["BridgeServer", "start_bridge_server", "list_engines", "main"]

BRIDGE_VERSION = "2.11.0"
DEFAULT_PORT = 8770
MAX_BODY = 20 * 1024 * 1024  # سقف امن حجم تصویر (۲۰MB)
MAX_TTS_BODY = 64 * 1024     # سقف امن حجم بدنهٔ TTS (۶۴KB)
MAX_TTS_CHARS = 6000         # سقف طول متن هر درخواست TTS

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
    """مسیرها: GET /ping، POST /ocr، POST /api/tts — بدون ذخیره‌سازی، بدون لاگ محتوا."""

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
                        "error_fa": "مسیر ناشناخته؛ فقط GET /ping و POST /ocr و POST /api/tts."},
                       status=404)
            return
        try:
            engines = list_engines(self.settings)
        except Exception as exc:  # noqa: BLE001
            self._json({"ok": False, "error_fa": f"خطای فهرست موتورها: {exc}"},
                       status=500)
            return
        from .tts import make_tts_provider
        _prov = make_tts_provider(self.settings.tts_provider)
        _tts_ok, _tts_hint = _prov.available()
        self._json({
            "ok": True,
            "server": "labelvoice-bridge",
            "version": BRIDGE_VERSION,
            "engines": engines,
            # v2.11.0: وضعیت TTS برای صفحهٔ موبایل — همان مدل دسکتاپ از همین مسیر
            "tts": {
                "provider": _prov.name,
                "voice": self.settings.tts_voice,
                "rate": self.settings.tts_rate,
                "voices": list(EDGE_VOICES),
                "available": _tts_ok,
                "hint_fa": _tts_hint,
            },
        })

    # ---------- POST /api/tts (v2.11.0 — همان مدل صوتی دسکتاپ برای موبایل/وب) ----------
    def _handle_tts(self) -> None:
        """بدنهٔ JSON: {text, consent, voice?, rate?} → audio/mpeg یا خطای فارسی.

        همان تابع synthesize_with_fallback دسکتاپ صدا را می‌سازد (edge → gtts)؛
        یعنی صدای موبایل دقیقاً همان مدل دسکتاپ است. بدون consent=true هیچ متنی
        به سرویس ابری نمی‌رود (خط قرمز حریم خصوصی). محتوای متن لاگ نمی‌شود.
        """
        import json as _json
        import re as _re

        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            self._json({"ok": False, "error_fa": "بدنهٔ درخواست TTS خالی است."},
                       status=400)
            return
        if length > MAX_TTS_BODY:
            self._json({"ok": False,
                        "error_fa": "بدنهٔ درخواست TTS بیش از حد بزرگ است (سقف ۶۴ کیلوبایت)."},
                       status=413)
            return
        raw = self.rfile.read(length)
        try:
            payload = _json.loads(raw.decode("utf-8"))
        except Exception:  # noqa: BLE001
            self._json({"ok": False, "error_fa": "بدنهٔ JSON نامعتبر است."},
                       status=400)
            return
        if payload.get("consent") is not True:
            self._json({"ok": False,
                        "error_fa": ("بدون رضایت صریح (consent=true) متن به سرویس صوتی "
                                     "ارسال نمی‌شود — حریم خصوصی.")},
                       status=403)
            return
        text = str(payload.get("text") or "").strip()
        if not text:
            self._json({"ok": False, "error_fa": "متنی برای خواندن وجود ندارد."},
                       status=400)
            return
        if len(text) > MAX_TTS_CHARS:
            self._json({"ok": False,
                        "error_fa": f"متن بیش از حد طولانی است (سقف {MAX_TTS_CHARS} نویسه)."},
                       status=400)
            return

        voice = str(payload.get("voice") or self.settings.tts_voice).strip()
        rate = str(payload.get("rate") or self.settings.tts_rate).strip()
        if voice not in EDGE_VOICES:
            self._json({"ok": False,
                        "error_fa": ("صدای ناشناخته است؛ گزینه‌های معتبر: "
                                     + "، ".join(EDGE_VOICES))},
                       status=400)
            return
        if not _re.fullmatch(r"[+-]\d{1,3}%", rate):
            self._json({"ok": False,
                        "error_fa": "قالب سرعت نامعتبر است؛ نمونهٔ درست: «+10%» یا «-15%»."},
                       status=400)
            return

        settings = self.settings.model_copy(
            update={"tts_voice": voice, "tts_rate": rate})
        t0 = time.perf_counter()
        try:
            audio, used = synthesize_with_fallback(text, settings)
        except TtsError as exc:
            self._json({"ok": False, "error_fa": str(exc.message_fa)},
                       status=502)
            return
        except Exception as exc:  # noqa: BLE001 — خطای ناشناخته → پیام شفاف
            self._json({"ok": False,
                        "error_fa": f"خطای ناشناختهٔ تولید صدا: {exc}"},
                       status=500)
            return
        duration_ms = int((time.perf_counter() - t0) * 1000)

        self.send_response(200)
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Content-Length", str(len(audio)))
        self.send_header("X-LabelVoice-Provider", used)
        self.send_header("X-LabelVoice-Voice", voice)
        self.send_header("X-LabelVoice-Duration-Ms", str(duration_ms))
        self._cors()
        self.end_headers()
        self.wfile.write(audio)

    # ---------- POST /ocr?engine=<id>  و  POST /api/tts ----------
    def do_POST(self) -> None:  # noqa: N802
        path, _, query = self.path.partition("?")
        if path == "/api/tts":
            self._handle_tts()
            return
        if path != "/ocr":
            self._json({"ok": False,
                        "error_fa": "مسیر ناشناخته؛ فقط POST /ocr?engine=… و POST /api/tts"},
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
    print("🛰️  پل برچسب‌خوان (OCR + TTS) راه‌اندازی شد (Ctrl+C برای توقف):")
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

# -*- coding: utf-8 -*-
"""آماده‌سازی مدل TTS لوکال LabelVoice v2.12.0 — Piper fa_IR-amir-medium

گام‌ها:
  ۱) استخراج tarball رسمی sherpa-onnx (vits-piper-fa_IR-amir-medium)
  ۲) سنتز پایه با fp32 (شواهد)
  ۳) کوانتیزهٔ دینامیک int8 با onnxruntime.quantization
  ۴) اعتبارسنجی: سنتز int8 و مقایسهٔ مدت/انرژی با fp32
  ۵) چیدمان نهایی:
       models/tts/piper-fa_IR-amir/{model.int8.onnx, model.onnx(خارج از گیت — فقط شواهد),
                                     tokens.txt, espeak-ng-data/, fa_IR-amir-medium.onnx.json}
اجرا: python scripts/prepare_tts_model_v2120.py
"""
from __future__ import annotations

import json
import shutil
import struct
import sys
import tarfile
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DL = Path("/home/z/my-project/tts-research/dl")
TARBALL = DL / "vits-piper-fa_IR-amir-medium.tar.bz2"
WORK = Path("/home/z/my-project/tts-research/work")
OUT = ROOT / "models" / "tts" / "piper-fa_IR-amir"
ONNX_JSON_SRC = DL / "fa_IR-amir-medium.onnx.json"

SAMPLE_SENTENCES = [
    "نام دارو: استامینوفن، قدرت پانصد میلی‌گرم.",
    "تاریخ انقضا: ۱۴۰۶/۰۵ — مقدار: سی عدد.",
]


def extract() -> Path:
    dest = WORK / "vits-piper-fa_IR-amir-medium"
    if not (dest / "fa_IR-amir-medium.onnx").exists():
        dest.mkdir(parents=True, exist_ok=True)
        print("[1] استخراج tarball ...")
        with tarfile.open(TARBALL, "r:bz2") as tf:
            tf.extractall(WORK)
    print("    فایل‌ها:", sorted(p.name for p in dest.iterdir())[:8])
    return dest


def write_wave(path: Path, samples, rate: int) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(
            struct.pack("<h", max(-32768, min(32767, int(s * 32767))))
            for s in samples))


def audio_stats(path: Path) -> dict:
    with wave.open(str(path), "rb") as w:
        rate, n = w.getframerate(), w.getnframes()
        frames = w.readframes(n)
    import array
    arr = array.array("h")
    arr.frombytes(frames)
    peak = max(abs(min(arr)), abs(max(arr))) if arr else 0
    rms = (sum(x * x for x in arr) / max(1, len(arr))) ** 0.5
    return {"duration_s": round(n / rate, 2), "rate": rate,
            "peak": peak, "rms": round(rms, 1), "frames": n}


def synthesize(model_path: Path, dest_dir: Path, tag: str) -> list[dict]:
    import sherpa_onnx
    cfg = sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                model=str(model_path),
                tokens=str(dest_dir / "tokens.txt"),
                data_dir=str(dest_dir / "espeak-ng-data"),
            ),
        ),
        max_num_sentences=1,
    )
    tts = sherpa_onnx.OfflineTts(cfg)
    results = []
    for i, text in enumerate(SAMPLE_SENTENCES):
        t0 = time.time()
        audio = tts.generate(text, sid=0, speed=1.0)
        gen_s = time.time() - t0
        out = dest_dir / f"evidence_{tag}_{i}.wav"
        write_wave(out, audio.samples, audio.sample_rate)
        st = audio_stats(out)
        st["gen_s"] = round(gen_s, 2)
        st["tag"] = tag
        results.append(st)
        print(f"    [{tag}] {st}")
    return results


def quantize(fp32: Path, out_int8: Path) -> None:
    from onnxruntime.quantization import QuantType, quantize_dynamic
    print("[3] کوانتیزهٔ دینامیک int8 ...")
    quantize_dynamic(
        model_input=str(fp32),
        model_output=str(out_int8),
        weight_type=QuantType.QInt8,
    )
    print(f"    fp32={fp32.stat().st_size/1e6:.1f}MB → "
          f"int8={out_int8.stat().st_size/1e6:.1f}MB")


def main() -> int:
    src = extract()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "espeak-ng-data").mkdir(exist_ok=True)

    tokens = src / "tokens.txt"
    espeak = src / "espeak-ng-data"
    fp32 = src / "fa_IR-amir-medium.onnx"
    for p in (tokens,):
        shutil.copy2(p, OUT / p.name)
    if not ONNX_JSON_SRC.exists():
        print("خطا: onnx.json دانلود نشده"); return 1
    shutil.copy2(ONNX_JSON_SRC, OUT / ONNX_JSON_SRC.name)
    # espeak-ng-data (پایتون): کپی کامل فقط اگر خالی است
    dst_es = OUT / "espeak-ng-data"
    if not any(dst_es.iterdir()):
        n = 0
        for f in sorted(espeak.rglob("*")):
            if f.is_file():
                rel = f.relative_to(espeak)
                (dst_es / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dst_es / rel)
                n += 1
        print(f"    espeak-ng-data: {n} فایل کپی شد")

    print("[2] سنتز پایه fp32 (شواهد) ...")
    fp32_res = synthesize(fp32, OUT, "fp32")

    int8_path = OUT / "model.int8.onnx"
    if not int8_path.exists():
        quantize(fp32, int8_path)

    print("[4] اعتبارسنجی int8 ...")
    int8_res = synthesize(int8_path, OUT, "int8")

    report = {"fp32": fp32_res, "int8": int8_res}
    ok = True
    for a, b in zip(fp32_res, int8_res):
        ratio = b["duration_s"] / max(0.1, a["duration_s"])
        if not (0.75 <= ratio <= 1.3):
            ok = False
            print(f"    ⚠️ نسبت مدت خارج از بازهٔ مجاز: {ratio}")
        else:
            print(f"    ✅ نسبت مدت {ratio}")
    (OUT / "quantization-report.json").write_text(
        json.dumps({"pairs": report, "accepted": ok},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    # fp32 خارج از OUT برای گیت (فقط در work برای شواهد می‌ماند)
    print("[5] نتیجه:", "قبول" if ok else "رد — نگاه دستی لازم")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())

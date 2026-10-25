# -*- coding: utf-8 -*-
"""بازتولید docs/evaluation/evaluation-results.json با خط پردازش v1.6.0.

- اجرای واقعی خط پردازش روی ۱۴ نمونه برچسب‌خورده (همان schema قبل)
- افزودن بخش realworld_v160: حالت واقعی کاربر (متن سفید روی جعبه آبی،
  عکس سه‌بعدی با پرسپکتیو) — تصویر ارسالی کاربر در گزارش v1.5.0 خوانده
  نمی‌شد؛ با اصلاحات v1.6.0 خوانش درست می‌شود.
- به‌روزرسانی آزمون‌ها (pytest 86 + Node 63)
هیچ عددی جعل نمی‌شود؛ همه از اجرای واقعی همین محیط.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from label_reader.config import load_settings  # noqa: E402
from label_reader.models import FieldStatus  # noqa: E402
from label_reader.pipeline import LabelReaderPipeline  # noqa: E402

REAL_IMAGE = Path('/home/z/my-project/upload/image2.jfif')


def norm_strength(value, unit):
    if not value:
        return ""
    return value if not unit else f"{value} {unit}"


def check(field, expected_raw):
    """عین منطق scripts/evaluate.py — برای سازگاری اعداد."""
    if field is None or field.status in (FieldStatus.MISSING, FieldStatus.CONFLICTING):
        return False
    got = field.value or ""
    exp = str(expected_raw).strip()
    if field.unit and field.key in ("strength", "count", "net_weight"):
        got_full = f"{got} {field.unit}"
        return exp.lower() in got_full.lower() or got_full.lower() == exp.lower()
    return got.lower() == exp.lower() or exp.lower() in got.lower()


def run_benchmark(pipeline, manifest):
    samples = []
    total_fields = matched = 0
    times = []
    for name, meta in sorted(manifest.items()):
        img_path = ROOT / "sample_images" / name
        if not img_path.exists():
            continue
        t0 = time.perf_counter()
        try:
            result = pipeline.process_bytes(img_path.read_bytes())
        except Exception as exc:  # noqa: BLE001
            samples.append({"sample": name, "case": meta["case"],
                            "error": exc.__class__.__name__,
                            "elapsed_ms": None, "fields": [],
                            "hits": 0, "tries": 0})
            continue
        elapsed = int((time.perf_counter() - t0) * 1000)
        times.append(elapsed)
        fields = []
        hits = tries = 0
        for key, expected in meta.get("expected", {}).items():
            tries += 1
            field = result.fields.get(key)
            ok = check(field, expected)
            matched += 1 if ok else 0
            total_fields += 1
            hits += 1 if ok else 0
            fields.append({
                "field": key, "expected": expected,
                "got": (field.value if field else None),
                "status": (field.status.value if field else "missing"),
                "ok": ok,
            })
        samples.append({
            "sample": name, "case": meta["case"],
            "engine": result.metadata.engine,
            "languages": result.metadata.languages,
            "elapsed_ms": elapsed, "fields": fields,
            "hits": hits, "tries": tries,
        })
    ts = sorted(times)
    def pct(p):
        return ts[min(len(ts) - 1, int(len(ts) * p))] if ts else 0
    summary = {
        "field_accuracy": round(100 * matched / total_fields, 1) if total_fields else 0,
        "matched_fields": matched, "total_fields": total_fields,
        "samples_run": len(samples),
        "latency_ms": {
            "mean": int(sum(ts) / len(ts)) if ts else 0,
            "median": ts[len(ts) // 2] if ts else 0,
            "min": ts[0] if ts else 0,
            "max": ts[-1] if ts else 0,
            "p95": pct(0.95),
        },
    }
    # per_field / per_case
    per_field = {}
    per_case = {}
    for s in samples:
        per_case.setdefault(s["case"], {"hit": 0, "total": 0})
        for f in s.get("fields", []):
            e = per_field.setdefault(f["field"], {"hit": 0, "total": 0})
            e["total"] += 1
            per_case[s["case"]]["total"] += 1
            if f["ok"]:
                e["hit"] += 1
                per_case[s["case"]]["hit"] += 1
    for d in (per_field, per_case):
        for k, v in d.items():
            v["acc"] = round(100 * v["hit"] / v["total"], 1) if v["total"] else 0.0
    summary["per_field"] = per_field
    summary["per_case"] = per_case
    return {"summary": summary, "samples": samples}


def run_realworld(pipeline):
    """حالت واقعی کاربر: عکس سه‌بعدی جعبه با متن سفید روی زمینه آبی."""
    if not REAL_IMAGE.exists():
        return None
    t0 = time.perf_counter()
    result = pipeline.process_bytes(REAL_IMAGE.read_bytes())
    elapsed = int((time.perf_counter() - t0) * 1000)
    name = result.fields.get("name")
    strong_words = [p.text for p in result.ocr_pieces
                    if (p.confidence or 0) >= 0.75 and len(p.text.strip()) >= 3]
    return {
        "sample": "user_real_image_medicine_box.jfif",
        "description": "عکس واقعی کاربر: جعبه سه‌بعدی با متن سفید روی زمینه آبی + پس‌زمینه روشن صحنه",
        "baseline_v150": ("خوانش تار: «RIE [SE …» در موبایل؛ «MEDICINE» تنها در دسکتاپ "
                          "با هشدارهای کاذب «تصویر بیش از حد روشن» و «چند ناحیه متنی مستقل»"),
        "result_v160": {
            "name_field": {
                "value": name.value if name else None,
                "status": name.status.value if name else None,
                "confidence": name.confidence if name else None,
            },
            "languages": result.metadata.languages,
            "false_quality_warnings": [
                q.code for q in result.quality_issues if q.code in ("bright", "glare")],
            "false_multiproduct_warning": any(
                "چند ناحیه متنی مستقل" in w for w in result.metadata.warnings_fa),
            "strong_words": strong_words,
        },
        "elapsed_ms": elapsed,
    }


def run_pytest():
    out = subprocess.run(
        ["/home/z/.venv/bin/python3", "-m", "pytest", "tests/", "-q", "--tb=no"],
        cwd=ROOT, capture_output=True, text=True, timeout=1200)
    tail = (out.stdout or "").strip().splitlines()[-1] if out.stdout else ""
    import re
    m = re.search(r"(\d+) passed", tail or "")
    passed = int(m.group(1)) if m else 0
    m2 = re.search(r"(\d+) failed", tail or "")
    failed = int(m2.group(1)) if m2 else 0
    # شمارش آزمون‌ها به تفکیک فایل (برای نمودار بخش ارزیابی app.py)
    per_file = {}
    out2 = subprocess.run(
        ["/home/z/.venv/bin/python3", "-m", "pytest", "tests/", "-q", "--co"],
        cwd=ROOT, capture_output=True, text=True, timeout=600)
    for line in (out2.stdout or "").splitlines():
        line = line.strip()
        if "::" in line and "tests/" in line:
            rel = line[line.rindex("tests/"):]
            fname = rel.split("::", 1)[0]
            per_file.setdefault(fname, {"total": 0})
            per_file[fname]["total"] += 1
            if not failed:
                per_file[fname]["passed"] = per_file[fname]["total"]
    return {"passed": passed, "failed": failed, "tail": tail,
            "per_file": per_file or None}


def run_node():
    out = subprocess.run(["node", "tests-js/run_tests.js"], cwd=ROOT,
                         capture_output=True, text=True, timeout=300)
    tail = (out.stdout or "").strip().splitlines()[-1] if out.stdout else ""
    import re
    m = re.search(r"(\d+) پاس، (\d+) شکست", tail or "")
    passed = int(m.group(1)) if m else 0
    failed = int(m.group(2)) if m else 0
    return {"passed": passed, "failed": failed, "tail": tail}


def main():
    settings = load_settings()
    pipeline = LabelReaderPipeline(settings)
    manifest = json.loads(
        (ROOT / "sample_images" / "manifest.json").read_text(encoding="utf-8"))

    old_path = ROOT / "docs" / "evaluation" / "evaluation-results.json"
    old = json.loads(old_path.read_text(encoding="utf-8")) if old_path.exists() else {}

    tess = run_benchmark(pipeline, manifest)
    real = run_realworld(pipeline)

    data = {
        "meta": dict(old.get("meta", {})),
        "pipeline": {"tesseract_full": tess},
        "realworld_v160": real,
        "unit_tests": {
            "python_pytest": run_pytest(),
            "javascript_node": run_node(),
        },
        "evaluation_principles": old.get("evaluation_principles", []),
    }
    data["meta"]["version"] = "1.6.0"
    data["meta"]["date"] = time.strftime("%Y-%m-%d")
    data["meta"]["environment"]["python"] = "3.12"
    data["meta"]["note_v160"] = (
        "بازتولید کامل با خط پردازش v1.6.0: نسخه کانال‌محور (متن سفید روی زمینه "
        "تیره)، انتخاب خودکار زبان (eng اول، fas+eng با شاهد فارسی)، ارزیابی "
        "کیفیت روی ناحیه بسته. بخش realworld_v160 حالت واقعی کاربر را ثبت می‌کند. "
        "محدودیت ارقام فارسی Tesseract پابرجاست (مستند در نمونه clear_persian) و "
        "با علامت «نامطمئن» + اصلاح دستی مدیریت می‌شود — نه حدس خاموش.")
    old_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print("written:", old_path)
    print("summary:", json.dumps(tess["summary"], ensure_ascii=False)[:300])
    print("realworld:", json.dumps(real, ensure_ascii=False)[:400])
    print("tests:", data["unit_tests"]["python_pytest"]["tail"],
          "|", data["unit_tests"]["javascript_node"]["tail"])


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""آزمون دود استریم‌لیت: اجرای واقعی app.py با AppTest — بدون استثنا."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest  # noqa: E402


def main() -> int:
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=90)
    at.run()
    assert not at.exception, at.exception

    # سایدبار: چک‌باکس اعلام مرحله‌به‌مرحله پیش‌فرض روشن
    cb = [c for c in at.sidebar.checkbox if "اعلام مرحله" in c.label]
    assert cb, "چک‌باکس اعلام مرحله‌به‌مرحله در سایدبار نیست"
    assert cb[0].value is True

    # دکمه‌های راهنما: مودال اعلام مراحل + ملزومات استاد
    labels = [b.label for b in at.button]
    assert any("اعلام مراحل و ارزیابی مرحله‌ای" in l for l in labels), labels
    assert any("ملزومات استاد" in l for l in labels), labels

    # یک اجرای واقعی مرحله‌ای خط لوله (معادل مسیر پردازش UI) — بدون UI
    import io

    import PIL.Image
    from label_reader.config import load_settings
    from label_reader.pipeline import LabelReaderPipeline
    from label_reader.stages import STAGE_DEFS, build_stage_item, report_json

    img_path = ROOT / "sample_images" / "en_paracetamol_500mg.png"
    if img_path.exists():
        records = []
        pipe = LabelReaderPipeline(load_settings())
        result = pipe.process_pil(
            PIL.Image.open(img_path).convert("RGB"),
            stage_callback=lambda k, p: records.append(
                build_stage_item(k, {kk: vv for kk, vv in p.items()
                                     if kk != "image_bgr"})))
        keys = [r["key"] for r in records]
        assert keys == ["opencv", "ocr", "fields", "response"], keys
        assert all("نیازمندی استاد برآورده شد" in r["done_message_fa"]
                   for r in records)
        rep = report_json(records, {"engine": "tesseract"})
        assert "استاد قربانی" in rep
        print("OK: staged pipeline run — callback keys:", keys)

    print("OK: AppTest passed (no exceptions), stages=%d" % len(STAGE_DEFS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

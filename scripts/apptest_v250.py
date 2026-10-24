# -*- coding: utf-8 -*-
"""AppTest v2.5.0 — اپ دسکتاپ بدون استثنا + حضور بخش پل OCR."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"),
                       default_timeout=60)
at.run()
assert not at.exception, f"exception: {at.exception}"

texts = "\n".join(
    str(el) for el in list(at.sidebar) + list(at.main)
)
assert "پل OCR" in texts, "بخش پل OCR در سایدبار نیست"
assert "موتور OCR" in texts, "منوی موتور OCR نیست"
assert "Qwen3-VL" in texts

# روشن‌کردن پل → باید پیام موفقیت با آدرس محلی بدهد
tg = at.sidebar.toggle(key="bridge_toggle")
tg.run = None  # noqa — فقط برای روشن‌کردن مقدار
tg.set_value(True)
at.run()
assert not at.exception, f"exception after bridge on: {at.exception}"
joined = "\n".join(str(s.value) for s in at.sidebar.success)
assert "پل فعال است" in joined or "127.0.0.1" in joined, f"success msg: {joined[:200]}"

# خاموش‌کردن پل
at.sidebar.toggle(key="bridge_toggle").set_value(False)
at.run()
assert not at.exception, "exception after bridge off"
print("APPTEST v2.5.0 PASSED — پل OCR در سایدبار فعال/غیرفعال شد بدون استثنا")
